namespace Himec.ChangeCore;

public static class ChangeMatchState
{
    /// <summary>One linked tag was found for the sentence. Still needs human approval.</summary>
    public const string Matched = "matched";

    /// <summary>The target could not be settled from the transcript. Ask the user.</summary>
    public const string QuestionNeeded = "question";
}

public static class ChangeQuestionKind
{
    public const string NoObjectMentioned = "no_object";
    public const string NoTagFound = "no_tag";
    public const string MultipleTags = "multiple_tags";
    public const string GenericOnly = "generic_only";
    public const string SeveralChangesInSentence = "several_changes";
}

public sealed class MatchedChange
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string SourceQuote { get; set; } = "";
    public string Action { get; set; } = "move";
    public double DxMm { get; set; }
    public double DyMm { get; set; }
    public List<string> Labels { get; set; } = [];
    public string? TagId { get; set; }
    public string? Drawing { get; set; }
    public string? Handle { get; set; }
    public string State { get; set; } = ChangeMatchState.QuestionNeeded;
    public string? QuestionKind { get; set; }
    public string? Question { get; set; }
    public List<string> CandidateTagIds { get; set; } = [];

    public bool IsMatched => State == ChangeMatchState.Matched;
}

/// <summary>Pairs the edits mentioned in a transcript with the objects tagged in the drawing.
///
/// This does not widen object recognition: it reuses the tags the user already
/// has and the same mention patterns the tag list uses. Anything it cannot settle
/// becomes a question for the user rather than a guess.
/// </summary>
public static class ChangeMatching
{
    public static IReadOnlyList<MatchedChange> Extract(
        string transcript, RecordingTagSession session, string currentDrawing)
    {
        if (session is null) throw new ArgumentNullException(nameof(session));
        var results = new List<MatchedChange>();
        if (string.IsNullOrWhiteSpace(transcript)) return results;

        foreach (var sentence in ObjectMentions.Sentences(transcript))
        {
            var moves = InstructionParser.ParseAllMoves(sentence);
            if (moves.Count == 0) continue;

            var labels = ObjectMentions.Labels(sentence);
            var explicitIds = ObjectMentions.ExplicitIds(sentence);
            foreach (var move in moves)
            {
                var item = new MatchedChange
                {
                    SourceQuote = sentence,
                    DxMm = move.DxMm,
                    DyMm = move.DyMm,
                    Labels = labels.ToList(),
                };
                if (moves.Count > 1)
                {
                    // Two edits in one sentence cannot be paired with two labels
                    // reliably, so the user decides instead of the rule guessing.
                    Ask(item, ChangeQuestionKind.SeveralChangesInSentence,
                        $"\"{sentence}\"에 이동 지시가 {moves.Count}건 있습니다. " +
                        $"{Describe(item)}의 대상을 도면에서 직접 선택해 주세요.");
                }
                else
                {
                    Resolve(item, labels, explicitIds, session, currentDrawing);
                }
                results.Add(item);
            }
        }
        return results;
    }

    /// <summary>The items the user still has to answer, in transcript order.</summary>
    public static IReadOnlyList<MatchedChange> Unanswered(IEnumerable<MatchedChange> changes) =>
        changes.Where(c => c.State == ChangeMatchState.QuestionNeeded).ToArray();

    private static void Resolve(MatchedChange item, string[] labels, string[] explicitIds,
        RecordingTagSession session, string currentDrawing)
    {
        if (labels.Length == 0)
        {
            Ask(item, ChangeQuestionKind.NoObjectMentioned,
                $"{Describe(item)} 지시에 대상이 언급되지 않았습니다. 도면에서 직접 선택해 주세요.");
            return;
        }
        if (labels.Length > 1)
        {
            Ask(item, ChangeQuestionKind.MultipleTags,
                $"\"{item.SourceQuote}\"에 대상 후보가 {string.Join(", ", labels)}로 여러 개입니다. " +
                $"{Describe(item)}의 대상을 골라 주세요.");
            return;
        }

        var label = labels[0];
        if (explicitIds.Length == 0)
        {
            // Generic nouns are never auto-linked, matching the recording tag rule.
            Ask(item, ChangeQuestionKind.GenericOnly,
                $"\"{label}\"은 일반 명칭이라 대상을 확정할 수 없습니다. " +
                $"{Describe(item)}의 대상을 도면에서 선택해 주세요.");
            return;
        }

        var matches = session.Tags.Where(t =>
                t.IsLinked &&
                string.Equals(t.Drawing, currentDrawing, StringComparison.OrdinalIgnoreCase) &&
                (ObjectMentions.Normalize(t.Label) == ObjectMentions.Normalize(label) ||
                 ObjectMentions.Normalize(t.ExtractionKey ?? "") == ObjectMentions.Normalize(label)))
            .GroupBy(t => t.Handle, StringComparer.OrdinalIgnoreCase)
            .Select(g => g.First())
            .OrderBy(t => t.Handle, StringComparer.OrdinalIgnoreCase)
            .ToArray();

        if (matches.Length == 1)
        {
            item.State = ChangeMatchState.Matched;
            item.TagId = matches[0].Id;
            item.Drawing = matches[0].Drawing;
            item.Handle = matches[0].Handle;
            item.CandidateTagIds = [matches[0].Id];
            return;
        }
        item.CandidateTagIds = matches.Select(t => t.Id).ToList();
        if (matches.Length == 0)
        {
            Ask(item, ChangeQuestionKind.NoTagFound,
                $"\"{label}\"에 연결된 도면 객체가 없습니다. {Describe(item)}의 대상을 도면에서 선택해 주세요.");
            return;
        }
        Ask(item, ChangeQuestionKind.MultipleTags,
            $"\"{label}\"에 연결된 객체가 {matches.Length}개입니다. {Describe(item)}의 대상을 골라 주세요.");
    }

    private static void Ask(MatchedChange item, string kind, string question)
    {
        item.State = ChangeMatchState.QuestionNeeded;
        item.QuestionKind = kind;
        item.Question = question;
        item.TagId = null;
        item.Drawing = null;
        item.Handle = null;
    }

    /// <summary>Human-readable move, e.g. "Y +300 mm".</summary>
    public static string Describe(MatchedChange item)
    {
        var parts = new List<string>();
        if (item.DxMm != 0) parts.Add($"X {item.DxMm:+0.##;-0.##} mm");
        if (item.DyMm != 0) parts.Add($"Y {item.DyMm:+0.##;-0.##} mm");
        return parts.Count == 0 ? "이동 없음" : string.Join(" / ", parts);
    }
}
