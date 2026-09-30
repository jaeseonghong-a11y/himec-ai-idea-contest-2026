#if NET48
// C# records and `init` accessors need this marker type, which .NET Framework
// does not ship. Declaring it here lets the shared sources compile unchanged
// for the AutoCAD 2024 build. It has no effect on the net8.0 build.
namespace System.Runtime.CompilerServices
{
    internal static class IsExternalInit
    {
    }
}
#endif
