using System.Net.Http.Headers;
using System.Text.Json;

namespace Himec.AutoCad2026;

internal static class OpenAiTranscriber
{
    private static readonly HttpClient Client = new() { Timeout = TimeSpan.FromMinutes(2) };

    public static bool HasEnvironmentKey => !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("OPENAI_API_KEY"));

    public static async Task<string> TranscribeAsync(string wavPath, string? sessionKey = null)
    {
        var key = !string.IsNullOrWhiteSpace(sessionKey)
            ? sessionKey.Trim()
            : Environment.GetEnvironmentVariable("OPENAI_API_KEY");
        if (string.IsNullOrWhiteSpace(key))
            throw new InvalidOperationException("전사 API 키가 없습니다. 팔레트의 'API 키 입력'을 누르거나 전사문을 직접 입력하세요.");
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
        var transcript = text.GetString();
        if (string.IsNullOrWhiteSpace(transcript))
            throw new InvalidOperationException("전사 결과가 비어 있습니다. 녹음 장치와 음성을 확인한 뒤 다시 시도하세요.");
        return transcript;
    }
}
