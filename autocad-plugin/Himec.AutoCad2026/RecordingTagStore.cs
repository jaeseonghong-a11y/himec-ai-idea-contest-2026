using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Himec.ChangeCore;

namespace Himec.AutoCad2026;

internal static class RecordingTagStore
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };
    private static string Root => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Himec", "Sessions");

    public static RecordingTagSession LoadOrCreate(string recordingPath)
    {
        var path = SessionFile(recordingPath);
        if (!File.Exists(path)) return new RecordingTagSession { RecordingPath = recordingPath };
        var session = JsonSerializer.Deserialize<RecordingTagSession>(File.ReadAllText(path))
            ?? throw new InvalidDataException("태그 세션 파일을 읽을 수 없습니다.");
        if (!StringComparer.OrdinalIgnoreCase.Equals(session.RecordingPath, recordingPath))
            throw new InvalidDataException("태그 세션의 녹음 경로가 일치하지 않습니다.");
        return session;
    }

    public static void Save(RecordingTagSession session)
    {
        Directory.CreateDirectory(Root);
        var path = SessionFile(session.RecordingPath);
        var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            File.WriteAllText(temporary, JsonSerializer.Serialize(session, JsonOptions));
            // File.Move(overwrite) is .NET Core only; File.Replace works on both targets.
            if (File.Exists(path)) File.Replace(temporary, path, null);
            else File.Move(temporary, path);
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }

    private static string SessionFile(string recordingPath)
    {
        var normalized = Path.GetFullPath(recordingPath).ToUpperInvariant();
        // SHA256.HashData and Convert.ToHexString are .NET 5+; these produce the
        // same uppercase digest on both targets, so existing session files still resolve.
        using var sha = SHA256.Create();
        var hash = BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(normalized))).Replace("-", string.Empty);
        return Path.Combine(Root, hash + ".tags.json");
    }
}
