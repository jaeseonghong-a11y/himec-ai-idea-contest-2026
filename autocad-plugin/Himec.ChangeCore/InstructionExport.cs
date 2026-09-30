using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Himec.ChangeCore;

/// <summary>One instruction as the relation editor reads it.
///
/// The field names are the editor's own ("지시 불러오기" in relation-editor,
/// the same shape tools/pdf_instructions.py writes), so the file opens there
/// without any conversion step.
/// </summary>
public sealed class InstructionItem
{
    [JsonPropertyName("no")] public int No { get; set; }
    [JsonPropertyName("change_id")] public string ChangeId { get; set; } = "";

    /// <summary>"C1 #8E": the spoken name with the handle, the form the editor also parses.</summary>
    [JsonPropertyName("target")] public string Target { get; set; } = "";
    [JsonPropertyName("tag")] public string Tag { get; set; } = "";
    [JsonPropertyName("handle")] public string? Handle { get; set; }
    [JsonPropertyName("grid")] public string? Grid { get; set; }

    /// <summary>"move" only when there is one axis and a finite amount; null otherwise.</summary>
    [JsonPropertyName("action")] public string? Action { get; set; }
    [JsonPropertyName("axis")] public string? Axis { get; set; }
    [JsonPropertyName("delta")] public double? Delta { get; set; }
    [JsonPropertyName("dx")] public double Dx { get; set; }
    [JsonPropertyName("dy")] public double Dy { get; set; }

    [JsonPropertyName("change")] public string Change { get; set; } = "";
    [JsonPropertyName("floor")] public string Floor { get; set; } = "";
    [JsonPropertyName("status")] public string Status { get; set; } = "";
    [JsonPropertyName("status_text")] public string StatusText { get; set; } = "";
    [JsonPropertyName("question")] public string? Question { get; set; }
}

public sealed class InstructionFile
{
    public const string SchemaName = "himec.change-instructions/v1";

    [JsonPropertyName("schema")] public string Schema { get; set; } = SchemaName;
    [JsonPropertyName("source_pdf")] public string SourcePdf { get; set; } = "";

    /// <summary>File name only. A handle means something only inside this drawing.</summary>
    [JsonPropertyName("drawing")] public string Drawing { get; set; } = "";
    [JsonPropertyName("units")] public string Units { get; set; } = "mm";
    [JsonPropertyName("exported_at")] public string ExportedAt { get; set; } = "";
    [JsonPropertyName("items")] public List<InstructionItem> Items { get; set; } = [];
    [JsonPropertyName("notes")] public List<string> Notes { get; set; } = [];
}

/// <summary>Writes the schedule as the instruction file saved next to the PDF.
///
/// The PDF table is for people; reading it back by text position broke whenever a
/// column was added. This file carries the same rows as data. The spoken quote is
/// left out on purpose: it is meeting talk, and the file travels with the drawing.
/// </summary>
public static class InstructionExport
{
    public const string StatusConfirmed = "confirmed";
    public const string StatusNeedsReview = "needs_review";

    private static readonly JsonSerializerOptions Options = new()
    {
        WriteIndented = true,
        // Keep Hangul readable instead of \uXXXX escapes.
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    /// <summary>The instruction file sits next to the PDF under the same name.</summary>
    public static string PathFor(string pdfPath) => Path.ChangeExtension(pdfPath, ".json");

    public static InstructionFile Build(PdfExportPlan plan, string sourcePdf, DateTimeOffset exportedAt)
    {
        if (plan is null) throw new ArgumentNullException(nameof(plan));
        var file = new InstructionFile
        {
            SourcePdf = Path.GetFileName(sourcePdf ?? ""),
            Drawing = Path.GetFileName(plan.Drawing ?? ""),
            ExportedAt = exportedAt.ToString("yyyy-MM-ddTHH:mm:sszzz"),
            Notes = [.. PdfExportPlanner.Questions(plan)],
        };
        foreach (var row in plan.Schedule)
            file.Items.AddRange(Items(row));
        return file;
    }

    public static string Serialize(InstructionFile file) => JsonSerializer.Serialize(file, Options);

    /// <summary>One item per axis. The editor moves one grid line per instruction, so a
    /// diagonal move becomes an X item and a Y item sharing the same number.</summary>
    private static IEnumerable<InstructionItem> Items(PdfScheduleRow row)
    {
        var axes = new List<(string Axis, double Delta)>();
        if (row.Action == "move")
        {
            if (Usable(row.DxMm)) axes.Add(("X", row.DxMm));
            if (Usable(row.DyMm)) axes.Add(("Y", row.DyMm));
        }
        if (axes.Count == 0)
        {
            yield return Item(row, null, null, row.Change);
            yield break;
        }
        foreach (var (axis, delta) in axes)
            yield return Item(row, axis, delta, axes.Count == 1 ? row.Change : $"{axis} {delta:+0.##;-0.##} mm");
    }

    private static InstructionItem Item(PdfScheduleRow row, string? axis, double? delta, string change)
    {
        var confirmed = row.State == PdfExportPlanner.StateConfirmedTarget && row.Handle.Length > 0;
        var tag = row.Target == "미지정" ? "" : row.Target;
        var handle = row.Handle.ToUpperInvariant();
        return new InstructionItem
        {
            No = int.TryParse(row.Marker, out var no) ? no : 0,
            ChangeId = row.ChangeId,
            Target = handle.Length > 0 ? $"{row.Target} #{handle}" : row.Target,
            Tag = tag,
            Handle = handle.Length > 0 ? handle : null,
            Grid = row.Grid.Length > 0 ? row.Grid : null,
            Action = axis is null ? null : "move",
            Axis = axis,
            Delta = delta,
            Dx = Usable(row.DxMm) ? row.DxMm : 0,
            Dy = Usable(row.DyMm) ? row.DyMm : 0,
            Change = change,
            Floor = row.Floor,
            Status = confirmed ? StatusConfirmed : StatusNeedsReview,
            StatusText = row.State,
            Question = confirmed || row.Note.Length == 0 ? null : row.Note,
        };
    }

    private static bool Usable(double mm) => mm != 0 && !double.IsNaN(mm) && !double.IsInfinity(mm);
}
