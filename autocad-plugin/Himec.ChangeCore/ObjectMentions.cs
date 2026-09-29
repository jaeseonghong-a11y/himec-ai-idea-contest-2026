using System.Text.RegularExpressions;

namespace Himec.ChangeCore;

/// <summary>Finds the words in a sentence that point at a drawing object.
///
/// The same two patterns were previously repeated in RecordingTagSession and
/// RealtimeTagging. They are kept here so the tag list, the realtime path and
/// change matching all read a transcript the same way.
/// </summary>
public static class ObjectMentions
{
    private static readonly Regex ExplicitId =
        new(@"(?<![A-Za-z0-9])(?:[CBE]-?\d{1,4})(?![A-Za-z0-9])", RegexOptions.IgnoreCase | RegexOptions.Compiled);

    private static readonly Regex GenericObject =
        new(@"기둥|덕트|배관|장비|(?<![가-힣])보(?=를|가|는|의|\s|$)", RegexOptions.Compiled);

    /// <summary>Split a transcript the way the tag list does.</summary>
    public static IEnumerable<string> Sentences(string transcript) =>
        Regex.Split(transcript ?? "", @"[.!?\r\n]+").Select(s => s.Trim()).Where(s => s.Length > 0);

    /// <summary>Explicit marks such as C1 or B-12, uppercased and de-duplicated.</summary>
    public static string[] ExplicitIds(string sentence) =>
        ExplicitId.Matches(sentence).Cast<Match>().Select(m => m.Value.ToUpperInvariant())
            .Distinct(StringComparer.OrdinalIgnoreCase).ToArray();

    /// <summary>Generic nouns such as 기둥 or 덕트.</summary>
    public static string[] GenericObjects(string sentence) =>
        GenericObject.Matches(sentence).Cast<Match>().Select(m => m.Value).Distinct().ToArray();

    /// <summary>Explicit marks when present, otherwise generic nouns.
    ///
    /// The fallback is exclusive on purpose: a sentence that names C1 is read as
    /// being about C1, not about every noun in it.
    /// </summary>
    public static string[] Labels(string sentence)
    {
        var ids = ExplicitIds(sentence);
        return ids.Length > 0 ? ids : GenericObjects(sentence);
    }

    /// <summary>Compare a transcript label with a drawing identifier.</summary>
    public static string Normalize(string value) =>
        (value ?? "").Trim().Replace("-", "").ToUpperInvariant();
}
