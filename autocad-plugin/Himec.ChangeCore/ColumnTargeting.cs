using System.Text.RegularExpressions;

namespace Himec.ChangeCore;

public sealed record ColumnCandidate(string Handle, string Name, double X, double Y);

public static class ColumnTargeting
{
    private static readonly Regex ColumnToken = new(
        @"(^|[^A-Z0-9])COLUMN(?=$|_|-|[0-9])|(^|[^A-Z0-9])C\d+($|[^A-Z0-9])",
        RegexOptions.Compiled | RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

    public static bool IsColumnLabel(string name, string layer) =>
        name.IndexOf("기둥", StringComparison.Ordinal) >= 0 || layer.IndexOf("기둥", StringComparison.Ordinal) >= 0 ||
        ColumnToken.IsMatch(name) || ColumnToken.IsMatch(layer);

    public static bool TryThirdFromLeft(IReadOnlyList<ColumnCandidate> candidates,
        out ColumnCandidate? selected, out string reason)
    {
        selected = null;
        if (candidates.Count < 3)
        {
            reason = $"기둥 후보가 {candidates.Count}개뿐입니다. 도면을 '열기'로 연 뒤 다시 찾거나 직접 선택하세요.";
            return false;
        }
        if (candidates.Any(x => double.IsNaN(x.X) || double.IsInfinity(x.X) ||
                                double.IsNaN(x.Y) || double.IsInfinity(x.Y)))
        {
            reason = "기둥 좌표가 유효하지 않아 직접 선택해야 합니다.";
            return false;
        }
        if (candidates.Max(x => x.Y) - candidates.Min(x => x.Y) > 1.0)
        {
            reason = "기둥 후보가 여러 줄에 있어 '왼쪽 세 번째' 기준이 모호합니다. 직접 선택하세요.";
            return false;
        }
        var sorted = candidates.OrderBy(x => x.X).ToArray();
        if (sorted.Zip(sorted.Skip(1), (left, right) => Math.Abs(left.X - right.X)).Any(gap => gap <= 1.0))
        {
            reason = "같은 X 위치에 겹친 기둥이 있어 세 번째를 확정할 수 없습니다. 직접 선택하세요.";
            return false;
        }
        selected = sorted[2];
        reason = "후보만 추천했습니다. 도면에서 직접 선택해야 승인할 수 있습니다.";
        return true;
    }
}
