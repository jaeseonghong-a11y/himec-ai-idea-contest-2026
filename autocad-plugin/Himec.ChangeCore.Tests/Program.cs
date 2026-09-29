using Himec.ChangeCore;
using System.Text.Json;

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

var rtSession = new RecordingTagSession { RecordingPath = "synthetic.wav" };
var drawingObjects = new[]
{
    new RecordingObjectCandidate("test.dxf", "20", ["C1"], "INSERT", "COLUMN"),
    new RecordingObjectCandidate("test.dxf", "30", ["B12"], "INSERT", "BEAM"),
    new RecordingObjectCandidate("test.dxf", "31", ["B-12"], "INSERT", "BEAM"),
    new RecordingObjectCandidate("other.dxf", "40", ["C1"], "INSERT", "COLUMN")
};
var one = RealtimeTagging.AddCompletedTurn(rtSession,
    new CompletedTranscriptTurn("turn-1", "C1 기둥을 옮기자", 2.4), "test.dxf", drawingObjects);
if (one.Count != 1 || one[0].Handle != "20" || one[0].CandidateHandles.Single() != "20" ||
    one[0].EffectiveSuggestionStatus != RecordingTagSuggestionStatus.Proposed ||
    one[0].ConfirmedByUserAt is not null || one[0].ApproximateOffsetSeconds != 2.4)
    throw new Exception("Unique explicit ID was not a reviewable proposal");
if (RealtimeTagging.AddCompletedTurn(rtSession,
    new CompletedTranscriptTurn("turn-1", "C1 기둥을 옮기자", 2.4), "test.dxf", drawingObjects).Count != 0)
    throw new Exception("Completed turn was duplicated");
rtSession.Remove(one[0].Id);
if (RealtimeTagging.AddCompletedTurn(rtSession,
    new CompletedTranscriptTurn("turn-1", "C1 기둥을 옮기자", 2.4), "test.dxf", drawingObjects).Count != 0)
    throw new Exception("Deleted turn was re-added by a repeated completion");
one = RealtimeTagging.AddCompletedTurn(rtSession,
    new CompletedTranscriptTurn("turn-1b", "C1 기둥을 옮기자", 2.5), "test.dxf", drawingObjects);
rtSession.Rename(one[0].Id, "C2");
if (one[0].IsLinked || one[0].CandidateHandles.Count != 0 ||
    one[0].EffectiveSuggestionStatus != RecordingTagSuggestionStatus.SelectionNeeded)
    throw new Exception("Edited proposal retained an unsafe object link");
var many = RealtimeTagging.AddCompletedTurn(rtSession,
    new CompletedTranscriptTurn("turn-2", "B12 보를 검토하자", 4.1), "test.dxf", drawingObjects);
if (many.Count != 1 || many[0].IsLinked ||
    !many[0].CandidateHandles.SequenceEqual(["30", "31"]) ||
    many[0].EffectiveSuggestionStatus != RecordingTagSuggestionStatus.SelectionNeeded)
    throw new Exception("Multiple objects were automatically linked");
var none = RealtimeTagging.AddCompletedTurn(rtSession,
    new CompletedTranscriptTurn("turn-3", "E5 장비를 검토하자", 6.0), "test.dxf", drawingObjects);
if (none.Count != 1 || none[0].IsLinked || none[0].CandidateHandles.Count != 0)
    throw new Exception("Unknown explicit ID was automatically linked");
var generic = RealtimeTagging.AddCompletedTurn(rtSession,
    new CompletedTranscriptTurn("turn-4", "왼쪽 세 번째 기둥을 옮기자", 8.0), "test.dxf", drawingObjects);
if (generic.Count != 1 || generic[0].IsLinked || generic[0].CandidateHandles.Count != 0)
    throw new Exception("Relative or generic mention was automatically linked");
try { rtSession.Confirm(many[0].Id, DateTimeOffset.UtcNow); throw new Exception("Unlinked tag was confirmed"); }
catch (InvalidOperationException) { }
rtSession.Link(many[0].Id, "test.dxf", "31", "INSERT", "BEAM");
var approvedAt = new DateTimeOffset(2026, 9, 29, 12, 0, 0, TimeSpan.Zero);
rtSession.Confirm(many[0].Id, approvedAt);
if (many[0].EffectiveSuggestionStatus != RecordingTagSuggestionStatus.Confirmed ||
    many[0].ConfirmedByUserAt != approvedAt) throw new Exception("User confirmation was not recorded");
