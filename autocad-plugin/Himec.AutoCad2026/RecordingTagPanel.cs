using System.Drawing;
using System.Windows.Forms;
using Himec.ChangeCore;

namespace Himec.AutoCad2026;

internal sealed class RecordingTagPanel : UserControl
{
    private readonly DataGridView _grid = new();
    private readonly TextBox _newLabel = new TextBox().WithHint("태그 이름 (예: C1 기둥)");
    private readonly Button _add = new() { Text = "태그 추가" };
    private readonly Button _pickNow = new() { Text = "녹음 중 객체 태그", Enabled = false };
    private readonly Button _link = new() { Text = "선택 태그에 객체 지정" };
    private readonly Button _scan = new() { Text = "전사문에서 객체 찾기" };
    private readonly Button _unlink = new() { Text = "객체 연결 해제" };
    private readonly Button _remove = new() { Text = "선택 태그 삭제" };
    private readonly Button _show = new() { Text = "선택된 객체 확인" };
    private readonly Button _confirm = new() { Text = "제안 연결 확정" };
    private readonly Label _count = new() { Height = 23, ForeColor = PaletteTheme.Muted };
    private RecordingTagSession? _session;
    private bool _isRecording;
    private string? _pendingTagId;
    private bool _pendingNewPick;

    public event Action? PickRequested;
    public event Action? ScanRequested;
    public event Action<string>? StatusChanged;

    /// <summary>The tags the PDF export matches change instructions against.</summary>
    internal RecordingTagSession? Session => _session;

