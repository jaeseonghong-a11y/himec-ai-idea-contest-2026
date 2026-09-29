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
    private readonly Button _liveStart = new() { Text = "실시간 전사 시작", Width = 170, Enabled = false };
    private readonly Button _liveStop = new() { Text = "실시간 전사 중지", Width = 170, Enabled = false };
    private readonly Label _liveState = new() { Height = 22, Width = 340, Text = "실시간 전사: 꺼짐 · 로컬 녹음만" };
    private readonly Label _livePartial = new() { Height = 24, Width = 340, Text = "말하는 중: —" };
    private readonly Button _analyze = new() { Text = "전사문에서 이동 지시 찾기", Width = 340 };
    private readonly Button _suggest = new() { Text = "'왼쪽 세 번째' 후보 찾기", Width = 340 };
    private readonly Button _pick = new() { Text = "도면에서 대상 직접 선택", Width = 340 };
    private readonly Button _approve = new() { Text = "지시 승인", Width = 340 };
    private readonly Button _execute = new() { Text = "승인된 변경 실행", Width = 340 };
    private readonly RecordingTagPanel _tagReview = new();
    private string? _sessionApiKey;
    private string? _selectedAudioPath;
    private RealtimeTranscriptionClient? _liveClient;
    private Action<byte[]>? _livePcmHandler;
    private string? _liveDrawing;
    private bool _stoppingRecording;
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
        var liveRow = new FlowLayoutPanel { Width = 340, Height = 39, WrapContents = false, BackColor = PaletteTheme.Surface, Margin = Padding.Empty };
        liveRow.Controls.Add(_liveStart);
        liveRow.Controls.Add(_liveStop);
        var cardInput = CreateCard("01  회의 입력", "녹음은 로컬 저장 · 전사는 별도 동의 후 전송", row, _chooseAudio, _recordingInfo,
            _keyState, _setApiKey, liveRow, _liveState, _livePartial, _transcribe,
            new Label { Text = "전사문  |  직접 수정·입력 가능", Height = 21 }, _transcript);
        var cardTags = CreateCard("02  녹음 객체 태그", "녹음 중 직접 찍기 · 전사 후 언급 검토/수정", _tagReview);
        var cardParse = CreateCard("03  변경 지시 확인", "이동량을 읽고, 불명확한 대상은 보류합니다.", _analyze, _summary);
        var cardTarget = CreateCard("04  도면 대상 지정", "단일 식별자는 자동 제안 · 애매하면 직접 클릭", _suggest, _pick, _target);
        var cardApply = CreateCard("05  검토 후 반영", "승인 전에는 도면을 수정하지 않습니다.", _approve, _execute);
        var cards = new[] { cardInput, cardTags, cardParse, cardTarget, cardApply };
        foreach (var card in cards) layout.Controls.Add(card);
        layout.SizeChanged += (_, _) =>
        {
            var cardWidth = Math.Max(260, layout.ClientSize.Width - layout.Padding.Horizontal - SystemInformation.VerticalScrollBarWidth - 3);
            foreach (var card in cards)
            {
                card.Width = cardWidth;
                var innerWidth = cardWidth - card.Padding.Horizontal;
                foreach (Control child in card.Controls)
                    child.Width = innerWidth;
                _record.Width = (innerWidth - 8) / 2;
                _stop.Width = (innerWidth - 8) / 2;
                _liveStart.Width = (innerWidth - 8) / 2;
                _liveStop.Width = (innerWidth - 8) / 2;
            }
        };
        shell.Controls.Add(header, 0, 0);
        shell.Controls.Add(_statusPanel, 0, 1);
        shell.Controls.Add(layout, 0, 2);
        Controls.Add(shell);

        foreach (var button in new[] { _record, _stop, _chooseAudio, _setApiKey, _liveStart, _liveStop, _transcribe, _analyze, _suggest, _pick, _approve, _execute })
            PaletteTheme.Button(button, primary: button == _analyze || button == _pick, caution: button == _execute);
        foreach (var label in new[] { _keyState, _recordingInfo, _liveState, _livePartial, _summary, _target }) PaletteTheme.Label(label);
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
        _recorder.RecordingEnded += () =>
        {
            if (!IsDisposed && IsHandleCreated) BeginInvoke(async () => await StopRecordingAsync());
        };
        _chooseAudio.Click += (_, _) => ChooseAudio();
        _setApiKey.Click += (_, _) => PromptForApiKey();
        _transcribe.Click += async (_, _) => await TranscribeAsync();
        _liveStart.Click += async (_, _) => await StartLiveAsync();
        _liveStop.Click += async (_, _) => await StopLiveAsync();
        _analyze.Click += (_, _) => Analyze();
        _suggest.Click += (_, _) => AcadApp.DocumentManager.MdiActiveDocument?.SendStringToExecute("HIMEC_SUGGEST ", true, false, false);
        _pick.Click += (_, _) => AcadApp.DocumentManager.MdiActiveDocument?.SendStringToExecute("HIMEC_PICK ", true, false, false);
        _approve.Click += (_, _) => Approve();
        _execute.Click += (_, _) => AcadApp.DocumentManager.MdiActiveDocument?.SendStringToExecute("HIMEC_APPLY ", true, false, false);
        _tagReview.StatusChanged += SetStatus;
        _tagReview.ScanRequested += () => ScanTranscript();
        _tagReview.PickRequested += () => AcadApp.DocumentManager.MdiActiveDocument?.SendStringToExecute("HIMEC_TAG_PICK ", true, false, false);
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
            _liveStart.Enabled = true;
            SetStatus("녹음 중. 로컬 파일은 약 3분/10MB가 상한입니다. 실시간 전사는 별도 동의가 필요합니다.");
        }
        catch (System.Exception ex) { SetStatus("녹음 시작 실패: " + ex.Message); }
    }

    private async Task StopRecordingAsync()
    {
        if (_stoppingRecording || !_stop.Enabled) return;
        _stoppingRecording = true;
        try
        {
            var path = await _recorder.StopAsync();
            await StopLiveAsync();
            SetSelectedAudio(path);
            _tagReview.Finish(path);
            SetStatus("녹음 저장 완료. 전사하려면 API 키와 외부 전송 동의가 필요합니다.");
        }
        catch (System.Exception ex) { SetStatus("녹음 중지 실패: " + ex.Message); }
        finally { _record.Enabled = true; _stop.Enabled = false; _liveStart.Enabled = false; _chooseAudio.Enabled = true; _transcribe.Enabled = true; _stoppingRecording = false; }
    }

    private async Task StartLiveAsync()
    {
        if (!_recorder.IsRecording || _liveClient is not null) return;
        if (string.IsNullOrWhiteSpace(_sessionApiKey) && !OpenAiTranscriber.HasEnvironmentKey && !PromptForApiKey()) return;
        if (!ConfirmLiveUpload()) { SetStatus("실시간 전사 취소 · 로컬 녹음은 계속됩니다."); return; }
        var key = _sessionApiKey ?? Environment.GetEnvironmentVariable("OPENAI_API_KEY");
        var client = new RealtimeTranscriptionClient();
        _liveStart.Enabled = false;
        _liveState.Text = "실시간 전사: 연결 중…";
        client.Partial += delta =>
        {
            if (!IsDisposed) BeginInvoke(() => _livePartial.Text = "말하는 중: " + delta);
        };
        client.Completed += turn =>
        {
            if (IsDisposed) return;
            BeginInvoke(() =>
            {
                _livePartial.Text = "말하는 중: —";
                _transcript.AppendText((string.IsNullOrWhiteSpace(_transcript.Text) ? "" : Environment.NewLine) + turn.Text);
                try
                {
                    var doc = AcadApp.DocumentManager.MdiActiveDocument;
                    var candidates = doc is not null && doc.Name == _liveDrawing
                        ? PluginCommands.GetDrawingCandidates() : [];
                    _tagReview.AddRealtimeTurn(turn, _liveDrawing ?? "도면 미지정", candidates);
                }
                catch (System.Exception ex) { SetStatus("실시간 태그 처리 실패: " + ex.Message); }
            });
        };
        client.Failed += error =>
        {
            if (!IsDisposed) BeginInvoke(async () =>
            {
                _liveState.Text = "실시간 전사: 연결 오류 · 로컬 녹음만";
                SetStatus(error);
                if (ReferenceEquals(_liveClient, client)) await StopLiveAsync();
            });
        };
        try
        {
            await client.StartAsync(key!);
            if (!_recorder.IsRecording)
            {
                await client.StopAsync();
                await client.DisposeAsync();
                return;
            }
            _liveDrawing = AcadApp.DocumentManager.MdiActiveDocument?.Name;
            _liveClient = client;
            _livePcmHandler = pcm => client.QueuePcm(pcm);
            _recorder.PcmAvailable += _livePcmHandler;
            _liveStop.Enabled = true;
            _liveState.Text = "실시간 전사: 전송 중 · 4초마다 문장 확정";
            SetStatus("동의한 현재 녹음의 음성만 OpenAI 실시간 전사로 보내고 있습니다.");
        }
        catch (System.Exception ex)
        {
            await client.DisposeAsync();
            _liveStart.Enabled = _recorder.IsRecording;
            _liveState.Text = "실시간 전사: 연결 실패 · 로컬 녹음만";
            SetStatus(ex.Message.Contains("429", StringComparison.Ordinal)
                ? "실시간 전사 연결 실패: HTTP 429 · OpenAI API 결제·한도·모델 사용 권한을 확인하세요. 로컬 녹음은 계속됩니다."
                : "실시간 전사 연결 실패. 네트워크·API 키·모델 사용 권한을 확인하세요. 로컬 녹음은 계속됩니다.");
        }
    }

    private async Task StopLiveAsync()
    {
        var client = _liveClient;
        if (client is null) return;
        _liveClient = null;
        if (_livePcmHandler is not null) _recorder.PcmAvailable -= _livePcmHandler;
        _livePcmHandler = null;
        _liveStop.Enabled = false;
        try { await client.StopAsync(); }
        catch (System.Exception ex) { SetStatus("실시간 전사 종료 오류: " + ex.Message); }
        finally
        {
            await client.DisposeAsync();
            _liveStart.Enabled = _recorder.IsRecording;
            _liveState.Text = "실시간 전사: 꺼짐 · 로컬 녹음만";
        }
    }

    private static bool ConfirmLiveUpload()
    {
        using var dialog = new Form
        {
            Text = "실시간 음성 외부 전송 동의", Width = 490, Height = 225,
            FormBorderStyle = FormBorderStyle.FixedDialog, StartPosition = FormStartPosition.CenterScreen,
            MaximizeBox = false, MinimizeBox = false
        };
        var explanation = new Label
        {
            Left = 16, Top = 12, Width = 445, Height = 84,
            Text = "실시간 전사를 시작하면 지금부터 중지할 때까지의 마이크 음성 조각이 OpenAI로 전송됩니다. 고객 회의·개인정보가 포함된 음성은 필요한 권한을 확인한 뒤에만 시작하세요. 도면 데이터는 보내지 않습니다."
        };
        var consent = new CheckBox { Left = 16, Top = 103, Width = 440, Text = "현재 녹음의 외부 음성 전송에 동의합니다", Checked = false };
        var accept = new Button { Left = 270, Top = 138, Width = 92, Text = "동의하고 시작", Enabled = false, DialogResult = DialogResult.OK };
        var cancel = new Button { Left = 370, Top = 138, Width = 86, Text = "취소", DialogResult = DialogResult.Cancel };
        consent.CheckedChanged += (_, _) => accept.Enabled = consent.Checked;
        dialog.Controls.AddRange([explanation, consent, accept, cancel]);
        dialog.AcceptButton = accept;
        dialog.CancelButton = cancel;
        return dialog.ShowDialog() == DialogResult.OK && consent.Checked;
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
            var tagsSaved = ScanTranscript();
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

    private bool ScanTranscript()
    {
        var doc = AcadApp.DocumentManager.MdiActiveDocument;
        if (doc is null) return _tagReview.AddTranscriptMentions(_transcript.Text);
        try { return _tagReview.AddTranscriptWithCandidates(_transcript.Text, doc.Name, PluginCommands.GetDrawingCandidates()); }
        catch (System.Exception ex)
        {
            SetStatus("도면 후보 검색 실패: " + ex.Message + ". 직접 객체를 지정할 수 있습니다.");
            return _tagReview.AddTranscriptMentions(_transcript.Text);
        }
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
        _summary.Text = $"제안: 블록 이동 X {change!.DxMm:+0.##;-0.##;0} mm / Y {change.DyMm:+0.##;-0.##;0} mm\nWCS 좌표 기준 · 로컬 규칙 해석 · 실행 전 승인 필수";
        try
        {
            _target.Text = PluginCommands.TrySuggestMoveTarget(change);
            SetStatus(_target.Text);
        }
        catch (System.Exception ex)
        {
            _target.Text = "대상 미지정 — 도면에서 직접 선택하세요.";
            SetStatus("자동 후보 검색 실패: " + ex.Message);
        }
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
        if (disposing)
        {
            if (_livePcmHandler is not null) _recorder.PcmAvailable -= _livePcmHandler;
            _liveClient?.DisposeAsync().AsTask().GetAwaiter().GetResult();
            _recorder.Dispose();
            _tooltips.Dispose();
            _sessionApiKey = null;
        }
        base.Dispose(disposing);
    }
}
