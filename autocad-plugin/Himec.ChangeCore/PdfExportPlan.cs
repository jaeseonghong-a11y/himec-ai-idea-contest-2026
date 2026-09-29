namespace Himec.ChangeCore;

/// <summary>One callout drawn on top of the object it refers to.</summary>
public sealed class PdfAnnotation
{
    public string ChangeId { get; set; } = "";
    public string Marker { get; set; } = "";
    public string Handle { get; set; } = "";
    public string Drawing { get; set; } = "";
    public string Text { get; set; } = "";
}

/// <summary>One line of the schedule printed at the right of the sheet.</summary>
public sealed class PdfScheduleRow
{
    public string Marker { get; set; } = "";
    public string Target { get; set; } = "";
    public string Change { get; set; } = "";
    public string State { get; set; } = "";
    public string Note { get; set; } = "";
    public string Quote { get; set; } = "";
}

public sealed class PdfExportPlan
{
    public string Drawing { get; set; } = "";
    public string Title { get; set; } = "설계 변경 지시 일람표";
    public List<PdfAnnotation> Annotations { get; set; } = [];
    public List<PdfScheduleRow> Schedule { get; set; } = [];
    public int MatchedCount { get; set; }
    public int QuestionCount { get; set; }

    /// <summary>Printed under the schedule so a reader cannot mistake it for an applied change.</summary>
    public string Footer =>
        $"확정 {MatchedCount}건 · 확인 필요 {QuestionCount}건 · 이 표는 검토용이며 도면은 수정되지 않았습니다.";
}

/// <summary>Turns matched changes into what the exporter has to draw.
///
/// Only a change whose object is settled gets a callout: an unresolved one has
/// no place on the drawing, so it appears in the schedule as a question instead
/// of being pinned to a guessed location.
/// </summary>
public static class PdfExportPlanner
{
    public const string StateConfirmedTarget = "대상 확정";
    public const string StateQuestion = "확인 필요";

    public static PdfExportPlan Build(IReadOnlyList<MatchedChange> changes, string drawing)
    {
        if (changes is null) throw new ArgumentNullException(nameof(changes));
        var plan = new PdfExportPlan { Drawing = drawing ?? "" };
        var number = 0;
        foreach (var change in changes)
        {
            number++;
            var marker = number.ToString();
            var target = change.Labels.Count > 0 ? string.Join(", ", change.Labels) : "미지정";
            var move = ChangeMatching.Describe(change);
            if (change.IsMatched)
            {
                plan.MatchedCount++;
                plan.Annotations.Add(new PdfAnnotation
                {
                    ChangeId = change.Id,
                    Marker = marker,
                    Handle = change.Handle ?? "",
                    Drawing = change.Drawing ?? drawing ?? "",
                    Text = $"[{marker}] {target}  {move}",
                });
                plan.Schedule.Add(new PdfScheduleRow
                {
                    Marker = marker,
                    Target = target,
                    Change = move,
                    State = StateConfirmedTarget,
                    Note = $"handle {change.Handle}",
                    Quote = change.SourceQuote,
                });
                continue;
            }
            plan.QuestionCount++;
            plan.Schedule.Add(new PdfScheduleRow
            {
                Marker = marker,
                Target = target,
                Change = move,
                State = StateQuestion,
                Note = change.Question ?? "",
                Quote = change.SourceQuote,
            });
        }
        return plan;
    }

    /// <summary>Column headers for the schedule, left to right.</summary>
    public static IReadOnlyList<string> Headers => ["번호", "대상", "변경", "상태", "비고"];

    /// <summary>The cells of one row, matching <see cref="Headers"/>.</summary>
    public static IReadOnlyList<string> Cells(PdfScheduleRow row) =>
        [row.Marker, row.Target, row.Change, row.State, row.Note];
}
