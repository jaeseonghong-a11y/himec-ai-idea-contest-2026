using System.Text.RegularExpressions;

namespace Himec.ChangeCore;

/// <summary>Which floor the meeting was talking about when a sentence was spoken.
///
/// A speaker names the floor once and then keeps saying "이 기둥" for a while. Carrying
/// the last named floor forward turns an unanswerable question into a narrower one.
/// It is only ever a reading of the transcript, never a confirmed target: the reviewer
/// still picks the object.
/// </summary>
public static class TranscriptContext
{
    // 지하 먼저 검사한다. "지하 2층"에서 "2층"만 잡히면 층이 뒤집힌다.
    private static readonly Regex Basement =
        new(@"지하\s*(?<n>\d{1,2})\s*층", RegexOptions.Compiled);

    private static readonly Regex Floor =
        new(@"(?<![\d.])(?<n>\d{1,3})\s*층", RegexOptions.Compiled);

    private static readonly Regex Roof =
        new(@"옥탑|옥상|지붕층|다락", RegexOptions.Compiled);

    /// <summary>The floor a sentence names, or null when it names none.</summary>
    public static string? FloorIn(string sentence)
    {
        if (string.IsNullOrWhiteSpace(sentence)) return null;
        var basement = Basement.Match(sentence);
        if (basement.Success) return $"지하 {basement.Groups["n"].Value}층";

        var roof = Roof.Match(sentence);
        var floor = Floor.Match(sentence);
        // 한 문장에 둘 다 있으면 먼저 나온 쪽을 쓴다.
        if (roof.Success && (!floor.Success || roof.Index < floor.Index)) return roof.Value;
        if (floor.Success) return $"{floor.Groups["n"].Value}층";
        return null;
    }

    /// <summary>Walk the sentences in order and report the floor in force for each one.
    ///
    /// A sentence that names no floor inherits the one before it, which is how the
    /// conversation actually moves from floor to floor.
    /// </summary>
    public static IReadOnlyList<string?> Track(IEnumerable<string> sentences)
    {
        if (sentences is null) throw new ArgumentNullException(nameof(sentences));
        var carried = new List<string?>();
        string? current = null;
        foreach (var sentence in sentences)
        {
            current = FloorIn(sentence) ?? current;
            carried.Add(current);
        }
        return carried;
    }
}
