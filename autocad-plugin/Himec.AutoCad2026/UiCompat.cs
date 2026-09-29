using System.Windows.Forms;
#if NET48
using System.Runtime.InteropServices;
#endif

namespace Himec.AutoCad2026;

/// <summary>Bridges the few WinForms APIs that exist only on .NET 5 and later.
///
/// The AutoCAD 2024 build targets .NET Framework 4.8 and shares these sources,
/// so anything missing there is implemented with the equivalent Win32 call
/// rather than by dropping the feature.
/// </summary>
internal static class UiCompat
{
#if NET48
    private const int EmSetCueBanner = 0x1501;

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr SendMessage(IntPtr window, int message, IntPtr wParam, string lParam);
#endif

    /// <summary>Grey hint text shown while the box is empty.</summary>
    public static TextBox WithHint(this TextBox box, string hint)
    {
#if NET48
        // TextBox.PlaceholderText is .NET 5+; EM_SETCUEBANNER is the same feature on Win32.
        // The handle may not exist yet when fields are initialised, so set it on creation too.
        if (box.IsHandleCreated) SendMessage(box.Handle, EmSetCueBanner, IntPtr.Zero, hint);
        else box.HandleCreated += (_, _) => SendMessage(box.Handle, EmSetCueBanner, IntPtr.Zero, hint);
#else
        box.PlaceholderText = hint;
#endif
        return box;
    }
}
