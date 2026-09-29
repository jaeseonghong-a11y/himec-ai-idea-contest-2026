using System.Drawing;
using System.Reflection;
using System.Runtime.Loader;
using System.Windows.Forms;
using NAudio.Wave;

namespace Himec.PalettePreview;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        if (args.Length > 0 && args[0] == "--test-wav")
        {
            var destination = args.Length > 1 ? args[1] : throw new ArgumentException("Output WAV path required.");
            if (File.Exists(destination)) throw new IOException("Test WAV already exists; refusing overwrite.");
            using (var writer = new WaveFileWriter(destination, new WaveFormat(16000, 16, 1)))
                writer.Write(new byte[32000], 0, 32000);
            Console.WriteLine(destination);
            return;
        }
        AssemblyLoadContext.Default.Resolving += (_, name) =>
        {
            var path = Path.Combine(@"C:\Program Files\Autodesk\AutoCAD 2026", name.Name + ".dll");
            return File.Exists(path) ? AssemblyLoadContext.Default.LoadFromAssemblyPath(path) : null;
        };
        ApplicationConfiguration.Initialize();
        var pluginPath = Path.Combine(AppContext.BaseDirectory, "Himec.AutoCad2026.dll");
        var type = AssemblyLoadContext.Default.LoadFromAssemblyPath(pluginPath).GetType("Himec.AutoCad2026.ReviewPanel")
            ?? throw new InvalidOperationException("ReviewPanel type not found.");
        using var panel = (Control)(Activator.CreateInstance(type, nonPublic: true)
            ?? throw new InvalidOperationException("ReviewPanel construction failed."));
        if (args.Length > 0 && args[0] == "--self-test")
        {
            TestAudioPickerState(type, panel);
            return;
        }
        using var form = new Form
        {
            Text = "HIMEC palette preview — no AutoCAD commands",
            ClientSize = new Size(420, args.Length > 1 && int.TryParse(args[1], out var height) ? height : 640),
            StartPosition = FormStartPosition.Manual,
            Location = new Point(30, 30)
        };
        form.Controls.Add(panel);
        form.Show();
        Application.DoEvents();
        using var bitmap = new Bitmap(form.ClientSize.Width, form.ClientSize.Height);
        form.DrawToBitmap(bitmap, new Rectangle(Point.Empty, bitmap.Size));
        var output = args.Length > 0 ? args[0] : Path.Combine(Path.GetTempPath(), "himec-palette-preview.png");
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
        bitmap.Save(output);
        Console.WriteLine(output);
        form.Close();
    }

    private static void TestAudioPickerState(Type type, Control panel)
    {
        var path = Path.Combine(Path.GetTempPath(), "himec-preview-test-" + Guid.NewGuid().ToString("N") + ".wav");
        var store = type.Assembly.GetType("Himec.AutoCad2026.RecordingTagStore")
            ?? throw new InvalidOperationException("RecordingTagStore not found.");
        var sessionPath = (string)(store.GetMethod("SessionFile", BindingFlags.Static | BindingFlags.NonPublic)?.Invoke(null, [path])
            ?? throw new InvalidOperationException("SessionFile not found."));
        try
        {
            using (var writer = new WaveFileWriter(path, new WaveFormat(16000, 16, 1)))
                writer.Write(new byte[32000], 0, 32000);
            var select = type.GetMethod("SetSelectedAudio", BindingFlags.Instance | BindingFlags.NonPublic)
                ?? throw new InvalidOperationException("SetSelectedAudio not found.");
            select.Invoke(panel, [path]);
            var info = (Label)(type.GetField("_recordingInfo", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(panel)
                ?? throw new InvalidOperationException("Recording info not found."));
            if (!info.Text.Contains("1.0초", StringComparison.Ordinal))
                throw new InvalidOperationException("Synthetic WAV duration was not shown.");
            type.GetMethod("SetStatus")!.Invoke(panel, ["전사 실패: 시험 오류"]);
            var status = (Label)(type.GetField("_status", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(panel)
                ?? throw new InvalidOperationException("Status label not found."));
            if (!status.Text.Contains("전사 실패", StringComparison.Ordinal))
                throw new InvalidOperationException("Transcription error was not shown.");
            var tagPanel = type.GetField("_tagReview", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(panel)
                ?? throw new InvalidOperationException("Tag review panel not found.");
            var tagType = tagPanel.GetType();
            tagType.GetMethod("AddTranscriptMentions")!.Invoke(tagPanel, ["C1 기둥을 옮기자. 덕트도 확인하자."]);
            var grid = (DataGridView)(tagType.GetField("_grid", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(tagPanel)
                ?? throw new InvalidOperationException("Tag grid not found."));
            if (grid.Rows.Count != 2) throw new InvalidOperationException("Transcript tag rows were not shown.");
            grid.CurrentCell = grid.Rows[0].Cells[1];
            tagType.GetField("_pendingTagId", BindingFlags.Instance | BindingFlags.NonPublic)!
                .SetValue(tagPanel, grid.Rows[0].Tag as string);
            tagType.GetMethod("CompletePick")!.Invoke(tagPanel, ["synthetic.dxf", "1A", "BlockReference", "COLUMN"]);
            if (Convert.ToString(grid.Rows[0].Cells[2].Value) != "지정 완료")
                throw new InvalidOperationException("Tag-object link was not shown.");
            if (!File.Exists(sessionPath)) throw new InvalidOperationException("Tag session was not saved.");
            Console.WriteLine("Palette audio, error, transcript-tag list, object-link and local-save checks passed");
        }
        finally
        {
            if (File.Exists(path)) File.Delete(path);
            if (File.Exists(sessionPath)) File.Delete(sessionPath);
        }
    }
}
