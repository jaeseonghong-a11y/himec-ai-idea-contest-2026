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
    internal const string BorderLayer = "HIMEC-테두리";

    /// <summary>A3 landscape proportion (420 x 297 mm).</summary>
    private const double A3Ratio = 420.0 / 297.0;
    private const double A3WidthMm = 420.0;
    private const double BorderInsetMm = 3.0;

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
        // Markup left by an earlier export would otherwise stack up: each run drew a new
        // set over the old one, so the sheet ended up with several schedules at once.
        EraseMarkup(doc);
        try
        {
            using (var tr = db.TransactionManager.StartTransaction())
            {
                _textStyle = EnsureTextStyle(tr, db);
                EnsureLayer(tr, db, AnnotationLayer, 6);
                EnsureLayer(tr, db, ScheduleLayer, 8);
                var space = (BlockTableRecord)tr.GetObject(db.CurrentSpaceId, OpenMode.ForWrite);

                db.UpdateExt(true);
                var min = db.Extmin;
                var max = db.Extmax;
                // Sized from the longer side: a wide, short drawing made the markup
                // unreadable when this was based on height alone.
                var span = Math.Max(Math.Max(max.X - min.X, max.Y - min.Y), 1.0);
                var textHeight = Math.Max(span / 60.0, 1.0);

                var grid = DrawingGrid.Read(tr, db);
                foreach (var annotation in plan.Annotations)
                {
                    var anchor = Anchor(tr, db, annotation.Handle);
                    if (anchor is null) continue;
                    // The grid name comes from the sheet's own axis bubbles, so the schedule
                    // and the drawing call the same intersection by the same name.
                    var at = Position(tr, db, annotation.Handle) ?? anchor.Value;
                    annotation.Grid = grid.IsEmpty ? "" : DrawingGrid.NameAt(grid, at);
                    annotation.Text = PdfExportPlanner.Callout(
                        annotation.Label, annotation.Grid, annotation.Move, annotation.Handle);
                    foreach (var row in plan.Schedule)
                        if (row.Handle == annotation.Handle) row.Grid = annotation.Grid;
                    created.AddRange(DrawCallout(tr, space, anchor.Value, annotation, textHeight));
                }
                created.AddRange(DrawSchedule(tr, space, plan, min, max, textHeight));
                tr.Commit();
            }

            // The sheet box is decided after the markup exists, so the border encloses
            // everything instead of cutting through the schedule.
            var window = SheetBox(db);
            using (var tr = db.TransactionManager.StartTransaction())
            {
                EnsureLayer(tr, db, BorderLayer, 8);
                var space = (BlockTableRecord)tr.GetObject(db.CurrentSpaceId, OpenMode.ForWrite);
                var inset = (window.MaxPoint.X - window.MinPoint.X) * BorderInsetMm / A3WidthMm;
                var border = new Polyline { Layer = BorderLayer, Closed = true };
                border.AddVertexAt(0, new Point2d(window.MinPoint.X + inset, window.MinPoint.Y + inset), 0, 0, 0);
                border.AddVertexAt(1, new Point2d(window.MaxPoint.X - inset, window.MinPoint.Y + inset), 0, 0, 0);
                border.AddVertexAt(2, new Point2d(window.MaxPoint.X - inset, window.MaxPoint.Y - inset), 0, 0, 0);
                border.AddVertexAt(3, new Point2d(window.MinPoint.X + inset, window.MaxPoint.Y - inset), 0, 0, 0);
                created.Add(Add(tr, space, border));

                // When the sheet was produced. Review copies get compared side by side,
                // so the minute matters more than the seconds.
                var stampHeight = (window.MaxPoint.Y - window.MinPoint.Y) / 75;
                var margin = inset + stampHeight;
                created.Add(Add(tr, space, new MText
                {
                    Contents = Escape("생성 " + DateTime.Now.ToString("yyyy-MM-dd HH:mm")),
                    Location = new Point3d(window.MaxPoint.X - margin, window.MaxPoint.Y - margin, 0),
                    TextHeight = stampHeight,
                    Attachment = AttachmentPoint.TopRight,
                    TextStyleId = _textStyle,
                    Layer = BorderLayer,
                }));
                tr.Commit();
            }

            PlotToPdf(doc, outputPath, window);
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

    /// <summary>The plotted area: everything drawn, padded, then grown to A3 proportions.
    ///
    /// Growing the box rather than the paper keeps the sheet the same shape whatever the
    /// drawing's own aspect is, so two exports print at the same proportion.
    /// </summary>
    private static Extents3d SheetBox(Database db)
    {
        db.UpdateExt(true);
        var min = db.Extmin;
        var max = db.Extmax;
        var width = Math.Max(max.X - min.X, 1.0);
        var height = Math.Max(max.Y - min.Y, 1.0);
        // Keep the border clear of the content.
        var pad = Math.Max(width, height) * 0.03;
        width += pad * 2;
        height += pad * 2;
        var cx = (min.X + max.X) / 2;
        var cy = (min.Y + max.Y) / 2;
        if (width / height < A3Ratio) width = height * A3Ratio;
        else height = width / A3Ratio;
        return new Extents3d(
            new Point3d(cx - width / 2, cy - height / 2, 0),
            new Point3d(cx + width / 2, cy + height / 2, 0));
    }

    private static void EnsureLayer(Transaction tr, Database db, string name, short colorIndex)
    {
        var colour = Autodesk.AutoCAD.Colors.Color.FromColorIndex(
            Autodesk.AutoCAD.Colors.ColorMethod.ByAci, colorIndex);
        var table = (LayerTable)tr.GetObject(db.LayerTableId, OpenMode.ForRead);
        if (table.Has(name))
        {
            // Also correct an existing layer: a drawing marked up by an older build keeps
            // the old colour otherwise, and the markup stays hard to tell from the drawing.
            var existing = (LayerTableRecord)tr.GetObject(table[name], OpenMode.ForWrite);
            if (existing.Color.ColorIndex != colorIndex) existing.Color = colour;
            return;
        }
        table.UpgradeOpen();
        var record = new LayerTableRecord { Name = name, Color = colour };
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

    /// <summary>Where the object sits, for deciding which grid intersection it is on.</summary>
    private static Point3d? Position(Transaction tr, Database db, string handle)
    {
        if (!long.TryParse(handle, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var value)) return null;
        if (!db.TryGetObjectId(new Handle(value), out var id) || id.IsNull || id.IsErased) return null;
        if (tr.GetObject(id, OpenMode.ForRead) is not Entity entity) return null;
        if (entity is BlockReference block) return block.Position;
        try
        {
            var extents = entity.GeometricExtents;
            return new Point3d((extents.MinPoint.X + extents.MaxPoint.X) / 2,
                               (extents.MinPoint.Y + extents.MaxPoint.Y) / 2, 0);
        }
        catch (Autodesk.AutoCAD.Runtime.Exception) { return null; }
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
        var width = textHeight * 52;
        var columns = new[] { 0.0, textHeight * 3.5, textHeight * 11, textHeight * 18, textHeight * 28, textHeight * 33, textHeight * 41 };
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
        using var locked = doc.LockDocument();
        return EraseMarkup(doc);
    }

    /// <summary>Erase the markup. The caller already holds the document lock.</summary>
    private static int EraseMarkup(Document doc)
    {
        var db = doc.Database;
        var erased = 0;
        using var tr = db.TransactionManager.StartTransaction();
        var space = (BlockTableRecord)tr.GetObject(db.CurrentSpaceId, OpenMode.ForRead);
        foreach (var id in space)
        {
            if (tr.GetObject(id, OpenMode.ForRead) is not Entity entity) continue;
            if (!entity.Layer.StartsWith("HIMEC-", StringComparison.Ordinal)) continue;
            entity.UpgradeOpen();
            entity.Erase();
            erased++;
        }
        tr.Commit();
        return erased;
    }

    /// <summary>Pick an A3 sheet if the driver offers one. The window already carries the
    /// proportion, so falling back to the default paper only changes the printed size.</summary>
    private static void TrySetA3(PlotSettingsValidator validator, PlotSettings settings)
    {
        try
        {
            foreach (var media in validator.GetCanonicalMediaNameList(settings))
            {
                var name = media?.ToString() ?? "";
                if (name.IndexOf("A3", StringComparison.OrdinalIgnoreCase) < 0) continue;
                validator.SetCanonicalMediaName(settings, name);
                return;
            }
        }
        catch (Autodesk.AutoCAD.Runtime.Exception)
        {
            // Keep the layout's paper; the window still gives the A3 proportion.
        }
    }

    private static void PlotToPdf(Document doc, string outputPath, Extents3d window)
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
        TrySetA3(validator, settings);
        validator.SetPlotWindowArea(settings, new Extents2d(
            window.MinPoint.X, window.MinPoint.Y, window.MaxPoint.X, window.MaxPoint.Y));
        validator.SetPlotType(settings, Autodesk.AutoCAD.DatabaseServices.PlotType.Window);
        validator.SetUseStandardScale(settings, true);
        validator.SetStdScaleType(settings, StdScaleType.ScaleToFit);
        validator.SetPlotCentered(settings, true);
        validator.SetPlotPaperUnits(settings, PlotPaperUnit.Millimeters);

        // A3 media is often listed portrait first; rotate rather than guess at the name.
        var paper = settings.PlotPaperSize;
        if (paper.Y > paper.X) validator.SetPlotRotation(settings, PlotRotation.Degrees090);

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
