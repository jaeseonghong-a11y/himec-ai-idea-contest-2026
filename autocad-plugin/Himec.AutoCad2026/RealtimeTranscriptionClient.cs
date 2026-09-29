using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using Himec.ChangeCore;

namespace Himec.AutoCad2026;

// Never persists the key, PCM, or server messages. One ordered sender owns the socket.
internal sealed class RealtimeTranscriptionClient : IAsyncDisposable
{
    internal static readonly Uri Endpoint = new("wss://api.openai.com/v1/realtime?intent=transcription");
    internal const string SessionUpdateMessage = """
        {"type":"session.update","session":{"type":"transcription","audio":{"input":{"format":{"type":"audio/pcm","rate":24000},"transcription":{"model":"gpt-live-transcribe","languages":["ko"]},"turn_detection":null}}}}
        """;
    private readonly ClientWebSocket _socket = new();
    private readonly CancellationTokenSource _cancellation = new();
    private readonly CancellationTokenSource _commitCancellation = new();
    private readonly object _queueLock = new();
    private readonly Channel<string> _outgoing = Channel.CreateBounded<string>(new BoundedChannelOptions(80)
    {
        SingleReader = true, SingleWriter = false, FullMode = BoundedChannelFullMode.Wait
    });
    private readonly TaskCompletionSource<bool> _ready = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private Task? _sender;
    private Task? _receiver;
    private Task? _committer;
    private long _uncommittedBytes;
    private long _totalBytes;
    private int _pendingTurns;
    private bool _acceptAudio;

    public event Action<string>? Partial;
    public event Action<CompletedTranscriptTurn>? Completed;
    public event Action<string>? Failed;

    public async Task StartAsync(string apiKey)
    {
        if (string.IsNullOrWhiteSpace(apiKey)) throw new InvalidOperationException("OpenAI API 키가 필요합니다.");
        _socket.Options.SetRequestHeader("Authorization", "Bearer " + apiKey.Trim());
        // The transcription model is selected by session.update, not by the WebSocket URL.
        await _socket.ConnectAsync(Endpoint,
            _cancellation.Token).WaitAsync(TimeSpan.FromSeconds(15), _cancellation.Token).ConfigureAwait(false);
        _sender = SendLoopAsync();
        _receiver = ReceiveLoopAsync();
        Enqueue(SessionUpdateMessage);
        await _ready.Task.WaitAsync(TimeSpan.FromSeconds(12), _cancellation.Token).ConfigureAwait(false);
        _acceptAudio = true;
        _committer = CommitLoopAsync();
    }

    public bool QueuePcm(byte[] pcm)
    {
        lock (_queueLock)
        {
            if (!_acceptAudio || pcm.Length == 0) return false;
            var message = JsonSerializer.Serialize(new { type = "input_audio_buffer.append", audio = Convert.ToBase64String(pcm) });
            if (!_outgoing.Writer.TryWrite(message))
            {
                _acceptAudio = false;
                Failed?.Invoke("실시간 전사 전송이 밀려 중단됐습니다. 로컬 WAV 녹음은 계속됩니다.");
                return false;
            }
            Interlocked.Add(ref _uncommittedBytes, pcm.Length);
            Interlocked.Add(ref _totalBytes, pcm.Length);
            return true;
        }
    }

    private void Enqueue(string message)
    {
        if (!_outgoing.Writer.TryWrite(message)) throw new InvalidOperationException("실시간 전사 전송 대기열이 가득 찼습니다.");
    }

    private async Task CommitLoopAsync()
    {
        try
        {
            using var timer = new PeriodicTimer(TimeSpan.FromSeconds(4));
            while (await timer.WaitForNextTickAsync(_commitCancellation.Token).ConfigureAwait(false))
                CommitPending();
        }
        catch (OperationCanceledException) { }
    }

    private void CommitPending()
    {
        lock (_queueLock)
            if (Interlocked.Exchange(ref _uncommittedBytes, 0) > 0)
            {
                Interlocked.Increment(ref _pendingTurns);
                Enqueue("{\"type\":\"input_audio_buffer.commit\"}");
            }
    }

