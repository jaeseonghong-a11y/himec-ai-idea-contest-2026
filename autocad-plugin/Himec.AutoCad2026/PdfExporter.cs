using System.Globalization;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.PlottingServices;
using Himec.ChangeCore;

namespace Himec.AutoCad2026;

/// <summary>Draws the review markup, plots it to PDF, then takes the markup back out.
///
/// The drawing is a carrier here, not a deliverable: every entity this creates is
/// erased again before the command returns, and nothing is saved. Approval and the
/// actual edit stay outside this path.
/// </summary>
internal static class PdfExporter
{
    internal const string AnnotationLayer = "HIMEC-주석";
    internal const string ScheduleLayer = "HIMEC-일람표";

    internal static string Export(Document doc, PdfExportPlan plan, string outputPath)
    {
        if (doc is null) throw new ArgumentNullException(nameof(doc));
        if (plan is null) throw new ArgumentNullException(nameof(plan));
        if (plan.Schedule.Count == 0) throw new InvalidOperationException("내보낼 변경 항목이 없습니다.");

        var db = doc.Database;
        var created = new List<ObjectId>();
        using var locked = doc.LockDocument();
        try
        {
            using (var tr = db.TransactionManager.StartTransaction())
            {
                EnsureLayer(tr, db, AnnotationLayer, 1);
                EnsureLayer(tr, db, ScheduleLayer, 4);
                var space = (BlockTableRecord)tr.GetObject(db.CurrentSpaceId, OpenMode.ForWrite);

                db.UpdateExt(true);
                var min = db.Extmin;
                var max = db.Extmax;
                var height = Math.Max(max.Y - min.Y, 1.0);
                // Keep the markup readable whatever the sheet size is.
                var textHeight = Math.Max(height / 70.0, 1.0);

                foreach (var annotation in plan.Annotations)
                {
                    var anchor = Anchor(tr, db, annotation.Handle);
                    if (anchor is null) continue;
                    created.AddRange(DrawCallout(tr, space, anchor.Value, annotation, textHeight));
                }
                created.AddRange(DrawSchedule(tr, space, plan, max, textHeight));
                tr.Commit();
            }

            PlotToPdf(doc, outputPath);
            return outputPath;
        }
        finally
        {
            Remove(db, created);
        }
    }

    private static void EnsureLayer(Transaction tr, Database db, string name, short colorIndex)
    {
        var table = (LayerTable)tr.GetObject(db.LayerTableId, OpenMode.ForRead);
        if (table.Has(name)) return;
        table.UpgradeOpen();
        var record = new LayerTableRecord { Name = name, Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(Autodesk.AutoCAD.Colors.ColorMethod.ByAci, colorIndex) };
        table.Add(record);
        tr.AddNewlyCreatedDBObject(record, true);
    }

    /// <summary>Top-centre of the referenced object, or null when the handle is gone.</summary>
    private static Point3d? Anchor(Transaction tr, Database db, string handle)
    {
        if (string.IsNullOrWhiteSpace(handle)) return null;
        if (!long.TryParse(handle, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var value)) return null;
        if (!db.TryGetObjectId(new Handle(value), out var id) || id.IsNull || id.IsErased) return null;
        if (tr.GetObject(id, OpenMode.ForRead) is not Entity entity) return null;
        try
        {
            var extents = entity.GeometricExtents;
            return new Point3d((extents.MinPoint.X + extents.MaxPoint.X) / 2.0, extents.MaxPoint.Y, 0);
        }
        catch (Autodesk.AutoCAD.Runtime.Exception)
        {
            // Entities without geometric extents cannot carry a callout.
            return null;
        }
    }

    private static List<ObjectId> DrawCallout(Transaction tr, BlockTableRecord space,
        Point3d anchor, PdfAnnotation annotation, double textHeight)
    {
        var ids = new List<ObjectId>();
        var tip = new Point3d(anchor.X, anchor.Y + textHeight * 3, 0);

        ids.Add(Add(tr, space, new Line(anchor, tip) { Layer = AnnotationLayer }));
        ids.Add(Add(tr, space, new Circle(tip, Vector3d.ZAxis, textHeight * 0.9) { Layer = AnnotationLayer }));
        ids.Add(Add(tr, space, new MText
        {
            Contents = annotation.Marker,
            Location = tip,
            TextHeight = textHeight,
            Attachment = AttachmentPoint.MiddleCenter,
            Layer = AnnotationLayer,
        }));
        ids.Add(Add(tr, space, new MText
        {
            Contents = annotation.Text,
            Location = new Point3d(tip.X + textHeight * 1.4, tip.Y, 0),
            TextHeight = textHeight,
            Attachment = AttachmentPoint.MiddleLeft,
            Layer = AnnotationLayer,
        }));
        return ids;
    }

