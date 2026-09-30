using System.Drawing;
using System.Windows.Forms;

namespace Himec.AutoCad2026;

internal static class PaletteTheme
{
    public static readonly Color Canvas = Color.FromArgb(29, 37, 46);
    public static readonly Color Header = Color.FromArgb(22, 29, 37);
    public static readonly Color Surface = Color.FromArgb(39, 49, 60);
    public static readonly Color Input = Color.FromArgb(22, 31, 40);
    public static readonly Color Border = Color.FromArgb(69, 83, 97);
    public static readonly Color Text = Color.FromArgb(239, 244, 247);
    public static readonly Color Muted = Color.FromArgb(176, 189, 201);
    public static readonly Color Accent = Color.FromArgb(73, 181, 205);
    public static readonly Color Status = Color.FromArgb(34, 66, 79);
    public static readonly Color Success = Color.FromArgb(35, 81, 66);
    public static readonly Color Warning = Color.FromArgb(92, 69, 36);
    public static readonly Color Error = Color.FromArgb(102, 52, 52);

    public static void Button(Button button, bool primary = false, bool caution = false)
    {
        button.Height = 36;
        button.FlatStyle = FlatStyle.Flat;
        button.FlatAppearance.BorderSize = 1;
        button.FlatAppearance.BorderColor = caution ? Color.FromArgb(203, 150, 84) : primary ? Accent : Border;
        button.BackColor = caution ? Color.FromArgb(108, 77, 42) : primary ? Color.FromArgb(34, 109, 130) : Surface;
        button.ForeColor = Text;
        button.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
        button.Margin = new Padding(0, 3, 0, 3);
        button.Cursor = Cursors.Hand;
    }

    public static void Check(CheckBox box)
    {
        box.Height = 26;
        box.ForeColor = Text;
        box.BackColor = Surface;
        box.Font = new Font("Segoe UI", 9F);
        box.Margin = new Padding(0, 3, 0, 3);
        box.Cursor = Cursors.Hand;
    }

    public static void Label(Label label)
    {
        label.ForeColor = Muted;
        label.Font = new Font("Segoe UI", 9F);
        label.Margin = new Padding(0, 3, 0, 3);
    }
}
