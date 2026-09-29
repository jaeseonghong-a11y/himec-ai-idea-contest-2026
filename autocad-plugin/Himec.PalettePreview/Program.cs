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
            Console.WriteLine("Palette audio-selection and error-status checks passed");
        }
        finally
        {
            if (File.Exists(path)) File.Delete(path);
        }
    }
}