    private async Task SendLoopAsync()
    {
        try
        {
            await foreach (var message in _outgoing.Reader.ReadAllAsync(_cancellation.Token).ConfigureAwait(false))
            {
                var bytes = Encoding.UTF8.GetBytes(message);
                await _socket.SendAsync(bytes, WebSocketMessageType.Text, true, _cancellation.Token).ConfigureAwait(false);
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception) { _acceptAudio = false; Failed?.Invoke("실시간 전사 연결이 끊겼습니다. 로컬 WAV 녹음은 계속됩니다."); }
    }

    private async Task ReceiveLoopAsync()
    {
        try
        {
            var buffer = new byte[8192];
            while (_socket.State == WebSocketState.Open && !_cancellation.IsCancellationRequested)
            {
                using var stream = new MemoryStream();
                WebSocketReceiveResult part;
                do
                {
                    part = await _socket.ReceiveAsync(buffer, _cancellation.Token).ConfigureAwait(false);
                    if (part.MessageType == WebSocketMessageType.Close)
                    {
                        _acceptAudio = false;
                        _ready.TrySetException(new InvalidOperationException("실시간 전사 서버가 연결을 닫았습니다."));
                        Failed?.Invoke("실시간 전사 연결이 종료됐습니다. 로컬 WAV 녹음은 계속됩니다.");
                        return;
                    }
                    if (stream.Length + part.Count > 100_000) throw new InvalidDataException("전사 응답이 너무 큽니다.");
                    stream.Write(buffer, 0, part.Count);
                } while (!part.EndOfMessage);
                HandleEvent(Encoding.UTF8.GetString(stream.ToArray()));
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception)
        {
            _acceptAudio = false;
            _ready.TrySetException(new InvalidOperationException("실시간 전사 연결 또는 응답에 오류가 있습니다."));
            Failed?.Invoke("실시간 전사 응답 오류. 로컬 WAV 녹음은 계속됩니다.");
        }
    }

    internal void HandleEvent(string message)
    {
        using var json = JsonDocument.Parse(message);
        var root = json.RootElement;
        if (!root.TryGetProperty("type", out var typeValue)) return;
        var type = typeValue.GetString();
        if (type == "session.updated") { _ready.TrySetResult(true); return; }
        if (type == "error")
        {
            _acceptAudio = false;
            _ready.TrySetException(new InvalidOperationException("실시간 전사 서버가 요청을 거절했습니다. API 결제·한도·모델 접근 권한을 확인하세요."));
            Failed?.Invoke("실시간 전사 서버 오류. API 결제·한도·모델 접근 권한을 확인하세요. 로컬 녹음은 계속됩니다.");
            return;
        }
        if (type == "conversation.item.input_audio_transcription.delta" &&
            root.TryGetProperty("delta", out var delta))
            Partial?.Invoke(delta.GetString() ?? "");
        if (type == "conversation.item.input_audio_transcription.completed" &&
            root.TryGetProperty("transcript", out var transcript) &&
            root.TryGetProperty("item_id", out var itemId))
        {
            if (Volatile.Read(ref _pendingTurns) > 0) Interlocked.Decrement(ref _pendingTurns);
            if (!string.IsNullOrWhiteSpace(transcript.GetString()))
                Completed?.Invoke(new CompletedTranscriptTurn(itemId.GetString() ?? Guid.NewGuid().ToString("N"),
                    transcript.GetString()!, Interlocked.Read(ref _totalBytes) / 48000.0));
        }
    }

    public async Task StopAsync()
    {
        lock (_queueLock) _acceptAudio = false;
        _commitCancellation.Cancel();
        if (_committer is not null) await _committer.ConfigureAwait(false);
        try { CommitPending(); } catch (InvalidOperationException) { }
        _outgoing.Writer.TryComplete();
        if (_sender is not null) await _sender.WaitAsync(TimeSpan.FromSeconds(5)).ConfigureAwait(false);
        // Preserve the last transcript when the server takes longer than a single audio frame.
        if (_receiver is not null)
        {
            var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(8);
            while (Volatile.Read(ref _pendingTurns) > 0 &&
                   _socket.State == WebSocketState.Open && DateTime.UtcNow < deadline)
                await Task.Delay(100).ConfigureAwait(false);
        }
        _cancellation.Cancel();
        _socket.Abort();
        if (_receiver is not null) try { await _receiver.ConfigureAwait(false); } catch (OperationCanceledException) { }
    }

    public async ValueTask DisposeAsync()
    {
        _cancellation.Cancel();
        _commitCancellation.Cancel();
        _socket.Dispose();
        _cancellation.Dispose();
        _commitCancellation.Dispose();
        await Task.CompletedTask;
    }
}
