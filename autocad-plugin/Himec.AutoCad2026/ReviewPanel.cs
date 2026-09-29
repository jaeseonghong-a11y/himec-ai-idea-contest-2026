using System.Windows.Forms;
using Himec.ChangeCore;
using AcadApp = Autodesk.AutoCAD.ApplicationServices.Application;

namespace Himec.AutoCad2026;

internal sealed class ReviewPanel : UserControl
{
    private readonly AudioRecorder _recorder = new();
    private readonly TextBox _transcript = new() { Multiline = true, ScrollBars = ScrollBars.Vertical, Width = 360, Height = 120 };
    private readonly Label _summary = new() { AutoSize = false, Width = 360, Height = 60, Text = "변경 지시 없음" };
    private readonly Label _target = new() { AutoSize = false, Width = 360, Height = 52, Text = "대상 미지정 — 도면에서 직접 선택하세요." };
    private readonly Label _status = new() { AutoSize = false, Width = 360, Height = 55, Text = "녹음은 로컬에 저장됩니다. 외부 전송은 전사 버튼을 눌렀을 때만 합니다." };
    private readonly Button _record = new() { Text = "● 녹음 시작", Width = 170 };
    private readonly Button _stop = new() { Text = "■ 녹음 중지", Width = 170, Enabled = false };
    private readonly Button _transcribe = new() { Text = "녹음 전사(API 호출)", Width = 340 };
    private readonly Button _analyze = new() { Text = "전사문에서 이동 지시 찾기", Width = 340 };
    private readonly Button _suggest = new() { Text = "'왼쪽 세 번째' 후보 찾기", Width = 340 };
    private readonly Button _pick = new() { Text = "도면에서 대상 직접 선택", Width = 340 };
    private readonly Button _approve = new() { Text = "지시 승인", Width = 340 };
    private readonly Button _execute = new() { Text = "승인된 변경 실행", Width = 340 };

    public ReviewPanel()
    {
        Dock = DockStyle.Fill;
        var layout = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoScroll = true };
        layout.Controls.Add(new Label { Text = "HIMEC 설계 변경 v0 — 합성 도면 시험용", Width = 360, Height = 28 });
        var row = new FlowLayoutPanel { Width = 370, Height = 39, WrapContents = false };
        row.Controls.Add(_record);
        row.Controls.Add(_stop);
        layout.Controls.Add(row);
        layout.Controls.Add(_transcribe);
        layout.Controls.Add(new Label { Text = "회의 전사문 (수동 입력도 가능)", Width = 360, Height = 25 });
        layout.Controls.Add(_transcript);
        layout.Controls.Add(_analyze);
        layout.Controls.Add(_summary);
        layout.Controls.Add(_suggest);
        layout.Controls.Add(_pick);
        layout.Controls.Add(_target);
        layout.Controls.Add(_approve);
        layout.Controls.Add(_execute);
        layout.Controls.Add(_status);
        Controls.Add(layout);