    public RecordingTagPanel()
    {
        Height = 367;
        Width = 340;
        BackColor = PaletteTheme.Surface;
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 7, Margin = Padding.Empty, Padding = Padding.Empty };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 26));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 135));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 38));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 39));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 39));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 39));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 39));
        _count.Dock = DockStyle.Fill;
        _count.Text = "태그 0개 · 녹음/전사문 선택 후 사용";
        layout.Controls.Add(_count, 0, 0); layout.SetColumnSpan(_count, 2);

        _grid.Dock = DockStyle.Fill;
        _grid.BackgroundColor = PaletteTheme.Input;
        _grid.GridColor = PaletteTheme.Border;
        _grid.BorderStyle = BorderStyle.None;
        _grid.RowHeadersVisible = false;
        _grid.AllowUserToAddRows = false;
        _grid.AllowUserToDeleteRows = false;
        _grid.MultiSelect = false;
        _grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
        _grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
        _grid.EnableHeadersVisualStyles = false;
        _grid.ColumnHeadersDefaultCellStyle.BackColor = PaletteTheme.Header;
        _grid.ColumnHeadersDefaultCellStyle.ForeColor = PaletteTheme.Text;
        _grid.DefaultCellStyle.BackColor = PaletteTheme.Input;
        _grid.DefaultCellStyle.ForeColor = PaletteTheme.Text;
        _grid.DefaultCellStyle.SelectionBackColor = PaletteTheme.Status;
        _grid.DefaultCellStyle.SelectionForeColor = PaletteTheme.Text;
        _grid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "시각", ReadOnly = true, FillWeight = 37 });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "태그 (수정 가능)", FillWeight = 90 });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "상태", ReadOnly = true, FillWeight = 62 });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "근거/객체", ReadOnly = true, FillWeight = 130 });
        _grid.CellEndEdit += (_, e) => RenameFromGrid(e.RowIndex, e.ColumnIndex);
        layout.Controls.Add(_grid, 0, 1); layout.SetColumnSpan(_grid, 2);

        _newLabel.Dock = DockStyle.Fill;
        _newLabel.BackColor = PaletteTheme.Input;
        _newLabel.ForeColor = PaletteTheme.Text;
        _newLabel.Margin = new Padding(0, 5, 4, 4);
        layout.Controls.Add(_newLabel, 0, 2);
        AddButton(layout, _add, 1, 2, () => AddManual());
        AddButton(layout, _pickNow, 0, 3, RequestNewPick);
        AddButton(layout, _link, 1, 3, RequestLinkPick);
        AddButton(layout, _scan, 0, 4, () => ScanRequested?.Invoke());
        AddButton(layout, _unlink, 1, 4, UnlinkSelected);
        AddButton(layout, _remove, 0, 5, RemoveSelected);
        AddButton(layout, _show, 1, 5, ShowSelected);
        AddButton(layout, _confirm, 0, 6, ConfirmSelected);
        layout.SetColumnSpan(_confirm, 2);
        Controls.Add(layout);
    }

    private static void AddButton(TableLayoutPanel layout, Button button, int col, int row, Action click)
    {
        PaletteTheme.Button(button);
        button.Dock = DockStyle.Fill;
        button.Margin = new Padding(2, 2, 2, 2);
        button.Click += (_, _) => click();
        layout.Controls.Add(button, col, row);
    }

    public void Start(string recordingPath)
    {
        _session = new RecordingTagSession { RecordingPath = recordingPath, CreatedAt = DateTimeOffset.Now };
        _isRecording = true;
        _pickNow.Enabled = true;
        SaveAndRefresh("녹음 태그 세션을 시작했습니다. 객체를 직접 찍으면 현재 시각이 기록됩니다.");
    }

    public void Finish(string recordingPath)
    {
        if (_session is null || !StringComparer.OrdinalIgnoreCase.Equals(_session.RecordingPath, recordingPath))
            _session = RecordingTagStore.LoadOrCreate(recordingPath);
        _isRecording = false;
        _pickNow.Enabled = false;
        SaveAndRefresh("녹음 태그를 저장했습니다. 전사 후 객체 언급을 추가로 찾을 수 있습니다.");
    }

    public void SelectAudio(string recordingPath)
    {
        _session = RecordingTagStore.LoadOrCreate(recordingPath);
        _isRecording = false;
        _pickNow.Enabled = false;
        RefreshGrid();
    }

    public bool AddTranscriptMentions(string transcript)
    {
        if (_session is null) { StatusChanged?.Invoke("먼저 녹음 파일을 선택하세요."); return false; }
        var added = _session.AddTranscriptMentions(transcript);
        return SaveAndRefresh($"전사문에서 객체 언급 {added}개를 추가했습니다. 미지정 항목은 도면에서 확인하세요.");
    }

    public bool AddTranscriptWithCandidates(string transcript, string drawing,
        IReadOnlyList<RecordingObjectCandidate> candidates)
    {
        if (_session is null) { StatusChanged?.Invoke("먼저 녹음 파일을 선택하세요."); return false; }
        var added = 0;
        foreach (var sentence in System.Text.RegularExpressions.Regex.Split(transcript, @"[.!?\r\n]+"))
        {
            if (string.IsNullOrWhiteSpace(sentence)) continue;
            var id = "file-" + Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(
                System.Text.Encoding.UTF8.GetBytes(sentence.Trim())));
            var tags = RealtimeTagging.AddCompletedTurn(_session,
                new CompletedTranscriptTurn(id, sentence.Trim(), 0), drawing, candidates);
            added += tags.Count;
        }
        return SaveAndRefresh($"객체 언급 {added}개를 찾았습니다. 단일 식별자만 검토 전 제안으로 연결했습니다.");
    }

    public bool AddRealtimeTurn(CompletedTranscriptTurn turn, string drawing,
        IReadOnlyList<RecordingObjectCandidate> candidates)
    {
        if (_session is null) return false;
        var added = RealtimeTagging.AddCompletedTurn(_session, turn, drawing, candidates);
        return SaveAndRefresh($"실시간 확정 문장에서 객체 언급 {added.Count}개를 찾았습니다. 자동 연결은 확인 후 확정하세요.");
    }

    private void ShowSelected()
    {
        var id = SelectedId();
        if (id is null || _session is null) { StatusChanged?.Invoke("목록에서 태그를 먼저 선택하세요."); return; }
        var tag = _session.Find(id);
        StatusChanged?.Invoke(!tag.IsLinked
            ? "이 태그는 아직 객체가 지정되지 않았습니다. 도면에서 직접 선택하세요."
            : PluginCommands.ShowSelectedObject(tag.Drawing!, tag.Handle!));
    }

    private void ConfirmSelected()
    {
        var id = SelectedId();
        if (id is null || _session is null) { StatusChanged?.Invoke("목록에서 태그를 먼저 선택하세요."); return; }
        try
        {
            _session.Confirm(id, DateTimeOffset.Now);
            SaveAndRefresh("이 객체 연결을 사용자가 확정했습니다. 도면은 수정하지 않았습니다.");
        }
        catch (Exception ex) { StatusChanged?.Invoke("연결 확정 실패: " + ex.Message); }
    }

    private void AddManual()
    {
        if (_session is null) { StatusChanged?.Invoke("먼저 녹음하거나 WAV를 선택하세요."); return; }
        try
        {
            _session.AddManual(_newLabel.Text, CurrentOffset());
            _newLabel.Clear();
            SaveAndRefresh("태그를 추가했습니다. 객체는 별도로 지정할 수 있습니다.");
        }
        catch (Exception ex) { StatusChanged?.Invoke("태그 추가 실패: " + ex.Message); }
    }

    private void RequestNewPick()
    {
        if (_session is null || !_isRecording) { StatusChanged?.Invoke("녹음 중에만 즉시 객체 태그를 사용할 수 있습니다."); return; }
        _pendingNewPick = true;
        _pendingTagId = null;
        PickRequested?.Invoke();
    }

    private void RequestLinkPick()
    {
        var id = SelectedId();
        if (id is null) { StatusChanged?.Invoke("목록에서 태그를 먼저 선택하세요."); return; }
        _pendingNewPick = false;
        _pendingTagId = id;
        PickRequested?.Invoke();
    }

    public void CompletePick(string drawing, string handle, string entityType, string layer)
    {
        if (_session is null) { StatusChanged?.Invoke("태그 세션이 없습니다."); return; }
        try
        {
            var id = _pendingNewPick
                ? _session.AddManual(string.IsNullOrWhiteSpace(_newLabel.Text) ? "수동 지정 객체" : _newLabel.Text, CurrentOffset()).Id
                : _pendingTagId ?? throw new InvalidOperationException("선택된 태그가 없습니다.");
            _session.Link(id, drawing, handle, entityType, layer);
            _newLabel.Clear();
            SaveAndRefresh($"객체 {handle}을(를) 태그에 연결했습니다. 도면 자체는 수정하지 않았습니다.");
        }
        catch (Exception ex) { StatusChanged?.Invoke("객체 태그 실패: " + ex.Message); }
        finally { _pendingTagId = null; _pendingNewPick = false; }
    }

    private double? CurrentOffset() => _isRecording && _session is not null
        ? Math.Max(0, (DateTimeOffset.Now - _session.CreatedAt).TotalSeconds)
        : null;

    private void RenameFromGrid(int rowIndex, int columnIndex)
    {
        if (columnIndex != 1 || _session is null || rowIndex < 0 || rowIndex >= _grid.Rows.Count) return;
        var id = _grid.Rows[rowIndex].Tag as string;
        if (id is null) return;
        try
        {
            _session.Rename(id, Convert.ToString(_grid.Rows[rowIndex].Cells[1].Value) ?? "");
            SaveAndRefresh("태그 이름을 수정했습니다.");
        }
        catch (Exception ex) { StatusChanged?.Invoke("태그 수정 실패: " + ex.Message); RefreshGrid(); }
    }

    private void UnlinkSelected()
    {
        var id = SelectedId();
        if (id is null || _session is null) { StatusChanged?.Invoke("목록에서 태그를 먼저 선택하세요."); return; }
        _session.Unlink(id);
        SaveAndRefresh("객체 연결을 해제했습니다. 태그 행은 남아 있습니다.");
    }

    private void RemoveSelected()
    {
        var id = SelectedId();
        if (id is null || _session is null) { StatusChanged?.Invoke("목록에서 태그를 먼저 선택하세요."); return; }
        var label = _session.Find(id).Label;
        if (MessageBox.Show($"'{label}' 태그를 목록에서 삭제할까요? 도면 객체는 삭제되지 않습니다.",
                "태그 삭제 확인", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
        _session.Remove(id);
        SaveAndRefresh("선택 태그를 삭제했습니다. 도면 객체는 삭제하지 않았습니다.");
    }

    private string? SelectedId() => _grid.CurrentRow?.Tag as string;

    private bool SaveAndRefresh(string message)
    {
        if (_session is null) return false;
        try { RecordingTagStore.Save(_session); RefreshGrid(); StatusChanged?.Invoke(message); return true; }
        catch (Exception ex) { StatusChanged?.Invoke("태그 저장 실패: " + ex.Message); RefreshGrid(); return false; }
    }

    private void RefreshGrid()
    {
        _grid.Rows.Clear();
        foreach (var tag in _session?.Tags ?? [])
        {
            var time = tag.OffsetSeconds is double seconds ? TimeSpan.FromSeconds(seconds).ToString(@"mm\:ss") : "—";
            var state = tag.EffectiveSuggestionStatus switch
            {
                RecordingTagSuggestionStatus.Proposed => "제안 연결 · 확인 필요",
                RecordingTagSuggestionStatus.Confirmed => "사용자 확정",
                _ => tag.IsLinked ? "지정 완료" : "선택 필요"
            };
            var row = _grid.Rows[_grid.Rows.Add(time, tag.Label, state,
                tag.IsLinked ? $"{Path.GetFileName(tag.Drawing)} #{tag.Handle} · {tag.Layer}" : tag.SourceQuote)];
            row.Tag = tag.Id;
            row.Cells[3].ToolTipText = tag.IsLinked ? $"{tag.Drawing}\n{tag.EntityType} / {tag.Layer}" : tag.SourceQuote;
        }
        var total = _session?.Tags.Count ?? 0;
        var linked = _session?.Tags.Count(t => t.IsLinked) ?? 0;
        _count.Text = $"태그 {total}개 · 연결 {linked}개 · 선택 필요 {total - linked}개";
        _grid.ClearSelection();
        _grid.CurrentCell = null;
    }
}
