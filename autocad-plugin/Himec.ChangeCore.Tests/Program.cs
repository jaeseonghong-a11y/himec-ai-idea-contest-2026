using Himec.ChangeCore;

var cases = new (string Text, double X, double Y)[]
{
    ("왼쪽에서 세번째 이 기둥을 위로 30CM위로 옮기자", 0, 300),
    ("C1을 아래로 500mm 이동", 0, -500),
    ("기둥을 오른쪽으로 1.5m 이동", 1500, 0),
    ("왼쪽으로 20센치", -200, 0),
};
foreach (var test in cases)
{
    if (!InstructionParser.TryParseMove(test.Text, out var item, out _) || item is null ||
        item.DxMm != test.X || item.DyMm != test.Y || item.Status != "needs_review" || item.TargetHandle is not null)
        throw new Exception($"Failed: {test.Text}");
}
if (InstructionParser.TryParseMove("여기 기둥 좀 옮겨", out _, out _))
    throw new Exception("Ambiguous amount was accepted");
Console.WriteLine($"{cases.Length + 1} parser checks passed");
