using System.Text.Json;
using Himec.ChangeCore;

namespace Himec.AutoCad2026;

internal static class LocalRecordStore
{
    public static string Root => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Himec", "Changes");

    public static void Save(ChangeInstruction instruction)
    {
        Directory.CreateDirectory(Root);
        var path = Path.Combine(Root, $"{instruction.Id}.json");
        File.WriteAllText(path, JsonSerializer.Serialize(instruction, new JsonSerializerOptions { WriteIndented = true }));
    }
}
