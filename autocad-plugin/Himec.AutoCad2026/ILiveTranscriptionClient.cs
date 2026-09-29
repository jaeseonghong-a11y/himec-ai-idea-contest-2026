using Himec.ChangeCore;

namespace Himec.AutoCad2026;

internal interface ILiveTranscriptionClient : IAsyncDisposable
{
    event Action<string>? Partial;
    event Action<CompletedTranscriptTurn>? Completed;
    event Action<string>? Failed;
    Task StartAsync(string apiKey);
    bool QueuePcm(byte[] pcm);
    Task StopAsync();
}
