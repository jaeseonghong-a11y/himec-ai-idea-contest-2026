using System.Text.RegularExpressions;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;

namespace Himec.AutoCad2026;

/// <summary>Reads the grid bubbles drawn on the sheet and names the intersection an object sits on.
///
/// The names are taken from the drawing, not computed: whatever the drafter labelled the
/// axes is what the schedule prints, so the plugin and anyone reading the sheet agree.
/// Nothing is invented — an object away from any labelled axis simply gets no name.
/// </summary>
internal static class DrawingGrid
{
    private static readonly Regex AxisLabel = new(@"^\s*(?<axis>[XY])\s*(?<n>\d{1,3})\s*$",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    internal sealed class Axis
    {
        public string Name = "";
        public double Coordinate;
    }

    internal sealed class Grid
    {
        public List<Axis> Vertical = [];     // X labels: the axis runs vertically, placed along X
        public List<Axis> Horizontal = [];   // Y labels: the axis runs horizontally, placed along Y
        public bool IsEmpty => Vertical.Count == 0 && Horizontal.Count == 0;
    }

    /// <summary>Collect axis labels such as X1 or Y2 from the current space.</summary>
    internal static Grid Read(Transaction tr, Database db)
    {
        var grid = new Grid();
        var space = (BlockTableRecord)tr.GetObject(db.CurrentSpaceId, OpenMode.ForRead);
        foreach (ObjectId id in space)
        {
            var entity = tr.GetObject(id, OpenMode.ForRead);
            string text;
            Point3d at;
            switch (entity)
            {
                case MText mtext:
                    text = mtext.Contents;
                    at = mtext.Location;
                    break;
                case DBText dbtext:
                    text = dbtext.TextString;
                    at = dbtext.Position;
                    break;
                default:
                    continue;
            }
            var match = AxisLabel.Match(text ?? "");
            if (!match.Success) continue;
            var name = match.Groups["axis"].Value.ToUpperInvariant() + match.Groups["n"].Value;
            var axis = new Axis { Name = name, Coordinate = name[0] == 'X' ? at.X : at.Y };
            (name[0] == 'X' ? grid.Vertical : grid.Horizontal).Add(axis);
        }
        grid.Vertical.Sort((a, b) => a.Coordinate.CompareTo(b.Coordinate));
        grid.Horizontal.Sort((a, b) => a.Coordinate.CompareTo(b.Coordinate));
        return grid;
    }

    /// <summary>Name of the intersection nearest to a point, e.g. "X1-Y2".
    ///
    /// Returns an empty string unless the point is close to one axis of each direction.
    /// "Close" is half the smallest spacing between neighbouring axes, so a column on the
    /// grid is named and one clearly off it is not.
    /// </summary>
    internal static string NameAt(Grid grid, Point3d point)
    {
        var x = Nearest(grid.Vertical, point.X);
        var y = Nearest(grid.Horizontal, point.Y);
        if (x is null || y is null) return "";
        return $"{x.Name}-{y.Name}";
    }

    private static Axis? Nearest(List<Axis> axes, double value)
    {
        if (axes.Count == 0) return null;
        var tolerance = Tolerance(axes);
        Axis? best = null;
        var bestGap = double.MaxValue;
        foreach (var axis in axes)
        {
            var gap = Math.Abs(axis.Coordinate - value);
            if (gap < bestGap) { bestGap = gap; best = axis; }
        }
        return bestGap <= tolerance ? best : null;
    }

    private static double Tolerance(List<Axis> axes)
    {
        if (axes.Count < 2) return double.MaxValue;   // a single axis cannot be mistaken for another
        var smallest = double.MaxValue;
        for (var i = 1; i < axes.Count; i++)
            smallest = Math.Min(smallest, Math.Abs(axes[i].Coordinate - axes[i - 1].Coordinate));
        return smallest / 2;
    }
}
