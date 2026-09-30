namespace Himec.ChangeCore;

public sealed record CompletedTranscriptTurn(string Id, string Text, double ApproximateOffsetSeconds);

// Only identifiers supplied by the local drawing index are considered. No drawing data is sent to STT.
public sealed record RecordingObjectCandidate(
    string Drawing,
    string Handle,
    IReadOnlyList<string> Identifiers,
    string EntityType,
    string Layer);

public static class RealtimeTagging
{
    public static IReadOnlyList<RecordingTag> AddCompletedTurn(
        RecordingTagSession session,
        CompletedTranscriptTurn turn,
        string currentDrawing,
        IEnumerable<RecordingObjectCandidate> drawingCandidates)
    {
        if (session is null) throw new ArgumentNullException(nameof(session));
        if (turn is null) throw new ArgumentNullException(nameof(turn));
        if (drawingCandidates is null) throw new ArgumentNullException(nameof(drawingCandidates));
        if (string.IsNullOrWhiteSpace(turn.Id)) throw new ArgumentException("전사 문장 ID가 필요합니다.");
        if (double.IsNaN(turn.ApproximateOffsetSeconds) || double.IsInfinity(turn.ApproximateOffsetSeconds) ||
            turn.ApproximateOffsetSeconds < 0) throw new ArgumentOutOfRangeException(nameof(turn));
        if (string.IsNullOrWhiteSpace(currentDrawing)) throw new ArgumentException("현재 도면 이름이 필요합니다.");
        if (session.ProcessedTranscriptTurnIds.Contains(turn.Id, StringComparer.Ordinal) ||
            session.Tags.Any(t => t.TranscriptTurnId == turn.Id)) return [];

        var quote = turn.Text.Trim();
        if (quote.Length == 0)
        {
            session.ProcessedTranscriptTurnIds.Add(turn.Id);
            return [];
        }
        var ids = ObjectMentions.ExplicitIds(quote);
        var labels = ObjectMentions.Labels(quote);
        var candidates = drawingCandidates.Where(c =>
            string.Equals(c.Drawing, currentDrawing, StringComparison.OrdinalIgnoreCase) &&
            !string.IsNullOrWhiteSpace(c.Handle)).ToArray();
        var added = new List<RecordingTag>();

        foreach (var label in labels)
        {
            RecordingObjectCandidate[] matches = ids.Length == 0 ? [] : candidates
                .Where(c => c.Identifiers.Any(i => ObjectMentions.Normalize(i) == ObjectMentions.Normalize(label)))
                .GroupBy(c => c.Handle, StringComparer.OrdinalIgnoreCase)
                .Select(g => g.First())
                .OrderBy(c => c.Handle, StringComparer.OrdinalIgnoreCase)
                .ToArray();
            var tag = new RecordingTag
            {
                Label = label,
                SourceQuote = quote,
                Origin = "realtime_transcript",
                ExtractionKey = label,
                TranscriptTurnId = turn.Id,
                ApproximateOffsetSeconds = turn.ApproximateOffsetSeconds,
                CandidateHandles = matches.Select(c => c.Handle).ToList(),
                SuggestionStatus = matches.Length == 1
                    ? RecordingTagSuggestionStatus.Proposed
                    : RecordingTagSuggestionStatus.SelectionNeeded
            };
            if (matches.Length == 1)
            {
                tag.Drawing = matches[0].Drawing;
                tag.Handle = matches[0].Handle;
                tag.EntityType = matches[0].EntityType;
                tag.Layer = matches[0].Layer;
            }
            session.Tags.Add(tag);
            added.Add(tag);
        }
        session.ProcessedTranscriptTurnIds.Add(turn.Id);
        return added;
    }
}