    private static List<ObjectId> DrawSchedule(Transaction tr, BlockTableRecord space,
        PdfExportPlan plan, Point3d max, double textHeight)
    {
        var ids = new List<ObjectId>();
        var rowHeight = textHeight * 2.2;
        var left = max.X + textHeight * 6;
        var top = max.Y;
        var width = textHeight * 46;
        var columns = new[] { 0.0, textHeight * 4, textHeight * 12, textHeight * 22, textHeight * 30 };

        ids.Add(Add(tr, space, new MText
        {
            Contents = plan.Title + "  —  " + plan.Drawing,
            Location = new Point3d(left, top + rowHeight, 0),
            TextHeight = textHeight * 1.3,
            Attachment = AttachmentPoint.TopLeft,
            Layer = ScheduleLayer,
        }));

        var y = top;
        WriteRow(tr, space, ids, PdfExportPlanner.Headers, left, y, columns, textHeight, width);
        foreach (var row in plan.Schedule)
        {
            y -= rowHeight;
            WriteRow(tr, space, ids, PdfExportPlanner.Cells(row), left, y, columns, textHeight, width);
        }

        var bottom = top - (plan.Schedule.Count + 1) * rowHeight;
        ids.Add(Add(tr, space, Box(left, bottom, left + width, top + rowHeight * 0.4)));
        ids.Add(Add(tr, space, new Line(
            new Point3d(left, top - rowHeight * 0.6, 0),
            new Point3d(left + width, top - rowHeight * 0.6, 0)) { Layer = ScheduleLayer }));
        ids.Add(Add(tr, space, new MText
        {
            Contents = plan.Footer,
            Location = new Point3d(left, bottom - rowHeight * 0.6, 0),
            TextHeight = textHeight * 0.9,
            Attachment = AttachmentPoint.TopLeft,
            Width = width,
            Layer = ScheduleLayer,
        }));
        return ids;
    }

    private static void WriteRow(Transaction tr, BlockTableRecord space, List<ObjectId> ids,
        IReadOnlyList<string> cells, double left, double y, double[] columns, double textHeight, double width)
    {
        for (var i = 0; i < cells.Count && i < columns.Length; i++)
        {
            var next = i + 1 < columns.Length ? columns[i + 1] : width;
            ids.Add(Add(tr, space, new MText
            {
                Contents = cells[i] ?? "",
                Location = new Point3d(left + columns[i] + textHeight * 0.4, y, 0),
                TextHeight = textHeight * 0.9,
                Attachment = AttachmentPoint.TopLeft,
                Width = Math.Max(next - columns[i] - textHeight * 0.8, textHeight * 2),
                Layer = ScheduleLayer,
            }));
        }
    }

    private static Polyline Box(double x1, double y1, double x2, double y2)
    {
        var box = new Polyline { Layer = ScheduleLayer, Closed = true };
        box.AddVertexAt(0, new Point2d(x1, y1), 0, 0, 0);
        box.AddVertexAt(1, new Point2d(x2, y1), 0, 0, 0);
        box.AddVertexAt(2, new Point2d(x2, y2), 0, 0, 0);
        box.AddVertexAt(3, new Point2d(x1, y2), 0, 0, 0);
        return box;
    }

    private static ObjectId Add(Transaction tr, BlockTableRecord space, Entity entity)
    {
        var id = space.AppendEntity(entity);
        tr.AddNewlyCreatedDBObject(entity, true);
        return id;
    }

    /// <summary>Erase the markup again. Runs even when plotting failed.</summary>
    private static void Remove(Database db, IEnumerable<ObjectId> ids)
    {
        using var tr = db.TransactionManager.StartTransaction();
        foreach (var id in ids)
        {
            if (id.IsNull || id.IsErased) continue;
            if (tr.GetObject(id, OpenMode.ForWrite, false) is Entity entity) entity.Erase();
        }
        tr.Commit();
    }

    private static void PlotToPdf(Document doc, string outputPath)
    {
        var db = doc.Database;
        using var tr = db.TransactionManager.StartTransaction();
        var manager = LayoutManager.Current;
        var layout = (Layout)tr.GetObject(manager.GetLayoutId(manager.CurrentLayout), OpenMode.ForRead);
        var settings = new PlotSettings(layout.ModelType);
        settings.CopyFrom(layout);

        var validator = PlotSettingsValidator.Current;
        validator.SetPlotConfigurationName(settings, "DWG To PDF.pc3", null);
        validator.RefreshLists(settings);
        validator.SetPlotType(settings, Autodesk.AutoCAD.DatabaseServices.PlotType.Extents);
        validator.SetUseStandardScale(settings, true);
        validator.SetStdScaleType(settings, StdScaleType.ScaleToFit);
        validator.SetPlotCentered(settings, true);
        validator.SetPlotPaperUnits(settings, PlotPaperUnit.Millimeters);

        var info = new PlotInfo { Layout = layout.ObjectId, OverrideSettings = settings };
        new PlotInfoValidator { MediaMatchingPolicy = MatchingPolicy.MatchEnabled }.Validate(info);

        using var engine = PlotFactory.CreatePublishEngine();
        using var progress = new PlotProgressDialog(false, 1, true);
        engine.BeginPlot(progress, null);
        engine.BeginDocument(info, doc.Name, null, 1, true, outputPath);
        engine.BeginPage(new PlotPageInfo(), info, true, null);
        engine.BeginGenerateGraphics(null);
        engine.EndGenerateGraphics(null);
        engine.EndPage(null);
        engine.EndDocument(null);
        engine.EndPlot(null);
        tr.Commit();
    }
}
