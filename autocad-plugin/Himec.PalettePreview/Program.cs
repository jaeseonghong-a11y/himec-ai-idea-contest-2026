using System.Drawing;
using System.Reflection;
using System.Runtime.Loader;
using System.Windows.Forms;

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
}
