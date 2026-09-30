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

    [CommandMethod("HIMEC_TAG_PICK")]
    public void PickRecordingTagObject()
    {
        var doc = AcadApp.DocumentManager.MdiActiveDocument;
        if (doc is null) { _panel?.SetStatus("태그할 도면이 열려 있지 않습니다."); return; }
        var picked = doc.Editor.GetEntity(new PromptEntityOptions("\n태그에 연결할 도면 객체를 선택하세요: "));
        if (picked.Status != PromptStatus.OK) { _panel?.SetStatus("객체 태그 선택을 취소했습니다."); return; }
        using var tr = doc.TransactionManager.StartTransaction();
        var entity = tr.GetObject(picked.ObjectId, OpenMode.ForRead) as Entity;
        if (entity is null) { _panel?.SetStatus("선택한 객체를 읽을 수 없습니다."); return; }
        _panel?.TagPicked(doc.Name, entity.Handle.ToString(), entity.GetType().Name, entity.Layer);
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
        if (!ColumnTargeting.IsColumnLabel(block.Name, block.Layer))
        {
            _panel?.SetTarget($"선택 거절: {block.Name}은 기둥 블록으로 식별되지 않습니다.");
            _panel?.SetStatus("도면 전체를 블록으로 삽입했다면 DXF 파일을 '열기'로 열어주세요. v0은 기둥 블록만 이동합니다.");
            return;
        }
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
        var columns = new List<ColumnCandidate>();
        foreach (ObjectId id in space)
        {
            if (tr.GetObject(id, OpenMode.ForRead) is not BlockReference block) continue;
            if (ColumnTargeting.IsColumnLabel(block.Name, block.Layer))
                columns.Add(new ColumnCandidate(block.Handle.ToString(), block.Name, block.Position.X, block.Position.Y));
        }
        if (!ColumnTargeting.TryThirdFromLeft(columns, out var candidate, out var reason))
        {
            _panel?.SetStatus(reason);
            return;
        }
        _panel?.SetTarget($"추천 후보(미확정): {candidate!.Name} / handle {candidate.Handle} / X={candidate.X:0.##}. 직접 선택해 확정하세요.");
        _panel?.SetStatus(reason);
    }

    [CommandMethod("HIMEC_PDF_CLEAR")]
    public void ClearPdfMarkup()
    {
        var doc = AcadApp.DocumentManager.MdiActiveDocument;
        if (doc is null) return;
        try
        {
            var erased = PdfExporter.ClearMarkup(doc);
            doc.Editor.WriteMessage($"\nHIMEC: 주석·일람표 객체 {erased}개를 지웠습니다.\n");
            _panel?.SetStatus($"주석·일람표 {erased}개를 지웠습니다. 도면은 저장하지 않았습니다.");
        }
        catch (System.Exception ex)
        {
            doc.Editor.WriteMessage($"\nHIMEC: 표식 지우기 실패: {ex.Message}\n");
            _panel?.SetStatus("표식 지우기 실패: " + ex.Message);
        }
    }

    [CommandMethod("HIMEC_PDF")]
    public void ExportPdf()
    {
        var doc = AcadApp.DocumentManager.MdiActiveDocument;
        if (doc is null) return;
        if (_panel is null)
        {
            doc.Editor.WriteMessage("\nHIMEC: 먼저 HIMEC 명령으로 팔레트를 여세요.\n");
            return;
        }
        var plan = _panel.BuildPdfPlan(doc.Name, out var reason);
        if (plan is null) { _panel.SetStatus(reason); return; }
        try
        {
            var folder = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Himec", "Exports");
            Directory.CreateDirectory(folder);
            var stem = Path.GetFileNameWithoutExtension(doc.Name);
            var path = Path.Combine(folder, $"{stem}-변경일람-{DateTime.Now:yyyyMMdd-HHmmss}.pdf");
            PdfExporter.Export(doc, plan, path, _panel.KeepMarkup);
            doc.Editor.WriteMessage($"\nHIMEC: PDF를 저장했습니다. {path}\n");
            // Written after the export: the grid names are read from the sheet while it draws.
            // The relation editor opens this file with its instruction loader as is.
            var json = InstructionExport.PathFor(path);
            File.WriteAllText(json, InstructionExport.Serialize(
                InstructionExport.Build(plan, path, DateTimeOffset.Now)));
            doc.Editor.WriteMessage($"HIMEC: 관계도용 지시 파일을 저장했습니다. {json}\n");
            var kept = _panel.KeepMarkup
                ? "주석·일람표를 도면에 남겼습니다(저장 안 함). 지우려면 표식 지우기."
                : "도면은 그대로 두었습니다.";
            var layers = PdfExporter.LastDeviceUsed.StartsWith("HIMEC", StringComparison.Ordinal)
                ? "레이어 포함"
                : "레이어 미포함(기본 드라이버)";
            _panel.SetStatus($"PDF·지시 JSON 저장 완료 — 확정 {plan.MatchedCount}건, 확인 필요 {plan.QuestionCount}건. {layers}. {kept}");
        }
        catch (System.Exception ex)
        {
            doc.Editor.WriteMessage($"\nHIMEC: PDF 내보내기 실패: {ex.Message}\n");
            _panel.SetStatus("PDF 내보내기 실패: " + ex.Message);
        }
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
            double.IsNaN(change.DxMm) || double.IsInfinity(change.DxMm) ||
            double.IsNaN(change.DyMm) || double.IsInfinity(change.DyMm) ||
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
            if (block is null || block.Handle.ToString() != change.TargetHandle ||
                !ColumnTargeting.IsColumnLabel(block.Name, block.Layer))
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