        _record.Click += (_, _) => StartRecording();
        _stop.Click += async (_, _) => await StopRecordingAsync();
        _transcribe.Click += async (_, _) => await TranscribeAsync();
        _analyze.Click += (_, _) => Analyze();
        _suggest.Click += (_, _) => AcadApp.DocumentManager.MdiActiveDocument?.SendStringToExecute("HIMEC_SUGGEST ", true, false, false);
        _pick.Click += (_, _) => AcadApp.DocumentManager.MdiActiveDocument?.SendStringToExecute("HIMEC_PICK ", true, false, false);
        _approve.Click += (_, _) => Approve();
        _execute.Click += (_, _) => AcadApp.DocumentManager.MdiActiveDocument?.SendStringToExecute("HIMEC_APPLY ", true, false, false);
    }

    public void SetStatus(string text)
    {
        if (IsDisposed) return;
        if (InvokeRequired) BeginInvoke(() => _status.Text = text);
        else _status.Text = text;
    }

    public void SetTarget(string text)
    {
        if (IsDisposed) return;
        if (InvokeRequired) BeginInvoke(() => _target.Text = text);
        else _target.Text = text;
    }

    private void StartRecording()
    {
        try
        {
            _recorder.Start();
            _record.Enabled = false;
            _stop.Enabled = true;
            SetStatus("녹음 중. 로컬 파일에만 저장하며 약 5분/10MB가 상한입니다.");
        }
        catch (System.Exception ex) { SetStatus("녹음 시작 실패: " + ex.Message); }
    }

    private async Task StopRecordingAsync()
    {
        try
        {
            var path = await _recorder.StopAsync();
            SetStatus("녹음 저장: " + path);
        }
        catch (System.Exception ex) { SetStatus("녹음 중지 실패: " + ex.Message); }
        finally { _record.Enabled = true; _stop.Enabled = false; }
    }

    private async Task TranscribeAsync()
    {
        var path = _recorder.LastFilePath;
        if (path is null) { SetStatus("먼저 녹음하세요. 전사문 직접 입력도 가능합니다."); return; }
        if (MessageBox.Show("합성 녹음 파일을 OpenAI 전사 API로 전송합니다. 동의하나요? 실제 회의/고객 정보는 보내지 마세요.",
                "외부 전송 확인", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) != DialogResult.Yes) return;
        _transcribe.Enabled = false;
        try
        {
            SetStatus("전사 중…");
            _transcript.Text = await OpenAiTranscriber.TranscribeAsync(path);
            SetStatus("전사 완료. 원문을 확인하고 이동 지시 찾기를 누르세요.");
        }
        catch (System.Exception ex) { SetStatus("전사 실패: " + ex.Message); }
        finally { _transcribe.Enabled = true; }
    }

    private void Analyze()
    {
        if (!InstructionParser.TryParseMove(_transcript.Text, out var change, out var reason))
        {
            PluginCommands.CurrentInstruction = null;
            PluginCommands.SelectedObjectId = Autodesk.AutoCAD.DatabaseServices.ObjectId.Null;
            _summary.Text = "해석 불가 — 전사문을 수정하거나 대상·이동량을 명확히 말하세요.";
            SetStatus(reason);
            return;
        }
        PluginCommands.CurrentInstruction = change;
        PluginCommands.SelectedObjectId = Autodesk.AutoCAD.DatabaseServices.ObjectId.Null;
        _summary.Text = $"제안: 블록 이동 X {change!.DxMm:+0.##;-0.##;0} mm / Y {change.DyMm:+0.##;-0.##;0} mm\nWCS 좌표 기준 · 자동 대상 확정 안 함 · 로컬 규칙 해석";
        _target.Text = "대상 미지정 — 도면에서 직접 선택하세요.";
        SetStatus(reason);
    }

    private void Approve()
    {
        var change = PluginCommands.CurrentInstruction;
        var doc = AcadApp.DocumentManager.MdiActiveDocument;
        if (change is null || doc is null || change.TargetHandle is null || change.TargetDrawing != doc.Name)
        {
            SetStatus("승인 불가: 도면에서 대상 블록을 먼저 지정하세요.");
            return;
        }
        if (_transcript.Text.Trim() != change.SourceText)
        {
            SetStatus("전사문이 바뀌었습니다. 다시 지시 찾기를 눌러 분석하세요.");
            return;
        }
        var message = $"현재 도면: {doc.Name}\n대상: {change.TargetHandle}\n이동: X {change.DxMm} mm, Y {change.DyMm} mm\n\n이 지시를 승인할까요?";
        if (MessageBox.Show(message, "변경 지시 검토", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
        try
        {
            change.Status = "confirmed";
            change.Reviewer = Environment.UserName;
            change.ReviewedAt = DateTimeOffset.Now;
            LocalRecordStore.Save(change);
            SetStatus("승인 기록 완료. 실행 버튼을 눌러야 도면이 바뀝니다.");
        }
        catch (System.Exception ex)
        {
            change.Status = "needs_review";
            change.Reviewer = null;
            change.ReviewedAt = null;
            SetStatus("승인 기록 실패, 실행 불가: " + ex.Message);
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing) _recorder.Dispose();
        base.Dispose(disposing);
    }
}
