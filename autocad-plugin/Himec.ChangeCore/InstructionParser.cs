using System.Globalization;
using System.Text.RegularExpressions;

namespace Himec.ChangeCore;

public static class InstructionParser
{
    // This small rule is intentionally not marketed as LLM understanding.
    private static readonly Regex Movement = new(
        @"(?<direction>위|아래|왼쪽|오른쪽)(?:로|으로)?\s*(?<amount>\d+(?:[.,]\d+)?)\s*(?<unit>mm|밀리미터|cm|센티미터|센치|m|미터)",
        RegexOptions.Compiled | RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

    public static bool TryParseMove(string sourceText, out ChangeInstruction? instruction, out string reason)
    {
        instruction = null;
        reason = "";
        if (string.IsNullOrWhiteSpace(sourceText))
        {
            reason = "회의 발화가 비어 있습니다.";
            return false;
        }

        var match = Movement.Match(sourceText);
        if (!match.Success)
        {
            reason = "이동 방향과 수치를 확인할 수 없습니다. 현재는 '위로 30cm' 같은 한 건의 이동만 지원합니다.";
            return false;
        }

        if (!TryBuild(match, sourceText, out instruction))
        {
            reason = "이동량이 유효하지 않습니다.";
            return false;
        }
        reason = "대상 객체를 아직 확정하지 않았습니다. 도면에서 직접 선택하고 검토해야 합니다.";
        return true;
    }

    /// <summary>Every movement phrase in the text, in the order it was spoken.
    ///
    /// TryParseMove returns only the first one, which is what the single-change
    /// palette flow uses. Change matching needs them all so a transcript that
    /// mentions several edits does not silently lose the rest.
    /// </summary>
    public static IReadOnlyList<ChangeInstruction> ParseAllMoves(string sourceText)
    {
        var found = new List<ChangeInstruction>();
        if (string.IsNullOrWhiteSpace(sourceText)) return found;
        foreach (Match match in Movement.Matches(sourceText))
        {
            // An out-of-range amount is dropped rather than clamped: a wrong number
            // must not turn into a drawing edit.
            if (TryBuild(match, sourceText, out var instruction) && instruction is not null)
                found.Add(instruction);
        }
        return found;
    }

    private static bool TryBuild(Match match, string sourceText, out ChangeInstruction? instruction)
    {
        instruction = null;
        var amountText = match.Groups["amount"].Value.Replace(',', '.');
        if (!double.TryParse(amountText, NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out var amount)
            || double.IsNaN(amount) || double.IsInfinity(amount) || amount <= 0 || amount > 100_000)
            return false;

        var unit = match.Groups["unit"].Value.ToLowerInvariant();
        var factor = unit switch
        {
            "cm" or "센티미터" or "센치" => 10d,
            "m" or "미터" => 1000d,
            _ => 1d
        };
        var distance = amount * factor;
        var direction = match.Groups["direction"].Value;
        instruction = new ChangeInstruction
        {
            SourceText = sourceText.Trim(),
            DxMm = direction == "오른쪽" ? distance : direction == "왼쪽" ? -distance : 0,
            DyMm = direction == "위" ? distance : direction == "아래" ? -distance : 0,
            Status = "needs_review"
        };
        return true;
    }
}
