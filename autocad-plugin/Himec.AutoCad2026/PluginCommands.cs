using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.Runtime;
using Autodesk.AutoCAD.Windows;
using Himec.ChangeCore;
using AcadApp = Autodesk.AutoCAD.ApplicationServices.Application;

namespace Himec.AutoCad2026;

public sealed class PluginCommands : IExtensionApplication
{
    private static PaletteSet? _palette;
    private static ReviewPanel? _panel;
    internal static ChangeInstruction? CurrentInstruction;
    internal static ObjectId SelectedObjectId = ObjectId.Null;

    public void Initialize() { }
    public void Terminate() { _panel?.Dispose(); }

    [CommandMethod("HIMEC")]
    public void ShowPanel()
    {
        if (_palette is null)
        {
            _panel = new ReviewPanel();
            _palette = new PaletteSet("HIMEC 설계 변경", new Guid("79736E11-07A6-4D5E-8210-7EF45EF747E2"))
            {
                Size = new System.Drawing.Size(420, 640),
                MinimumSize = new System.Drawing.Size(360, 500)
            };
            _palette.Add("회의 변경", _panel);
        }
        _palette.Visible = true;
    }

    [CommandMethod("HIMEC_PICK")]
    public void PickTarget()
    {
        var doc = AcadApp.DocumentManager.MdiActiveDocument;
        if (doc is null || CurrentInstruction is null)
        {
            _panel?.SetStatus("먼저 지시를 분석하세요.");
            return;
        }
        var options = new PromptEntityOptions("\n변경할 블록을 직접 선택하세요: ");
        options.SetRejectMessage("\n첫 버전은 블록만 이동할 수 있습니다.");
        options.AddAllowedClass(typeof(BlockReference), true);
        var picked = doc.Editor.GetEntity(options);
        if (picked.Status != PromptStatus.OK) return;
        using var tr = doc.TransactionManager.StartTransaction();
        var block = tr.GetObject(picked.ObjectId, OpenMode.ForRead) as BlockReference;
        if (block is null) return;
        CurrentInstruction.TargetHandle = block.Handle.ToString();
        CurrentInstruction.TargetDrawing = doc.Name;
        CurrentInstruction.Status = "needs_review";
        CurrentInstruction.ReviewedAt = null;
        CurrentInstruction.Reviewer = null;
        SelectedObjectId = picked.ObjectId;
        _panel?.SetTarget($"블록 {block.Name} / handle {block.Handle} / 현재 위치 {block.Position}");
        _panel?.SetStatus("대상이 지정됐습니다. 지시 내용을 확인한 뒤 승인하세요.");
    }

    [CommandMethod("HIMEC_SUGGEST")]
    public void SuggestCandidate()
    {
        var doc = AcadApp.DocumentManager.MdiActiveDocument;
        var text = CurrentInstruction?.SourceText ?? "";
        if (doc is null || !text.Contains("왼쪽에서") ||
            !(text.Contains("세번째") || text.Contains("세 번째") || text.Contains("3번째")))
        {
            _panel?.SetStatus("현재 후보 추천은 '왼쪽에서 세 번째 기둥' 표현만 지원합니다.");
            return;
        }
        using var tr = doc.TransactionManager.StartTransaction();
        var space = (BlockTableRecord)tr.GetObject(doc.Database.CurrentSpaceId, OpenMode.ForRead);
        var columns = new List<BlockReference>();
        foreach (ObjectId id in space)
        {
            if (tr.GetObject(id, OpenMode.ForRead) is not BlockReference block) continue;
            var label = (block.Name + " " + block.Layer).ToUpperInvariant();
            if (label.Contains("COLUMN") || label.Contains("기둥") ||
                System.Text.RegularExpressions.Regex.IsMatch(label, @"\bC\d+\b"))
                columns.Add(block);
        }
        if (columns.Count < 3)
        {
            _panel?.SetStatus($"기둥 후보가 {columns.Count}개뿐이어서 세 번째를 고를 수 없습니다. 직접 선택하세요.");
            return;
        }
        var minY = columns.Min(x => x.Position.Y);
        var maxY = columns.Max(x => x.Position.Y);
        if (maxY - minY > 1.0)
        {
            _panel?.SetStatus("기둥 후보가 여러 줄에 있어 '왼쪽 세 번째' 기준이 모호합니다. 직접 선택하세요.");
            return;
        }
        var candidate = columns.OrderBy(x => x.Position.X).ElementAt(2);
        _panel?.SetTarget($"추천 후보(미확정): {candidate.Name} / handle {candidate.Handle} / X={candidate.Position.X:0.##}. 직접 선택해 확정하세요.");
        _panel?.SetStatus("추천은 참고용입니다. 선택 버튼으로 도면 객체를 직접 클릭해야 승인할 수 있습니다.");
    }

    [CommandMethod("HIMEC_APPLY")]
    public void ApplyReviewedMove()
    {
        var doc = AcadApp.DocumentManager.MdiActiveDocument;
        var change = CurrentInstruction;
        if (doc is null || change is null || change.Status != "confirmed" ||
            change.Reviewer is null || change.ReviewedAt is null ||
            change.Action != "move" || change.TargetHandle is null ||
            change.TargetDrawing != doc.Name || SelectedObjectId.IsNull ||
            !double.IsFinite(change.DxMm) || !double.IsFinite(change.DyMm) ||
            (change.DxMm == 0 && change.DyMm == 0))
        {
            doc?.Editor.WriteMessage("\nHIMEC: 승인·도면·대상 조건이 맞지 않아 실행하지 않았습니다.\n");
            _panel?.SetStatus("실행 거절: 승인·도면·대상을 다시 확인하세요.");
            return;
        }
        if (Convert.ToInt32(AcadApp.GetSystemVariable("INSUNITS")) != 4)
        {
            doc.Editor.WriteMessage("\nHIMEC: 도면 INSUNITS가 mm(4)가 아니므로 실행하지 않았습니다.\n");
            _panel?.SetStatus("실행 거절: 도면 단위가 mm가 아닙니다.");
            return;
        }

        try
        {
            using var tr = doc.TransactionManager.StartTransaction();
            var block = tr.GetObject(SelectedObjectId, OpenMode.ForWrite, false) as BlockReference;
            if (block is null || block.Handle.ToString() != change.TargetHandle)
                throw new InvalidOperationException("선택 객체가 변경되었거나 블록이 아닙니다.");
            var before = block.Position;
            block.TransformBy(Matrix3d.Displacement(new Vector3d(change.DxMm, change.DyMm, 0)));
            tr.Commit();
            change.Status = "applied";
            change.ExecutedAt = DateTimeOffset.Now;
            try
            {
                LocalRecordStore.Save(change);
                doc.Editor.WriteMessage($"\nHIMEC: 블록 {change.TargetHandle} {before} → {block.Position}. UNDO로 되돌릴 수 있습니다.\n");
                _panel?.SetStatus("이동 완료. 원본 도면은 자동 저장하지 않았습니다. UNDO 가능.");
            }
            catch (System.Exception logError)
            {
                doc.Editor.WriteMessage($"\nHIMEC: 도면은 이동됐지만 기록 저장 실패: {logError.Message}. 즉시 UNDO를 검토하세요.\n");
                _panel?.SetStatus("도면은 이동됐지만 기록 저장 실패. 즉시 UNDO를 검토하세요.");
            }
        }
        catch (System.Exception ex)
        {
            doc.Editor.WriteMessage($"\nHIMEC: 실행 실패: {ex.Message}\n");
            _panel?.SetStatus("실행 실패: " + ex.Message);
        }
    }
}
