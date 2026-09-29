using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using Himec.ChangeCore;

namespace Himec.AutoCad2026;

// Gemini Live requires 16 kHz mono PCM. The recorder remains 24 kHz for OpenAI and local WAV.
internal sealed class GeminiLiveTranscriptionClient : ILiveTranscriptionClient
{
    internal const string SetupMessage = """
        {"setup":{"model":"models/gemini-3.5-transcribe-live","generationConfig":{"responseModalities":["TEXT"]},"inputAudioTranscription":{"languageCodes":["ko-KR"]}}}
        """;
    private const string BaseUrl = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=";
    private readonly ClientWebSocket _socket = new();
    private readonly CancellationTokenSource _cancel = new();
    private readonly Channel<string> _outgoing = Channel.CreateBounded<string>(new BoundedChannelOptions(80)
    {
        SingleReader = true, SingleWriter = false, FullMode = BoundedChannelFullMode.Wait
    });
    private readonly TaskCompletionSource<bool> _ready = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly object _sync = new();
    private Task? _sender;
    private Task? _receiver;
    private bool _acceptAudio;
    private long _totalInputBytes;
    private int _turnNumber;
    private short[] _resampleCarry = [];

    public event Action<string>? Partial;
    public event Action<CompletedTranscriptTurn>? Completed;
    public event Action<string>? Failed;

    public async Task StartAsync(string apiKey)
    {
        if (string.IsNullOrWhiteSpace(apiKey)) throw new InvalidOperationException("Gemini API 키가 필요합니다.");
        try
        {
            // The provider's documented WebSocket protocol uses a key query parameter.
            // Never display/log this URI or raw network exceptions.
            await _socket.ConnectAsync(new Uri(BaseUrl + Uri.EscapeDataString(apiKey.Trim())), _cancel.Token)
                .WaitAsync(TimeSpan.FromSeconds(15), _cancel.Token);
            _sender = SendLoopAsync();
            _receiver = ReceiveLoopAsync();
            _outgoing.Writer.TryWrite(SetupMessage);
            await _ready.Task.WaitAsync(TimeSpan.FromSeconds(12), _cancel.Token);
            _acceptAudio = true;
        }
        catch (Exception)
        {
            throw new InvalidOperationException("Gemini 실시간 전사 연결 실패. API 키·결제·모델 접근 권한·네트워크를 확인하세요. 로컬 WAV는 계속 녹음됩니다.");
        }
    }

    public bool QueuePcm(byte[] pcm)
    {
        lock (_sync)
        {
            if (!_acceptAudio || pcm.Length < 6) return false;
            var converted = Downsample24To16(pcm, ref _resampleCarry);
            var message = JsonSerializer.Serialize(new { realtimeInput = new { audio = new { data = Convert.ToBase64String(converted), mimeType = "audio/pcm;rate=16000" } } });
            if (!_outgoing.Writer.TryWrite(message))
            {
                _acceptAudio = false;
                Failed?.Invoke("Gemini 실시간 전사 전송 대기열이 가득 찼습니다. 로컬 WAV는 계속 녹음됩니다.");
                return false;
            }
            Interlocked.Add(ref _totalInputBytes, pcm.Length);
            return true;
        }
    }

    // Three 24 kHz samples become two 16 kHz samples; carry preserves frame boundaries.
    internal static byte[] Downsample24To16(byte[] pcm, ref short[] carry)
    {
        var sampleCount = pcm.Length / 2;
        var samples = new short[carry.Length + sampleCount];
        carry.CopyTo(samples, 0);
        Buffer.BlockCopy(pcm, 0, samples, carry.Length * 2, sampleCount * 2);
        var groups = samples.Length / 3;
        var output = new short[groups * 2];
        for (var i = 0; i < groups; i++)
        {
            var offset = i * 3;
            output[i * 2] = samples[offset];
            output[i * 2 + 1] = (short)((samples[offset + 1] + samples[offset + 2]) / 2);
        }
        carry = samples.Skip(groups * 3).ToArray();
        var bytes = new byte[output.Length * 2];
        Buffer.BlockCopy(output, 0, bytes, 0, bytes.Length);
        return bytes;
    }

