using System.Windows.Forms;
using System.Drawing;
using NAudio.Wave;
using Himec.ChangeCore;
using AcadApp = Autodesk.AutoCAD.ApplicationServices.Application;

namespace Himec.AutoCad2026;

internal sealed class ReviewPanel : UserControl
{
    private readonly AudioRecorder _recorder = new();
    private readonly TextBox _transcript = new() { Multiline = true, ScrollBars = ScrollBars.Vertical, Width = 360, Height = 92 };
    private readonly Label _summary = new() { AutoSize = false, Width = 360, Height = 54, Text = "변경 지시 없음" };
    private readonly Label _target = new() { AutoSize = false, Width = 360, Height = 48, Text = "대상 미지정 — 도면에서 직접 선택하세요." };
    private readonly Label _status = new() { AutoSize = false, Width = 360, Height = 55, Text = "녹음은 로컬에 저장됩니다. 외부 전송은 전사 버튼을 눌렀을 때만 합니다." };
    private readonly Label _keyState = new() { AutoSize = false, Width = 360, Height = 22 };
    private readonly Label _recordingInfo = new() { AutoSize = false, Width = 360, Height = 22, Text = "선택된 녹음 없음" };
    private readonly ToolTip _tooltips = new();
    private readonly Button _record = new() { Text = "● 녹음 시작", Width = 170 };
    private readonly Button _stop = new() { Text = "■ 녹음 중지", Width = 170, Enabled = false };
    private readonly Button _chooseAudio = new() { Text = "이미 녹음한 WAV 선택", Width = 340 };
    private readonly Button _setApiKey = new() { Text = "전사 API 키 입력 (이번 실행에만 사용)", Width = 340 };
    private readonly Button _transcribe = new() { Text = "녹음 전사(API 호출)", Width = 340 };
    private readonly Button _analyze = new() { Text = "전사문에서 이동 지시 찾기", Width = 340 };
    private readonly Button _suggest = new() { Text = "'왼쪽 세 번째' 후보 찾기", Width = 340 };
    private readonly Button _pick = new() { Text = "도면에서 대상 직접 선택", Width = 340 };
    private readonly Button _exportPdf = new() { Text = "수정사항 PDF, JSON으로 내보내기", Width = 340 };
    private readonly Button _clearMarkup = new() { Text = "도면에서 주석·일람표 지우기", Width = 340 };
    private readonly CheckBox _keepMarkup = new() { Text = "표식을 도면에 남기기 (저장은 하지 않음)", Checked = true, Width = 340 };
    private readonly RecordingTagPanel _tagReview = new();
    private string? _sessionApiKey;
    private string? _selectedAudioPath;
    private readonly Panel _statusPanel = new() { Dock = DockStyle.Fill, BackColor = PaletteTheme.Status };

