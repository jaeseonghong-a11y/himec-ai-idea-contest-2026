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
if (ColumnTargeting.IsColumnLabel("three_columns_mm", "0"))
    throw new Exception("Whole-drawing inserted block was misclassified as a column");
if (!ColumnTargeting.IsColumnLabel("COLUMN", "0") || !ColumnTargeting.IsColumnLabel("STRUCT_COLUMN_A", "0"))
    throw new Exception("Column block was not recognized");
var columns = new[]
{
    new ColumnCandidate("A", "COLUMN", 0, 0),
    new ColumnCandidate("B", "COLUMN", 1000, 0),
    new ColumnCandidate("C", "COLUMN", 2000, 0)
};
if (!ColumnTargeting.TryThirdFromLeft(columns, out var third, out _) || third?.Handle != "C")
    throw new Exception("Third column was not suggested");
var repeated = new[] { columns[0], columns[1], columns[1] with { Handle = "D" } };
if (ColumnTargeting.TryThirdFromLeft(repeated, out _, out _))
    throw new Exception("Overlapping columns were accepted");
var multipleRows = new[] { columns[0], columns[1], columns[2] with { Y = 1000 } };
if (ColumnTargeting.TryThirdFromLeft(multipleRows, out _, out _))
    throw new Exception("Multiple rows were accepted");
var tagSession = new RecordingTagSession { RecordingPath = "synthetic.wav" };
var liveTag = tagSession.AddManual("왼쪽 세 번째 기둥", 12.5);
if (liveTag.OffsetSeconds != 12.5 || liveTag.IsLinked) throw new Exception("Live manual tag failed");
tagSession.Link(liveTag.Id, "synthetic.dxf", "1A", "INSERT", "COLUMN");
if (!liveTag.IsLinked || liveTag.Handle != "1A") throw new Exception("Tag-object link failed");
tagSession.Rename(liveTag.Id, "C1");
if (liveTag.Label != "C1") throw new Exception("Tag rename failed");
var found = tagSession.AddTranscriptMentions("C1 기둥을 옮기고 B12 보를 검토하자. 덕트도 확인하자.");
if (found != 3 || tagSession.Tags.Count != 4) throw new Exception("Transcript mention extraction failed");
if (tagSession.AddTranscriptMentions("C1 기둥을 옮기고 B12 보를 검토하자. 덕트도 확인하자.") != 0)
    throw new Exception("Transcript tag deduplication failed");
var extracted = tagSession.Tags.First(t => t.Origin == "transcript");
tagSession.Rename(extracted.Id, "사용자 검토 태그");
if (tagSession.AddTranscriptMentions("C1 기둥을 옮기고 B12 보를 검토하자. 덕트도 확인하자.") != 0)
    throw new Exception("Renamed transcript tag was duplicated");
tagSession.Unlink(liveTag.Id);
if (liveTag.IsLinked) throw new Exception("Tag unlink failed");
tagSession.Remove(liveTag.Id);
if (tagSession.Tags.Count != 3) throw new Exception("Tag delete failed");
Console.WriteLine($"{cases.Length + 14} parser, targeting and recording-tag checks passed");