rtSession.Unlink(many[0].Id);
if (many[0].IsLinked || many[0].ConfirmedByUserAt is not null ||
    many[0].EffectiveSuggestionStatus != RecordingTagSuggestionStatus.SelectionNeeded)
    throw new Exception("Unlinked tag remained confirmed");
var legacyJson = """{"RecordingPath":"old.wav","Tags":[{"Id":"legacy","Label":"C1","Origin":"manual","Drawing":"old.dxf","Handle":"A"}]}""";
var legacy = JsonSerializer.Deserialize<RecordingTagSession>(legacyJson)
    ?? throw new Exception("Legacy recording session did not deserialize");
if (legacy.Tags.Count != 1 || legacy.Tags[0].EffectiveSuggestionStatus != RecordingTagSuggestionStatus.DirectLinked ||
    legacy.Tags[0].CandidateHandles.Count != 0)
    throw new Exception("Legacy linked tag lost its state");
var roundTrip = JsonSerializer.Deserialize<RecordingTagSession>(JsonSerializer.Serialize(rtSession))
    ?? throw new Exception("Realtime session did not deserialize");
if (roundTrip.Tags.Count != rtSession.Tags.Count ||
    roundTrip.Tags.First(t => t.TranscriptTurnId == "turn-1b").ApproximateOffsetSeconds != 2.5 ||
    !roundTrip.ProcessedTranscriptTurnIds.Contains("turn-1"))
    throw new Exception("Realtime tag contract did not round-trip");
// --- change matching: transcript edits paired with tagged drawing objects ---
var matchSession = new RecordingTagSession { RecordingPath = "match.wav" };
var c1Tag = matchSession.AddManual("C1");
matchSession.Link(c1Tag.Id, "plan.dxf", "A1", "INSERT", "COLUMN");
var b12Tag = matchSession.AddManual("B12");
matchSession.Link(b12Tag.Id, "plan.dxf", "A2", "INSERT", "BEAM");

var everyMove = InstructionParser.ParseAllMoves("C1을 위로 30cm 올리고 B12를 아래로 200mm 내리자");
if (everyMove.Count != 2 || everyMove[0].DyMm != 300 || everyMove[1].DyMm != -200)
    throw new Exception("ParseAllMoves lost a movement");
if (InstructionParser.ParseAllMoves("위로 999999mm 올리자").Count != 0)
    throw new Exception("Out-of-range amount was accepted");

var matched = ChangeMatching.Extract("C1을 위로 30cm 올리자.", matchSession, "plan.dxf");
if (matched.Count != 1 || !matched[0].IsMatched || matched[0].Handle != "A1" ||
    matched[0].TagId != c1Tag.Id || matched[0].DyMm != 300)
    throw new Exception("Explicit id was not matched to its tagged object");
if (ChangeMatching.Unanswered(matched).Count != 0)
    throw new Exception("A matched change was still queued as a question");

var noTarget = ChangeMatching.Extract("위로 30cm 올리자.", matchSession, "plan.dxf");
if (noTarget.Count != 1 || noTarget[0].QuestionKind != ChangeQuestionKind.NoObjectMentioned ||
    noTarget[0].Handle is not null)
    throw new Exception("Change without a target was not turned into a question");

var genericOnly = ChangeMatching.Extract("기둥을 위로 30cm 올리자.", matchSession, "plan.dxf");
if (genericOnly.Count != 1 || genericOnly[0].QuestionKind != ChangeQuestionKind.GenericOnly ||
    genericOnly[0].Handle is not null)
    throw new Exception("Generic noun was auto-linked");

var unknownMark = ChangeMatching.Extract("C9를 위로 30cm 올리자.", matchSession, "plan.dxf");
if (unknownMark.Count != 1 || unknownMark[0].QuestionKind != ChangeQuestionKind.NoTagFound)
    throw new Exception("Unknown mark did not ask the user");

