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
            throw new InvalidOperationException(DescribeError((int)response.StatusCode, body));
        using var json = JsonDocument.Parse(body);
        if (!json.RootElement.TryGetProperty("text", out var text))
            throw new InvalidOperationException("전사 API 응답에 text가 없습니다.");
        var transcript = text.GetString();
        if (string.IsNullOrWhiteSpace(transcript))
            throw new InvalidOperationException("전사 결과가 비어 있습니다. 녹음 장치와 음성을 확인한 뒤 다시 시도하세요.");
        return transcript;
    }

    internal static string DescribeError(int status, string body)
    {
        string? code = null;
        try
        {
            using var json = JsonDocument.Parse(body);
            if (json.RootElement.TryGetProperty("error", out var error) &&
                error.TryGetProperty("code", out var value) && value.ValueKind == JsonValueKind.String)
                code = value.GetString();
        }
        catch (JsonException) { /* Never show untrusted response text or a secret in the UI. */ }
        var explanation = code switch
        {
            "credit_balance_exhausted" or "insufficient_quota" => "API 잔액/할당량을 확인하세요. ChatGPT 구독과 API 결제는 별도입니다.",
            "project_spend_limit_exceeded" => "이 API 키가 속한 프로젝트의 지출 한도를 확인하세요.",
            "organization_spend_limit_exceeded" or "organization_usage_limit_exceeded" => "API 조직의 사용·지출 한도를 확인하세요.",
            "invalid_api_key" => "API 키가 유효하지 않습니다. 팔레트에서 OpenAI API 키를 다시 입력하세요.",
            _ when status == 429 => "요청 속도 제한 또는 API 잔액·사용 한도 문제입니다. OpenAI API 결제/한도 페이지를 확인하세요.",
            _ when status == 401 => "OpenAI API 키가 유효하지 않습니다. 키를 다시 입력하세요.",
            _ when status == 413 => "녹음 파일 크기 제한입니다. 더 짧게 녹음하세요.",
            _ => "계정 상태·파일 형식·네트워크를 확인하세요."
        };
        var safeCode = code is "credit_balance_exhausted" or "insufficient_quota" or
            "project_spend_limit_exceeded" or "organization_spend_limit_exceeded" or
            "organization_usage_limit_exceeded" or "invalid_api_key" ? $" ({code})" : "";
        return $"전사 API 오류: HTTP {status}{safeCode}. {explanation} 녹음 파일은 로컬에 남아 있습니다.";
    }
}
