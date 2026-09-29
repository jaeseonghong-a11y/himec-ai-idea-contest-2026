using NAudio.Wave;

namespace Himec.AutoCad2026;

internal sealed class AudioRecorder : IDisposable
{
    private WaveInEvent? _input;
    private WaveFileWriter? _writer;
    private TaskCompletionSource<string>? _stopped;
    private string? _path;
    private bool _disposed;
    private const long MaxBytes = 10_000_000;

    public bool IsRecording => _input is not null;
    public string? LastFilePath { get; private set; }

    public string Start()
    {
        if (_disposed) throw new ObjectDisposedException(nameof(AudioRecorder));
        if (_input is not null) throw new InvalidOperationException("이미 녹음 중입니다.");
        var folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Himec", "Recordings");
        Directory.CreateDirectory(folder);
        _path = Path.Combine(folder, $"meeting-{DateTime.Now:yyyyMMdd-HHmmss}-{Guid.NewGuid():N}.wav");
        var input = new WaveInEvent { WaveFormat = new WaveFormat(16000, 16, 1), BufferMilliseconds = 200 };
        var writer = new WaveFileWriter(_path, input.WaveFormat);
        _stopped = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
        _input = input;
        _writer = writer;
        input.DataAvailable += (_, e) =>
        {
            writer.Write(e.Buffer, 0, e.BytesRecorded);
            if (writer.Length >= MaxBytes) input.StopRecording();
        };
        input.RecordingStopped += (_, e) =>
        {
            writer.Dispose();
            input.Dispose();
            _writer = null;
            _input = null;
            if (e.Exception is not null) _stopped?.TrySetException(e.Exception);
            else
            {
                LastFilePath = _path;
                _stopped?.TrySetResult(_path!);
            }
        };
        try { input.StartRecording(); }
        catch
        {
            writer.Dispose();
            input.Dispose();
            _writer = null;
            _input = null;
            throw;
        }
        return _path;
    }

    public Task<string> StopAsync()
    {
        if (_input is null || _stopped is null) throw new InvalidOperationException("녹음 중이 아닙니다.");
        _input.StopRecording();
        return _stopped.Task;
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        if (_input is not null) _input.StopRecording();
    }
}