    private async Task SendLoopAsync()
    {
        try
        {
            await foreach (var message in _outgoing.Reader.ReadAllAsync(_cancel.Token))
                await _socket.SendAsync(Encoding.UTF8.GetBytes(message), WebSocketMessageType.Text, true, _cancel.Token);
        }
        catch (OperationCanceledException) { }
        catch (Exception) { Failed?.Invoke("Gemini 실시간 전사 전송 오류. 로컬 WAV는 계속 녹음됩니다."); }
    }

    private async Task ReceiveLoopAsync()
    {
        try
        {
            var buffer = new byte[8192];
            while (_socket.State == WebSocketState.Open && !_cancel.IsCancellationRequested)
            {
                using var stream = new MemoryStream();
                WebSocketReceiveResult part;
                do
                {
                    part = await _socket.ReceiveAsync(buffer, _cancel.Token);
                    if (part.MessageType == WebSocketMessageType.Close)
                    {
                        _ready.TrySetException(new InvalidOperationException("Gemini가 연결을 종료했습니다."));
                        Failed?.Invoke("Gemini 실시간 전사 연결이 종료됐습니다. 로컬 WAV는 계속 녹음됩니다.");
                        return;
                    }
                    if (stream.Length + part.Count > 100_000) throw new InvalidDataException("응답 크기 제한");
                    stream.Write(buffer, 0, part.Count);
                } while (!part.EndOfMessage);
                HandleEvent(Encoding.UTF8.GetString(stream.ToArray()));
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception)
        {
            _ready.TrySetException(new InvalidOperationException("Gemini 실시간 전사 응답 오류"));
            Failed?.Invoke("Gemini 실시간 전사 응답 오류. 로컬 WAV는 계속 녹음됩니다.");
        }
    }

    internal void HandleEvent(string message)
    {
        using var json = JsonDocument.Parse(message);
        var root = json.RootElement;
        if (root.TryGetProperty("setupComplete", out _)) { _ready.TrySetResult(true); return; }
        if (root.TryGetProperty("error", out _))
        {
            _ready.TrySetException(new InvalidOperationException("Gemini 요청 거절"));
            Failed?.Invoke("Gemini가 실시간 전사를 거절했습니다. API 결제·한도·모델 접근 권한을 확인하세요.");
            return;
        }
        if (!root.TryGetProperty("serverContent", out var content)) return;
        if (content.TryGetProperty("interimInputTranscription", out var interim) &&
            interim.TryGetProperty("text", out var partial)) Partial?.Invoke(partial.GetString() ?? "");
        if (content.TryGetProperty("inputTranscription", out var final) &&
            final.TryGetProperty("text", out var text) && !string.IsNullOrWhiteSpace(text.GetString()))
            Completed?.Invoke(new CompletedTranscriptTurn("gemini-" + Interlocked.Increment(ref _turnNumber),
                text.GetString()!, Interlocked.Read(ref _totalInputBytes) / 48000.0));
    }

    public async Task StopAsync()
    {
        lock (_sync) _acceptAudio = false;
        _outgoing.Writer.TryWrite("{\"realtimeInput\":{\"audioStreamEnd\":true}}");
        _outgoing.Writer.TryComplete();
        if (_sender is not null) try { await _sender.WaitAsync(TimeSpan.FromSeconds(5)); } catch (Exception) { }
        // Allow the server to return the final utterance after audioStreamEnd.
        await Task.Delay(700);
        _cancel.Cancel();
        _socket.Abort();
        if (_receiver is not null) try { await _receiver; } catch (Exception) { }
    }

    public ValueTask DisposeAsync()
    {
        _cancel.Cancel();
        _socket.Dispose();
        _cancel.Dispose();
        return ValueTask.CompletedTask;
    }
}
