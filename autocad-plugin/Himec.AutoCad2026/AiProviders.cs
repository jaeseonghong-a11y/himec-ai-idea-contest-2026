using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

namespace Himec.AutoCad2026;

internal enum AiProvider { OpenAI, Gemini, Claude }

internal static class AiProviders
{
    private static readonly HttpClient Client = new() { Timeout = TimeSpan.FromMinutes(2) };
    internal static string Name(AiProvider provider) => provider switch
    {
        AiProvider.OpenAI => "OpenAI", AiProvider.Gemini => "Gemini", _ => "Claude"
    };
    internal static string EnvironmentName(AiProvider provider) => provider switch
    {
        AiProvider.OpenAI => "OPENAI_API_KEY", AiProvider.Gemini => "GEMINI_API_KEY", _ => "ANTHROPIC_API_KEY"
    };
    internal static string? ResolveKey(AiProvider provider, string? sessionKey)
    {
        var value = !string.IsNullOrWhiteSpace(sessionKey) ? sessionKey : Environment.GetEnvironmentVariable(EnvironmentName(provider));
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }

    internal static async Task<string> TranscribeAsync(AiProvider provider, string wavPath, string? key)
    {
        if (provider == AiProvider.Claude) throw new NotSupportedException("Claude API는 WAV 음성 전사를 지원하지 않습니다. OpenAI 또는 Gemini를 선택하세요.");
        if (provider == AiProvider.OpenAI) return await OpenAiTranscriber.TranscribeAsync(wavPath, key);
        key = RequireKey(provider, key);
        var file = new FileInfo(wavPath);
        if (!file.Exists || file.Length < 44 || file.Length > 10_000_000) throw new InvalidOperationException("WAV 파일은 10MB 이하의 유효한 파일이어야 합니다.");
        var body = new
        {
            contents = new[] { new { parts = new object[] {
                new { text = "이 음성을 한국어 원문 그대로 전사하세요. 설명, 요약, 추측, 코드 블록 없이 발화한 말만 출력하세요." },
                new { inlineData = new { mimeType = "audio/wav", data = Convert.ToBase64String(await File.ReadAllBytesAsync(wavPath)) } }
            } } }
        };
        using var request = JsonRequest("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent", body);
        request.Headers.Add("x-goog-api-key", key);
        using var json = await SendAsync(request, provider);
        return GeminiText(json.RootElement);
    }

    internal static async Task<string> ReviewAsync(AiProvider provider, string transcript, string? key)
    {
        if (string.IsNullOrWhiteSpace(transcript)) throw new InvalidOperationException("검토할 전사문이 없습니다.");
        if (transcript.Length > 12000) throw new InvalidOperationException("전사문은 12,000자 이하만 보낼 수 있습니다.");
        key = RequireKey(provider, key);
        var prompt = "다음은 건축 도면 변경 회의의 전사문입니다. 변경 대상, 위치/방향, 수치를 원문 근거와 함께 간결한 한국어로 정리하세요. 불명확한 대상은 반드시 '확인 필요'로 표시하세요. 없는 객체 번호나 치수를 만들지 마세요. 이 결과는 제안일 뿐 CAD 실행 지시가 아닙니다.\n\n<전사문>\n" + transcript + "\n</전사문>";
        HttpRequestMessage request;
        if (provider == AiProvider.OpenAI)
        {
            request = JsonRequest("https://api.openai.com/v1/chat/completions", new { model = "gpt-4o-mini", max_tokens = 600, messages = new[] { new { role = "user", content = prompt } } });
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", key);
        }
        else if (provider == AiProvider.Gemini)
        {
            request = JsonRequest("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent", new { contents = new[] { new { parts = new[] { new { text = prompt } } } } });
            request.Headers.Add("x-goog-api-key", key);
        }
        else
        {
            request = JsonRequest("https://api.anthropic.com/v1/messages", new { model = "claude-haiku-4-5-20251001", max_tokens = 600, messages = new[] { new { role = "user", content = prompt } } });
            request.Headers.Add("x-api-key", key);
            request.Headers.Add("anthropic-version", "2023-06-01");
        }
        using (request)
        using (var json = await SendAsync(request, provider))
        {
            var root = json.RootElement;
            string? result = provider switch
            {
                AiProvider.Gemini => GeminiText(root),
                AiProvider.OpenAI => root.GetProperty("choices")[0].GetProperty("message").GetProperty("content").GetString(),
                _ => string.Join("\n", root.GetProperty("content").EnumerateArray().Where(x => x.TryGetProperty("type", out var t) && t.GetString() == "text").Select(x => x.GetProperty("text").GetString()))
            };
            return !string.IsNullOrWhiteSpace(result) ? result.Trim() : throw new InvalidOperationException("AI 검토 응답이 비어 있습니다.");
        }
    }

    private static string RequireKey(AiProvider provider, string? key) =>
        ResolveKey(provider, key) is { Length: > 0 } resolved ? resolved : throw new InvalidOperationException($"{Name(provider)} API 키가 없습니다. 키를 입력하거나 {EnvironmentName(provider)} 환경변수를 설정하세요.");

    private static HttpRequestMessage JsonRequest(string url, object body) => new(HttpMethod.Post, url)
    {
        Content = new StringContent(JsonSerializer.Serialize(body), Encoding.UTF8, "application/json")
    };

    private static async Task<JsonDocument> SendAsync(HttpRequestMessage request, AiProvider provider)
    {
        using var response = await Client.SendAsync(request);
        // Do not echo provider responses: they can contain user data or credentials.
        if (!response.IsSuccessStatusCode)
            throw new InvalidOperationException($"{Name(provider)} API 오류: HTTP {(int)response.StatusCode}. 계정 결제·한도·모델 접근 권한과 네트워크를 확인하세요.");
        using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonDocument.ParseAsync(stream);
    }

    private static string GeminiText(JsonElement root)
    {
        var parts = root.GetProperty("candidates")[0].GetProperty("content").GetProperty("parts");
        var result = string.Join("\n", parts.EnumerateArray().Where(p => p.TryGetProperty("text", out _)).Select(p => p.GetProperty("text").GetString()));
        return !string.IsNullOrWhiteSpace(result) ? result.Trim() : throw new InvalidOperationException("Gemini 응답에 텍스트가 없습니다.");
    }
}
