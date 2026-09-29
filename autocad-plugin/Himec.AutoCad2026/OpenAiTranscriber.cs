using System.Net.Http.Headers;
using System.Text.Json;

namespace Himec.AutoCad2026;

internal static class OpenAiTranscriber
{
    private static readonly HttpClient Client = new() { Timeout = TimeSpan.FromMinutes(2) };

    public static async Task<string> TranscribeAsync(string wavPath)
    {
        var key = Environment.GetEnvironmentVariable("OPENAI_API_KEY");
        if (string.IsNullOrWhiteSpace(key))
            throw new InvalidOperationException("OPENAI_API_KEY가 로컬 환경변수에 없습니다. 전사문을 직접 입력할 수 있습니다.");
        if (!File.Exists(wavPath)) throw new FileNotFoundException("녹음 파일을 찾을 수 없습니다.", wavPath);

        using var request = new HttpRequestMessage(HttpMethod.Post, "https://api.openai.com/v1/audio/transcriptions");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", key);
        using var form = new MultipartFormDataContent();
        var audio = new StreamContent(File.OpenRead(wavPath));
        audio.Headers.ContentType = new MediaTypeHeaderValue("audio/wav");
        form.Add(audio, "file", Path.GetFileName(wavPath));
        form.Add(new StringContent("gpt-4o-mini-transcribe"), "model");
        form.Add(new StringContent("ko"), "language");
        request.Content = form;
        using var response = await Client.SendAsync(request).ConfigureAwait(false);
        var body = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
            throw new InvalidOperationException($"전사 API 오류: HTTP {(int)response.StatusCode}. 키·사용량·파일 형식을 확인하세요.");
        using var json = JsonDocument.Parse(body);
        if (!json.RootElement.TryGetProperty("text", out var text))
            throw new InvalidOperationException("전사 API 응답에 text가 없습니다.");
        return text.GetString() ?? "";
    }
}