var otherDrawing = ChangeMatching.Extract("C1을 위로 30cm 올리자.", matchSession, "section.dxf");
if (otherDrawing.Count != 1 || otherDrawing[0].QuestionKind != ChangeQuestionKind.NoTagFound)
    throw new Exception("A tag from another drawing was used");

var duplicate = matchSession.AddManual("C1");
matchSession.Link(duplicate.Id, "plan.dxf", "A3", "INSERT", "COLUMN");
var ambiguous = ChangeMatching.Extract("C1을 위로 30cm 올리자.", matchSession, "plan.dxf");
if (ambiguous.Count != 1 || ambiguous[0].QuestionKind != ChangeQuestionKind.MultipleTags ||
    ambiguous[0].CandidateTagIds.Count != 2 || ambiguous[0].Handle is not null)
    throw new Exception("Duplicate tags were not turned into a question");
matchSession.Remove(duplicate.Id);

var twoInOne = ChangeMatching.Extract("C1을 위로 30cm 올리고 B12를 아래로 200mm 내리자.", matchSession, "plan.dxf");
if (twoInOne.Count != 2 ||
    twoInOne.Any(c => c.QuestionKind != ChangeQuestionKind.SeveralChangesInSentence))
    throw new Exception("Two edits in one sentence were paired without asking");

var several = ChangeMatching.Extract(
    "C1을 위로 30cm 올리자. 그리고 B12를 아래로 200mm 내리자. 오늘 회의는 여기까지.",
    matchSession, "plan.dxf");
if (several.Count != 2 || !several[0].IsMatched || !several[1].IsMatched ||
    several[0].Handle != "A1" || several[1].Handle != "A2")
    throw new Exception("Multiple sentences were not matched independently");
if (ChangeMatching.Extract("오늘 회의는 여기까지.", matchSession, "plan.dxf").Count != 0)
    throw new Exception("Small talk produced a change item");
if (ChangeMatching.Describe(several[0]) != "Y +300 mm")
    throw new Exception("Move description is wrong: " + ChangeMatching.Describe(several[0]));

// --- pdf export plan: callouts on matched objects, schedule for everything ---
var planInput = ChangeMatching.Extract(
    "C1을 위로 30cm 올리자. 기둥을 아래로 200mm 내리자. 오늘은 여기까지.",
    matchSession, "plan.dxf");
var plan = PdfExportPlanner.Build(planInput, "plan.dxf");
if (plan.MatchedCount != 1 || plan.QuestionCount != 1)
    throw new Exception("Plan counted the wrong number of changes");
if (plan.Schedule.Count != 2)
    throw new Exception("Every change must appear in the schedule");
if (plan.Annotations.Count != 1 || plan.Annotations[0].Handle != "A1")
    throw new Exception("Only a settled target may get a callout");
if (plan.Annotations[0].Marker != "1" || plan.Schedule[0].Marker != "1" || plan.Schedule[1].Marker != "2")
    throw new Exception("Markers must number the transcript order");
if (!plan.Annotations[0].Text.Contains("C1") || !plan.Annotations[0].Text.Contains("Y +300 mm"))
    throw new Exception("Callout text lost the target or the move");
if (plan.Schedule[1].State != PdfExportPlanner.StateQuestion || plan.Schedule[1].Note.Length == 0)
    throw new Exception("An unresolved change must carry its question into the schedule");
if (plan.Schedule[0].State != PdfExportPlanner.StateConfirmedTarget)
    throw new Exception("A settled change was not marked as confirmed target");
if (PdfExportPlanner.Cells(plan.Schedule[0]).Count != PdfExportPlanner.Headers.Count)
    throw new Exception("Schedule row does not match the header count");
if (!plan.Footer.Contains("도면은 수정되지 않았습니다"))
    throw new Exception("Footer must state that the drawing was not edited");
var emptyPlan = PdfExportPlanner.Build([], "plan.dxf");
if (emptyPlan.Schedule.Count != 0 || emptyPlan.Annotations.Count != 0 || emptyPlan.MatchedCount != 0)
    throw new Exception("Empty change list produced content");

Console.WriteLine("Parser, targeting, legacy recording tags, realtime tag contract, change matching, and pdf plan checks passed");
