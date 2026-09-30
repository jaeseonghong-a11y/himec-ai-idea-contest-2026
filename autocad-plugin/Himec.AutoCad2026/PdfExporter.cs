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
    internal const string TextStyleName = "HIMEC-TEXT";
    internal const string AnnotationLayer = "HIMEC-주석";
    internal const string ScheduleLayer = "HIMEC-일람표";

    /// <summary>Plotter configurations to try, best first.
    ///
    /// "Include layer information" lives in the PDF driver's own options and cannot be
    /// set through the .NET API, so a PC3 saved with it enabled is preferred when the
    /// user has made one. With it, the markup layers can be switched off in the PDF
    /// viewer. Falling back to the stock driver still produces a PDF, just without layers.
    /// </summary>
    private static readonly string[] Devices = ["HIMEC PDF (layers).pc3", "DWG To PDF.pc3"];

    /// <summary>The plot configuration used by the last export.</summary>
    internal static string LastDeviceUsed { get; private set; } = "";

    private static ObjectId _textStyle = ObjectId.Null;

    internal static string Export(Document doc, PdfExportPlan plan, string outputPath, bool keepMarkup)
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
                _textStyle = EnsureTextStyle(tr, db);
                EnsureLayer(tr, db, AnnotationLayer, 1);
                EnsureLayer(tr, db, ScheduleLayer, 4);
                var space = (BlockTableRecord)tr.GetObject(db.CurrentSpaceId, OpenMode.ForWrite);

                db.UpdateExt(true);
                var min = db.Extmin;
                var max = db.Extmax;
                // Sized from the longer side: a wide, short drawing made the markup
                // unreadable when this was based on height alone.
                var span = Math.Max(Math.Max(max.X - min.X, max.Y - min.Y), 1.0);
                var textHeight = Math.Max(span / 60.0, 1.0);

                foreach (var annotation in plan.Annotations)
                {
                    var anchor = Anchor(tr, db, annotation.Handle);
                    if (anchor is null) continue;
                    created.AddRange(DrawCallout(tr, space, anchor.Value, annotation, textHeight));
                }
                created.AddRange(DrawSchedule(tr, space, plan, min, max, textHeight));
                tr.Commit();
            }

            PlotToPdf(doc, outputPath);
            return outputPath;
        }
        finally
        {
            // Kept on request so the reviewer can see the callouts in the drawing.
            // HIMEC_PDF_CLEAR removes them again; the drawing is never saved here.
            if (!keepMarkup) Remove(db, created);
        }
    }

    /// <summary>A TrueType style for the markup.
    ///
    /// The drawing's default style is usually an SHX font, which AutoCAD can only stroke
    /// for Latin text and has to substitute for Hangul. That mixes hairline Latin with
    /// solid Hangul on the same line, and leaves the Latin unsearchable in the PDF.
    /// One TrueType face covering both scripts keeps the weight even.
    /// </summary>
    private static ObjectId EnsureTextStyle(Transaction tr, Database db)
    {
        var table = (TextStyleTable)tr.GetObject(db.TextStyleTableId, OpenMode.ForRead);
        if (table.Has(TextStyleName)) return table[TextStyleName];
        table.UpgradeOpen();
        var style = new TextStyleTableRecord
        {
            Name = TextStyleName,
            FileName = "malgun.ttf",
            Font = new Autodesk.AutoCAD.GraphicsInterface.FontDescriptor("Malgun Gothic", false, false, 0, 0),
        };
        var id = table.Add(style);
        tr.AddNewlyCreatedDBObject(style, true);
        return id;
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
        // A 45-degree leader instead of a vertical one: dimension lines run horizontally
        // and vertically above the object, and a straight-up leader lands on top of them.
        var reach = textHeight * 2.6;
        var tip = new Point3d(anchor.X + reach, anchor.Y + reach, 0);
        var radius = textHeight * 0.9;
        // Stop at the bubble edge rather than running through it to the centre.
        var stop = tip - (tip - anchor).GetNormal() * radius;

        ids.Add(Add(tr, space, new Line(anchor, stop) { Layer = AnnotationLayer }));
        ids.Add(Add(tr, space, new Circle(tip, Vector3d.ZAxis, radius) { Layer = AnnotationLayer }));
        ids.Add(Add(tr, space, new MText
        {
            Contents = Escape(annotation.Marker),
            Location = tip,
            TextHeight = textHeight,
            Attachment = AttachmentPoint.MiddleCenter,
            TextStyleId = _textStyle,
            Layer = AnnotationLayer,
        }));
        ids.Add(Add(tr, space, new MText
        {
            Contents = Escape(annotation.Text),
            Location = new Point3d(tip.X + radius + textHeight * 0.5, tip.Y, 0),
            TextHeight = textHeight,
            Attachment = AttachmentPoint.MiddleLeft,
            TextStyleId = _textStyle,
            Layer = AnnotationLayer,
        }));
        return ids;
    }

    private static List<ObjectId> DrawSchedule(Transaction tr, BlockTableRecord space,
        PdfExportPlan plan, Point3d min, Point3d max, double textHeight)
    {
        var ids = new List<ObjectId>();
        var rowHeight = textHeight * 2.0;
        var left = max.X + textHeight * 8;
        var width = textHeight * 40;
        var columns = new[] { 0.0, textHeight * 3.5, textHeight * 11, textHeight * 21, textHeight * 27 };
        var questions = PdfExportPlanner.Questions(plan);

        var titleHeight = rowHeight * 1.5;
        var tableHeight = (plan.Schedule.Count + 1) * rowHeight;
        // Wrapped text needs room proportional to its length: a fixed block let the
        // longest question run over the footer.
        var questionHeight = questions.Sum(q => BlockHeight(q, width, textHeight)) + rowHeight * 0.4;
        var footerHeight = rowHeight * 1.6;

        // Bottom-aligned with the drawing so the block reads as a lower-right schedule.
        var bottom = min.Y;
        var top = bottom + titleHeight + tableHeight + questionHeight + footerHeight;

        var sheet = string.IsNullOrWhiteSpace(plan.Drawing) ? "" : Path.GetFileName(plan.Drawing);
        ids.Add(Add(tr, space, Text(plan.Title + "  —  " + sheet,
            left, top, textHeight * 1.3, width)));

        // Each row owns a band of rowHeight; cells are centred inside their own band.
        var tableTop = top - titleHeight;
        var band = tableTop;
        WriteRow(tr, space, ids, PdfExportPlanner.Headers, left, band, columns, textHeight, width, rowHeight);
        foreach (var row in plan.Schedule)
        {
            band -= rowHeight;
            WriteRow(tr, space, ids, PdfExportPlanner.Cells(row), left, band, columns, textHeight, width, rowHeight);
        }

        var tableBottom = tableTop - tableHeight;
        ids.Add(Add(tr, space, Box(left, tableBottom, left + width, tableTop)));
        var headerLine = tableTop - rowHeight;
        ids.Add(Add(tr, space, new Line(
            new Point3d(left, headerLine, 0),
            new Point3d(left + width, headerLine, 0)) { Layer = ScheduleLayer }));

        // A question is a sentence, not a cell value: printing it full width under the
        // table keeps it from running over the neighbouring columns.
        var y = tableBottom - rowHeight * 0.9;
        foreach (var question in questions)
        {
            ids.Add(Add(tr, space, Text(question, left, y, textHeight * 0.85, width)));
            y -= BlockHeight(question, width, textHeight);
        }
        ids.Add(Add(tr, space, Text(plan.Footer, left, y - rowHeight * 0.5, textHeight * 0.85, width)));
        return ids;
    }

    private static void WriteRow(Transaction tr, BlockTableRecord space, List<ObjectId> ids,
        IReadOnlyList<string> cells, double left, double bandTop, double[] columns,
        double textHeight, double width, double rowHeight)
    {
        var middle = bandTop - rowHeight / 2;
        for (var i = 0; i < cells.Count && i < columns.Length; i++)
        {
            // An empty cell used to leave an invisible MText behind: it cannot be picked
            // on screen, so it survived manual cleanup and stayed in the drawing.
            if (string.IsNullOrWhiteSpace(cells[i])) continue;
            var next = i + 1 < columns.Length ? columns[i + 1] : width;
            ids.Add(Add(tr, space, new MText
            {
                Contents = Escape(cells[i]),
                Location = new Point3d(left + columns[i] + textHeight * 0.4, middle, 0),
                TextHeight = textHeight * 0.9,
                Attachment = AttachmentPoint.MiddleLeft,
                Width = Math.Max(next - columns[i] - textHeight * 0.8, textHeight * 2),
                TextStyleId = _textStyle,
                Layer = ScheduleLayer,
            }));
        }
    }

    private static MText Text(string? contents, double x, double y, double height, double width) => new()
    {
        Contents = Escape(contents),
        Location = new Point3d(x, y, 0),
        TextHeight = height,
        Attachment = AttachmentPoint.TopLeft,
        Width = width,
        TextStyleId = _textStyle,
        Layer = ScheduleLayer,
    };

    /// <summary>Rough height of wrapped text. Estimated from character count because the
    /// real extent is only known after the MText is added to the database.</summary>
    private static double BlockHeight(string text, double width, double textHeight)
    {
        var perLine = Math.Max(1, (int)(width / (textHeight * 0.75)));
        var lines = Math.Max(1, (int)Math.Ceiling((text ?? "").Length / (double)perLine));
        return lines * textHeight * 1.5;
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

    /// <summary>MText reads a backslash as a format code, so a Windows path or a
    /// brace in the transcript would silently disappear from the sheet.</summary>
    private static string Escape(string? text) => (text ?? "")
        .Replace("\\", "\\\\").Replace("{", "\\{").Replace("}", "\\}");

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

    /// <summary>Erase every entity this exporter left on its two layers.</summary>
    internal static int ClearMarkup(Document doc)
    {
        var db = doc.Database;
        var erased = 0;
        using var locked = doc.LockDocument();
        using var tr = db.TransactionManager.StartTransaction();
        var space = (BlockTableRecord)tr.GetObject(db.CurrentSpaceId, OpenMode.ForRead);
        foreach (var id in space)
        {
            if (tr.GetObject(id, OpenMode.ForRead) is not Entity entity) continue;
            if (entity.Layer != AnnotationLayer && entity.Layer != ScheduleLayer) continue;
            entity.UpgradeOpen();
            entity.Erase();
            erased++;
        }
        tr.Commit();
        return erased;
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
        var chosen = "";
        foreach (var device in Devices)
        {
            try
            {
                validator.SetPlotConfigurationName(settings, device, null);
                chosen = device;
                break;
            }
            catch (Autodesk.AutoCAD.Runtime.Exception)
            {
                // Not installed on this machine; try the next one.
            }
        }
        if (chosen.Length == 0)
            throw new InvalidOperationException("PDF 플로터를 찾지 못했습니다. DWG To PDF.pc3 설치를 확인하세요.");
        LastDeviceUsed = chosen;
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
