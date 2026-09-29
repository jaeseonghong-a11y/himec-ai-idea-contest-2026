using System.Text.RegularExpressions;
using System.Text.Json.Serialization;

namespace Himec.ChangeCore;

public sealed class RecordingTag
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string Label { get; set; } = "";
    public string SourceQuote { get; set; } = "";
    public double? OffsetSeconds { get; set; }
    public string Origin { get; set; } = "manual";
    public string? ExtractionKey { get; set; }
    public string? Drawing { get; set; }
    public string? Handle { get; set; }
    public string? EntityType { get; set; }
    public string? Layer { get; set; }
    public string? TranscriptTurnId { get; set; }
    public double? ApproximateOffsetSeconds { get; set; }
    public string? SuggestionStatus { get; set; }
    public List<string> CandidateHandles { get; set; } = [];
    public DateTimeOffset? ConfirmedByUserAt { get; set; }
    public bool IsLinked => !string.IsNullOrWhiteSpace(Drawing) && !string.IsNullOrWhiteSpace(Handle);

    // Old session JSON has no SuggestionStatus. Derive its display state without rewriting it.
    [JsonIgnore]
    public string EffectiveSuggestionStatus => SuggestionStatus ?? (IsLinked
        ? RecordingTagSuggestionStatus.DirectLinked
        : RecordingTagSuggestionStatus.SelectionNeeded);
}

public static class RecordingTagSuggestionStatus
{
    public const string DirectLinked = "direct_linked";
    public const string Proposed = "proposed";
    public const string SelectionNeeded = "selection_needed";
    public const string Confirmed = "confirmed";
}

public sealed class RecordingTagSession
{
    private static readonly Regex ExplicitId = new(@"(?<![A-Za-z0-9])(?:[CBE]-?\d{1,4})(?![A-Za-z0-9])", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex GenericObject = new(@"기둥|덕트|배관|장비|(?<![가-힣])보(?=를|가|는|의|\s|$)", RegexOptions.Compiled);

    public string RecordingPath { get; set; } = "";
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.Now;
    public List<RecordingTag> Tags { get; set; } = [];
    public List<string> ProcessedTranscriptTurnIds { get; set; } = [];

    public RecordingTag AddManual(string label, double? offsetSeconds = null)
    {
        var clean = label.Trim();
        if (clean.Length is < 1 or > 80) throw new ArgumentException("태그 이름은 1~80자로 입력하세요.");
        var tag = new RecordingTag { Label = clean, SourceQuote = "사용자 직접 지정", OffsetSeconds = offsetSeconds };
        Tags.Add(tag);
        return tag;
    }

    public int AddTranscriptMentions(string transcript)
    {
        var count = 0;
        foreach (var sentence in Regex.Split(transcript, @"[.!?\r\n]+"))
        {
            var quote = sentence.Trim();
            if (quote.Length == 0) continue;
            var labels = ExplicitId.Matches(quote).Cast<Match>().Select(m => m.Value.ToUpperInvariant()).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
            if (labels.Length == 0)
                labels = GenericObject.Matches(quote).Cast<Match>().Select(m => m.Value).Distinct().ToArray();
            foreach (var label in labels)
            {
                if (Tags.Any(t => t.Origin == "transcript" && t.ExtractionKey == label && t.SourceQuote == quote)) continue;
                Tags.Add(new RecordingTag { Label = label, ExtractionKey = label, SourceQuote = quote, Origin = "transcript" });
                count++;
            }
        }
        return count;
    }

    public void Rename(string id, string label)
    {
        var clean = label.Trim();
        if (clean.Length is < 1 or > 80) throw new ArgumentException("태그 이름은 1~80자로 입력하세요.");
        var tag = Find(id);
        if (tag.SuggestionStatus == RecordingTagSuggestionStatus.Proposed &&
            !string.Equals(tag.Label, clean, StringComparison.OrdinalIgnoreCase))
        {
            // A proposal for the old label must not remain attached after an edit.
            ClearLink(tag);
            tag.CandidateHandles.Clear();
            tag.SuggestionStatus = RecordingTagSuggestionStatus.SelectionNeeded;
        }
        tag.Label = clean;
    }

    public void Link(string id, string drawing, string handle, string entityType, string layer)
    {
        if (string.IsNullOrWhiteSpace(drawing) || string.IsNullOrWhiteSpace(handle))
            throw new ArgumentException("도면과 객체 핸들이 필요합니다.");
        var tag = Find(id);
        tag.Drawing = drawing;
        tag.Handle = handle;
        tag.EntityType = entityType;
        tag.Layer = layer;
        tag.SuggestionStatus = RecordingTagSuggestionStatus.DirectLinked;
        tag.ConfirmedByUserAt = null;
    }

    public void Unlink(string id)
    {
        var tag = Find(id);
        ClearLink(tag);
        tag.SuggestionStatus = RecordingTagSuggestionStatus.SelectionNeeded;
        tag.ConfirmedByUserAt = null;
    }

    public void Confirm(string id, DateTimeOffset confirmedAt)
    {
        var tag = Find(id);
        if (!tag.IsLinked) throw new InvalidOperationException("도면 객체를 먼저 연결하세요.");
        tag.SuggestionStatus = RecordingTagSuggestionStatus.Confirmed;
        tag.ConfirmedByUserAt = confirmedAt;
    }

    public void Remove(string id) => Tags.Remove(Find(id));

    public RecordingTag Find(string id) => Tags.FirstOrDefault(t => t.Id == id)
        ?? throw new KeyNotFoundException("선택한 태그를 찾지 못했습니다.");

    private static void ClearLink(RecordingTag tag)
    {
        tag.Drawing = null;
        tag.Handle = null;
        tag.EntityType = null;
        tag.Layer = null;
    }
}