    public ReviewPanel()
    {
        Dock = DockStyle.Fill;
        BackColor = PaletteTheme.Canvas;
        ForeColor = PaletteTheme.Text;
        Font = new Font("Segoe UI", 9F);

        var shell = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 3, Margin = Padding.Empty, Padding = Padding.Empty };
        shell.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 66));
        shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 58));
        shell.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        var header = new Panel { Dock = DockStyle.Fill, BackColor = PaletteTheme.Header, Padding = new Padding(13, 8, 8, 4) };
        header.Controls.Add(new Label
        {
            Dock = DockStyle.Bottom, Height = 20, ForeColor = PaletteTheme.Muted,
            Text = "녹음 → 객체 태그 → 변경 해석 → 승인 실행", Font = new Font("Segoe UI", 8.5F)
        });
        header.Controls.Add(new Label
        {
            Dock = DockStyle.Top, Height = 28, ForeColor = PaletteTheme.Text,
            Text = "HIMEC  |  설계 변경", Font = new Font("Segoe UI", 12F, FontStyle.Bold)
        });
        _status.Dock = DockStyle.Fill;
        _status.ForeColor = PaletteTheme.Text;
        _status.Padding = new Padding(12, 10, 12, 8);
        _status.Font = new Font("Segoe UI", 9F);
        _statusPanel.Controls.Add(_status);

        var layout = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false,
            AutoScroll = true, Padding = new Padding(10, 12, 10, 12), BackColor = PaletteTheme.Canvas
        };
        var row = new FlowLayoutPanel { Width = 340, Height = 39, WrapContents = false, BackColor = PaletteTheme.Surface, Margin = Padding.Empty };
        row.Controls.Add(_record);
        row.Controls.Add(_stop);
        var cardInput = CreateCard("01  회의 입력", "녹음은 로컬 저장 · 전사는 별도 동의 후 전송", row, _chooseAudio, _recordingInfo,
            _keyState, _setApiKey, _transcribe,
            new Label { Text = "전사문  |  직접 수정·입력 가능", Height = 21 }, _transcript);
        var cardTags = CreateCard("02  녹음 객체 태그", "녹음 중 직접 찍기 · 전사 후 언급 검토/수정", _tagReview);
        var cardParse = CreateCard("03  변경 지시 확인", "이동량을 읽고, 불명확한 대상은 보류합니다.", _analyze, _summary);
        var cardTarget = CreateCard("04  도면 대상 지정", "후보는 참고용 · 최종 대상은 직접 클릭", _suggest, _pick, _target);
        var cardExport = CreateCard("05  PDF 내보내기", "일람표는 도면 우측 하단, 주석은 해당 요소 위. 관계도용 JSON을 PDF 옆에 함께 저장합니다.", _keepMarkup, _exportPdf, _clearMarkup);
        var cards = new[] { cardInput, cardTags, cardParse, cardTarget, cardExport };
        foreach (var card in cards) layout.Controls.Add(card);
        layout.SizeChanged += (_, _) =>
        {
            var cardWidth = Math.Max(320, layout.ClientSize.Width - layout.Padding.Horizontal - SystemInformation.VerticalScrollBarWidth - 3);
            foreach (var card in cards)
            {
                card.Width = cardWidth;
                var innerWidth = cardWidth - card.Padding.Horizontal;
                foreach (Control child in card.Controls)
                    child.Width = innerWidth;
                _record.Width = (innerWidth - 8) / 2;
                _stop.Width = (innerWidth - 8) / 2;
            }
        };
        shell.Controls.Add(header, 0, 0);
        shell.Controls.Add(_statusPanel, 0, 1);
        shell.Controls.Add(layout, 0, 2);
        Controls.Add(shell);

        PaletteTheme.Check(_keepMarkup);
        foreach (var button in new[] { _record, _stop, _chooseAudio, _setApiKey, _transcribe, _analyze, _suggest, _pick, _exportPdf, _clearMarkup })
            PaletteTheme.Button(button, primary: button == _analyze || button == _pick);
        foreach (var label in new[] { _keyState, _recordingInfo, _summary, _target }) PaletteTheme.Label(label);
        _summary.ForeColor = PaletteTheme.Text;
        _target.ForeColor = PaletteTheme.Text;
        _transcript.BackColor = PaletteTheme.Input;
        _transcript.ForeColor = PaletteTheme.Text;
        _transcript.BorderStyle = BorderStyle.FixedSingle;
        _transcript.Font = new Font("Segoe UI", 10F);
        _transcript.Margin = new Padding(0, 4, 0, 4);
        UpdateKeyState();

        _record.Click += (_, _) => StartRecording();
        _stop.Click += async (_, _) => await StopRecordingAsync();
        _chooseAudio.Click += (_, _) => ChooseAudio();
        _setApiKey.Click += (_, _) => PromptForApiKey();
        _transcribe.Click += async (_, _) => await TranscribeAsync();
        _analyze.Click += (_, _) => Analyze();
        _suggest.Click += (_, _) => AcadApp.DocumentManager.MdiActiveDocument?.SendStringToExecute("HIMEC_SUGGEST ", true, false, false);
        _pick.Click += (_, _) => AcadApp.DocumentManager.MdiActiveDocument?.SendStringToExecute("HIMEC_PICK ", true, false, false);
        _exportPdf.Click += (_, _) => AcadApp.DocumentManager.MdiActiveDocument?.SendStringToExecute("HIMEC_PDF ", true, false, false);
        _clearMarkup.Click += (_, _) => AcadApp.DocumentManager.MdiActiveDocument?.SendStringToExecute("HIMEC_PDF_CLEAR ", true, false, false);
        _tagReview.StatusChanged += SetStatus;
        _tagReview.ScanRequested += () => { _tagReview.AddTranscriptMentions(_transcript.Text); };
        _tagReview.PickRequested += () => AcadApp.DocumentManager.MdiActiveDocument?.SendStringToExecute("HIMEC_TAG_PICK ", true, false, false);
    }

    /// <summary>Whether the callouts and schedule stay in the drawing after plotting.</summary>
    internal bool KeepMarkup => _keepMarkup.Checked;

    /// <summary>Match the transcript against the tagged objects and lay out the PDF content.
    /// Returns null with a reason when there is nothing to export yet.</summary>
    internal PdfExportPlan? BuildPdfPlan(string drawing, out string reason)
    {
        reason = "";
        var session = _tagReview.Session;
        if (session is null)
        {
            reason = "먼저 녹음 파일을 선택하거나 태그를 만드세요.";
            return null;
        }
        if (string.IsNullOrWhiteSpace(_transcript.Text))
        {
            reason = "전사문이 비어 있습니다. 전사하거나 직접 입력하세요.";
            return null;
        }
        var changes = ChangeMatching.Extract(_transcript.Text, session, drawing);
        if (changes.Count == 0)
        {
            reason = "전사문에서 수정사항을 찾지 못했습니다.";
            return null;
        }
        return PdfExportPlanner.Build(changes, drawing);
    }

    public void SetStatus(string text)
    {
        if (IsDisposed) return;
        if (InvokeRequired) BeginInvoke(() => SetStatus(text));
        else
        {
            _status.Text = text;
            _statusPanel.BackColor = text.Contains("실패") || text.Contains("불가")
                ? PaletteTheme.Error
                : text.Contains("취소") || text.Contains("미설정")
                    ? PaletteTheme.Warning
                    : text.Contains("완료") || text.Contains("저장") || text.Contains("설정됐")
                        ? PaletteTheme.Success
                        : PaletteTheme.Status;
        }
    }

    private static FlowLayoutPanel CreateCard(string title, string subtitle, params Control[] children)
    {
        var card = new FlowLayoutPanel
        {
            FlowDirection = FlowDirection.TopDown, WrapContents = false,
            AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink,
            Width = 360, Padding = new Padding(12, 9, 12, 11), Margin = new Padding(0, 0, 0, 10),
            BackColor = PaletteTheme.Surface
        };
        card.Controls.Add(new Label
        {
            Text = title, Height = 22, Width = 336, ForeColor = PaletteTheme.Accent,
            Font = new Font("Segoe UI", 10F, FontStyle.Bold), Margin = new Padding(0, 0, 0, 2)
        });
        card.Controls.Add(new Label
        {
            Text = subtitle, Height = 24, Width = 336, ForeColor = PaletteTheme.Muted,
            Font = new Font("Segoe UI", 8.5F), Margin = new Padding(0, 0, 0, 5)
        });
        foreach (var child in children)
        {
            if (child is Label label && label.ForeColor == SystemColors.ControlText) PaletteTheme.Label(label);
            card.Controls.Add(child);
        }
        return card;
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
            var path = _recorder.Start();
            _tagReview.Start(path);
            _selectedAudioPath = null;
            _recordingInfo.Text = "녹음 중… 중지 후 파일을 확인하세요.";
            _record.Enabled = false;
            _stop.Enabled = true;
            _chooseAudio.Enabled = false;
            _transcribe.Enabled = false;
            SetStatus("녹음 중. 로컬 파일에만 저장하며 약 5분/10MB가 상한입니다.");
        }
        catch (System.Exception ex) { SetStatus("녹음 시작 실패: " + ex.Message); }
    }

    private async Task StopRecordingAsync()
    {
        try
        {
            var path = await _recorder.StopAsync();
            SetSelectedAudio(path);
            _tagReview.Finish(path);
            SetStatus("녹음 저장 완료. 전사하려면 API 키와 외부 전송 동의가 필요합니다.");
        }
        catch (System.Exception ex) { SetStatus("녹음 중지 실패: " + ex.Message); }
        finally { _record.Enabled = true; _stop.Enabled = false; _chooseAudio.Enabled = true; _transcribe.Enabled = true; }
    }

    private async Task TranscribeAsync()
    {
        var path = _selectedAudioPath;
        if (path is null) { SetStatus("먼저 녹음하거나 기존 WAV를 선택하세요. 전사문 직접 입력도 가능합니다."); return; }
        if (string.IsNullOrWhiteSpace(_sessionApiKey) && !OpenAiTranscriber.HasEnvironmentKey && !PromptForApiKey())
        {
            SetStatus("전사 취소: API 키가 없습니다. 전사문을 직접 입력할 수 있습니다.");
            return;
        }
        if (MessageBox.Show($"{Path.GetFileName(path)} 파일을 OpenAI 전사 API로 전송합니다. 동의하나요? 허가받지 않은 회의/고객 정보는 보내지 마세요.",
                "외부 전송 확인", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) != DialogResult.Yes) return;
        _transcribe.Enabled = false;
        try
        {
            SetStatus("전사 중…");
            _transcript.Text = await OpenAiTranscriber.TranscribeAsync(path, _sessionApiKey);
            var tagsSaved = _tagReview.AddTranscriptMentions(_transcript.Text);
            SetStatus(tagsSaved
                ? "전사 완료. 객체 언급 목록과 원문을 확인하세요."
                : "전사 완료, 태그 저장 실패. 상단 오류와 로컬 저장 경로를 확인하세요.");
        }
        catch (System.Exception ex)
        {
            SetStatus("전사 실패: " + ex.Message);
            MessageBox.Show(ex.Message, "전사 실패 — 녹음 파일은 로컬에 남아 있습니다", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally { _transcribe.Enabled = true; }
    }

    private void ChooseAudio()
    {
        using var picker = new OpenFileDialog
        {
            Title = "전사할 WAV 파일 선택",
            InitialDirectory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Himec", "Recordings"),
            Filter = "WAV 오디오 (*.wav)|*.wav",
            CheckFileExists = true,
            Multiselect = false
        };
        if (picker.ShowDialog() != DialogResult.OK) return;
        try
        {
            SetSelectedAudio(picker.FileName);
            SetStatus("녹음 파일이 선택됐습니다. API 키 설정 후 전사 버튼을 누르세요.");
        }
        catch (System.Exception ex)
        {
            SetStatus("녹음 파일 선택 실패: " + ex.Message);
            MessageBox.Show(ex.Message, "녹음 파일을 사용할 수 없습니다", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void SetSelectedAudio(string path)
    {
        var size = new FileInfo(path).Length;
        if (size < 44 || size > 10_000_000)
            throw new InvalidOperationException("WAV 파일은 10MB 이하이고 비어 있지 않아야 합니다.");
        using var reader = new WaveFileReader(path);
        if (reader.TotalTime.TotalSeconds <= 0)
            throw new InvalidOperationException("WAV 파일 길이가 0초입니다.");
        _tagReview.SelectAudio(path);
        _selectedAudioPath = path;
        _recordingInfo.Text = $"선택 녹음: {reader.TotalTime.TotalSeconds:0.0}초 · {size / 1024.0:0}KB";
        _tooltips.SetToolTip(_recordingInfo, path);
    }

    public void TagPicked(string drawing, string handle, string entityType, string layer)
    {
        if (IsDisposed) return;
        if (InvokeRequired) BeginInvoke(() => _tagReview.CompletePick(drawing, handle, entityType, layer));
        else _tagReview.CompletePick(drawing, handle, entityType, layer);
    }

    private bool PromptForApiKey()
    {
        using var dialog = new Form
        {
            Text = "OpenAI 전사 API 키",
            Width = 470,
            Height = 185,
            FormBorderStyle = FormBorderStyle.FixedDialog,
            StartPosition = FormStartPosition.CenterScreen,
            MaximizeBox = false,
            MinimizeBox = false
        };
        var explanation = new Label
        {
            Left = 16, Top = 12, Width = 420, Height = 45,
            Text = "키는 이번 AutoCAD 실행 중 메모리에서만 사용하며 파일이나 Git에 저장하지 않습니다. 화면 공유 중에는 입력하지 마세요."
        };
        var input = new TextBox { Left = 16, Top = 61, Width = 420, UseSystemPasswordChar = true };
        var okay = new Button { Text = "사용", Left = 250, Top = 98, Width = 88, DialogResult = DialogResult.OK };
        var cancel = new Button { Text = "취소", Left = 348, Top = 98, Width = 88, DialogResult = DialogResult.Cancel };
        dialog.Controls.AddRange([explanation, input, okay, cancel]);
        dialog.AcceptButton = okay;
        dialog.CancelButton = cancel;
        if (dialog.ShowDialog() != DialogResult.OK) return false;
        if (string.IsNullOrWhiteSpace(input.Text))
        {
            SetStatus("빈 API 키는 사용할 수 없습니다.");
            return false;
        }
        _sessionApiKey = input.Text.Trim();
        input.Clear();
        UpdateKeyState();
        SetStatus("전사 API 키가 이번 실행에만 설정됐습니다. 녹음 전사 버튼으로 전송을 확인하세요.");
        return true;
    }

    private void UpdateKeyState()
    {
        _keyState.Text = !string.IsNullOrWhiteSpace(_sessionApiKey)
            ? "전사 키: 이번 실행에만 입력됨"
            : OpenAiTranscriber.HasEnvironmentKey
                ? "전사 키: 로컬 환경변수에서 사용 가능"
                : "전사 키: 미설정 — 녹음은 가능, API 전사는 불가";
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

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _recorder.Dispose();
            _tooltips.Dispose();
            _sessionApiKey = null;
        }
        base.Dispose(disposing);
    }
}
