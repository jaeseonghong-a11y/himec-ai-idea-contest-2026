using System.Drawing;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Runtime.Loader;
using System.Windows.Forms;
using NAudio.Wave;
using Himec.ChangeCore;

namespace Himec.PalettePreview;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        if (args.Length > 0 && args[0] == "--test-wav")
        {
            var destination = args.Length > 1 ? args[1] : throw new ArgumentException("Output WAV path required.");
            if (File.Exists(destination)) throw new IOException("Test WAV already exists; refusing overwrite.");
            using (var writer = new WaveFileWriter(destination, new WaveFormat(16000, 16, 1)))
                writer.Write(new byte[32000], 0, 32000);
            Console.WriteLine(destination);
            return;
        }
        AssemblyLoadContext.Default.Resolving += (_, name) =>
        {
            var path = Path.Combine(@"C:\Program Files\Autodesk\AutoCAD 2026", name.Name + ".dll");
            return File.Exists(path) ? AssemblyLoadContext.Default.LoadFromAssemblyPath(path) : null;
        };
        ApplicationConfiguration.Initialize();
        var pluginPath = Path.Combine(AppContext.BaseDirectory, "Himec.AutoCad2026.dll");
        var type = AssemblyLoadContext.Default.LoadFromAssemblyPath(pluginPath).GetType("Himec.AutoCad2026.ReviewPanel")
            ?? throw new InvalidOperationException("ReviewPanel type not found.");
        using var panel = (Control)(Activator.CreateInstance(type, nonPublic: true)
            ?? throw new InvalidOperationException("ReviewPanel construction failed."));
        if (args.Length > 0 && args[0] == "--self-test")
        {
            TestAudioPickerState(type, panel);
            return;
        }
        using var form = new Form
        {
            Text = "HIMEC palette preview — no AutoCAD commands",
            ClientSize = new Size(420, args.Length > 1 && int.TryParse(args[1], out var height) ? height : 640),
            StartPosition = FormStartPosition.Manual,
            Location = new Point(30, 30)
        };
        form.Controls.Add(panel);
        form.Show();
        Application.DoEvents();
        using var bitmap = new Bitmap(form.ClientSize.Width, form.ClientSize.Height);
        form.DrawToBitmap(bitmap, new Rectangle(Point.Empty, bitmap.Size));
        var output = args.Length > 0 ? args[0] : Path.Combine(Path.GetTempPath(), "himec-palette-preview.png");
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
        bitmap.Save(output);
        Console.WriteLine(output);
        form.Close();
    }

    private static void TestAudioPickerState(Type type, Control panel)
    {
        var path = Path.Combine(Path.GetTempPath(), "himec-preview-test-" + Guid.NewGuid().ToString("N") + ".wav");
        var store = type.Assembly.GetType("Himec.AutoCad2026.RecordingTagStore")
            ?? throw new InvalidOperationException("RecordingTagStore not found.");
        var sessionPath = (string)(store.GetMethod("SessionFile", BindingFlags.Static | BindingFlags.NonPublic)?.Invoke(null, [path])
            ?? throw new InvalidOperationException("SessionFile not found."));
        try
        {
            using (var writer = new WaveFileWriter(path, new WaveFormat(16000, 16, 1)))
                writer.Write(new byte[32000], 0, 32000);
            var select = type.GetMethod("SetSelectedAudio", BindingFlags.Instance | BindingFlags.NonPublic)
                ?? throw new InvalidOperationException("SetSelectedAudio not found.");
            select.Invoke(panel, [path]);
            var info = (Label)(type.GetField("_recordingInfo", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(panel)
                ?? throw new InvalidOperationException("Recording info not found."));
            if (!info.Text.Contains("1.0초", StringComparison.Ordinal))
                throw new InvalidOperationException("Synthetic WAV duration was not shown.");
            type.GetMethod("SetStatus")!.Invoke(panel, ["전사 실패: 시험 오류"]);
            var status = (Label)(type.GetField("_status", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(panel)
                ?? throw new InvalidOperationException("Status label not found."));
            if (!status.Text.Contains("전사 실패", StringComparison.Ordinal))
                throw new InvalidOperationException("Transcription error was not shown.");
            var tagPanel = type.GetField("_tagReview", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(panel)
                ?? throw new InvalidOperationException("Tag review panel not found.");
            var tagType = tagPanel.GetType();
            tagType.GetMethod("AddTranscriptMentions")!.Invoke(tagPanel, ["C1 기둥을 옮기자. 덕트도 확인하자."]);
            var grid = (DataGridView)(tagType.GetField("_grid", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(tagPanel)
                ?? throw new InvalidOperationException("Tag grid not found."));
            if (grid.Rows.Count != 2) throw new InvalidOperationException("Transcript tag rows were not shown.");
            grid.CurrentCell = grid.Rows[0].Cells[1];
            tagType.GetField("_pendingTagId", BindingFlags.Instance | BindingFlags.NonPublic)!
                .SetValue(tagPanel, grid.Rows[0].Tag as string);
            tagType.GetMethod("CompletePick")!.Invoke(tagPanel, ["synthetic.dxf", "1A", "BlockReference", "COLUMN"]);
            if (Convert.ToString(grid.Rows[0].Cells[2].Value) != "지정 완료")
                throw new InvalidOperationException("Tag-object link was not shown.");
            if (!File.Exists(sessionPath)) throw new InvalidOperationException("Tag session was not saved.");
            var transcriber = type.Assembly.GetType("Himec.AutoCad2026.OpenAiTranscriber")
                ?? throw new InvalidOperationException("Transcriber not found.");
            var describe = transcriber.GetMethod("DescribeError", BindingFlags.Static | BindingFlags.NonPublic)
                ?? throw new InvalidOperationException("Error mapper not found.");
            var quota = (string)(describe.Invoke(null, [429, "{\"error\":{\"code\":\"credit_balance_exhausted\"}}"])
                ?? throw new InvalidOperationException("No quota message."));
            if (!quota.Contains("잔액") || quota.Contains("파일 형식"))
                throw new InvalidOperationException("429 quota reason was not distinguished from file format.");
            var noLeak = (string)(describe.Invoke(null, [429, "{\"error\":{\"code\":\"secret-value\"}}"])
                ?? throw new InvalidOperationException("No generic 429 message."));
            if (noLeak.Contains("secret-value")) throw new InvalidOperationException("Untrusted error code leaked into UI.");
            describe.Invoke(null, [429, "{\"error\":\"malformed\"}"]);
            TestGeminiHttp(type);
            var speechProvider = (ComboBox)(type.GetField("_speechProvider", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(panel)
                ?? throw new InvalidOperationException("Speech provider selector not found."));
            var reviewProvider = (ComboBox)(type.GetField("_reviewProvider", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(panel)
                ?? throw new InvalidOperationException("Review provider selector not found."));
            if (speechProvider.Items.Count != 2 || reviewProvider.Items.Count != 3 ||
                speechProvider.Items[1]?.ToString() != "Gemini" || reviewProvider.Items[2]?.ToString() != "Claude")
                throw new InvalidOperationException("Provider choices differ from supported capabilities.");
            var geminiType = type.Assembly.GetType("Himec.AutoCad2026.GeminiLiveTranscriptionClient")
                ?? throw new InvalidOperationException("Gemini live client not found.");
            var setup = (string)geminiType.GetField("SetupMessage", BindingFlags.Static | BindingFlags.NonPublic)!.GetRawConstantValue()!;
            using (var setupJson = System.Text.Json.JsonDocument.Parse(setup))
                if (setupJson.RootElement.GetProperty("setup").GetProperty("model").GetString() != "models/gemini-3.5-transcribe-live")
                    throw new InvalidOperationException("Gemini live model contract differs from documentation.");
            var pcm = new byte[12];
            for (short i = 0; i < 6; i++) BitConverter.TryWriteBytes(pcm.AsSpan(i * 2), i * 100);
            var downsample = geminiType.GetMethod("Downsample24To16", BindingFlags.Static | BindingFlags.NonPublic)!;
            var arguments = new object[] { pcm, Array.Empty<short>() };
            var converted = (byte[])downsample.Invoke(null, arguments)!;
            if (converted.Length != 8 || BitConverter.ToInt16(converted, 0) != 0 ||
                BitConverter.ToInt16(converted, 2) != 150 || BitConverter.ToInt16(converted, 4) != 300)
                throw new InvalidOperationException("Gemini PCM resampling failed.");
            var geminiLive = Activator.CreateInstance(geminiType, nonPublic: true)!;
            try
            {
                if ((bool)geminiType.GetMethod("QueuePcm")!.Invoke(geminiLive, [pcm])!)
                    throw new InvalidOperationException("Gemini accepted PCM before consent and setup.");
                CompletedTranscriptTurn? geminiTurn = null;
                geminiType.GetEvent("Completed")!.AddEventHandler(geminiLive,
                    new Action<CompletedTranscriptTurn>(turn => geminiTurn = turn));
                geminiType.GetMethod("HandleEvent", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(geminiLive,
                    ["{\"serverContent\":{\"inputTranscription\":{\"text\":\"C2 기둥\"}}}"]);
                if (geminiTurn?.Text != "C2 기둥") throw new InvalidOperationException("Gemini final transcript not parsed.");
            }
            finally { ((IAsyncDisposable)geminiLive).DisposeAsync().AsTask().GetAwaiter().GetResult(); }
            var candidates = new List<RecordingObjectCandidate>
            {
                new("synthetic.dxf", "A1", new[] { "C2" }, "BlockReference", "COLUMN"),
                new("synthetic.dxf", "A2", new[] { "B12" }, "BlockReference", "BEAM"),
                new("synthetic.dxf", "A3", new[] { "B12" }, "BlockReference", "BEAM")
            };
            tagType.GetMethod("AddTranscriptWithCandidates")!.Invoke(tagPanel,
                ["C2 기둥을 옮기자. B12도 확인하자.", "synthetic.dxf", candidates]);
            if (!grid.Rows.Cast<DataGridViewRow>().Any(r => Convert.ToString(r.Cells[1].Value) == "C2" &&
                    Convert.ToString(r.Cells[2].Value)!.Contains("제안 연결")))
                throw new InvalidOperationException("Unique drawing identifier did not create a proposed link.");
            if (!grid.Rows.Cast<DataGridViewRow>().Any(r => Convert.ToString(r.Cells[1].Value) == "B12" &&
                    Convert.ToString(r.Cells[2].Value) == "선택 필요"))
                throw new InvalidOperationException("Ambiguous drawing identifier was auto-linked.");
            var liveType = type.Assembly.GetType("Himec.AutoCad2026.RealtimeTranscriptionClient")
                ?? throw new InvalidOperationException("Realtime client not found.");
            var endpoint = (Uri)liveType.GetField("Endpoint", BindingFlags.Static | BindingFlags.NonPublic)!.GetValue(null)!;
            if (endpoint.Query != "?intent=transcription" || endpoint.Query.Contains("model="))
                throw new InvalidOperationException("Live transcription endpoint is not transcription-only.");
            var sessionUpdate = (string)liveType.GetField("SessionUpdateMessage", BindingFlags.Static | BindingFlags.NonPublic)!.GetRawConstantValue()!;
            using (var sessionJson = System.Text.Json.JsonDocument.Parse(sessionUpdate))
            {
                var input = sessionJson.RootElement.GetProperty("session").GetProperty("audio").GetProperty("input");
                if (input.GetProperty("format").GetProperty("rate").GetInt32() != 24000 ||
                    input.GetProperty("transcription").GetProperty("model").GetString() != "gpt-live-transcribe" ||
                    input.GetProperty("turn_detection").ValueKind != System.Text.Json.JsonValueKind.Null)
                    throw new InvalidOperationException("Live session configuration differs from the 24 kHz manual-commit contract.");
            }
            var live = Activator.CreateInstance(liveType, nonPublic: true)!;
            try
            {
                if ((bool)liveType.GetMethod("QueuePcm")!.Invoke(live, [new byte[9600]])!)
                    throw new InvalidOperationException("PCM was accepted before consent and session readiness.");
                CompletedTranscriptTurn? completed = null;
                liveType.GetEvent("Completed")!.AddEventHandler(live,
                    new Action<CompletedTranscriptTurn>(turn => completed = turn));
                liveType.GetMethod("HandleEvent", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(live,
                    ["{\"type\":\"conversation.item.input_audio_transcription.completed\",\"item_id\":\"item-test\",\"transcript\":\"C2 기둥\"}"]);
                if (completed?.Id != "item-test" || completed.Text != "C2 기둥")
                    throw new InvalidOperationException("Completed live transcript was not parsed.");
                tagType.GetMethod("AddRealtimeTurn")!.Invoke(tagPanel,
                    [completed, "synthetic.dxf", candidates]);
                var liveRow = grid.Rows.Cast<DataGridViewRow>().FirstOrDefault(r =>
                    Convert.ToString(r.Cells[1].Value) == "C2" &&
                    Convert.ToString(r.Cells[2].Value)!.Contains("제안 연결"));
                if (liveRow is null) throw new InvalidOperationException("Final live turn did not create a proposed tag.");
                grid.CurrentCell = liveRow.Cells[1];
                tagType.GetMethod("ConfirmSelected", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(tagPanel, null);
                if (!grid.Rows.Cast<DataGridViewRow>().Any(r => Convert.ToString(r.Cells[2].Value) == "사용자 확정"))
                    throw new InvalidOperationException("Proposed tag was not confirmed by the user action.");
                ((Task)liveType.GetMethod("StopAsync")!.Invoke(live, null)!).GetAwaiter().GetResult();
                if ((bool)liveType.GetMethod("QueuePcm")!.Invoke(live, [new byte[9600]])!)
                    throw new InvalidOperationException("PCM was accepted after live transcription stop.");
            }
            finally { ((IAsyncDisposable)live).DisposeAsync().AsTask().GetAwaiter().GetResult(); }
            Console.WriteLine("Palette audio, error, transcript-tag list, object-link and local-save checks passed");
        }
        finally
        {
            if (File.Exists(path)) File.Delete(path);
            if (File.Exists(sessionPath)) File.Delete(sessionPath);
        }
    }

    private static void TestGeminiHttp(Type panelType)
    {
        var providers = panelType.Assembly.GetType("Himec.AutoCad2026.AiProviders")!;
        var send = providers.GetMethod("SendGeminiTranscriptionAsync", BindingFlags.Static | BindingFlags.NonPublic)!;
        var describe = providers.GetMethod("DescribeHttpError", BindingFlags.Static | BindingFlags.NonPublic)!;
        var providerEnum = panelType.Assembly.GetType("Himec.AutoCad2026.AiProvider")!;
        var gemini = Enum.Parse(providerEnum, "Gemini");
        var message = (string)describe.Invoke(null, [gemini, 503, 3])!;
        if (!message.Contains("과부하") || message.Contains("결제") || message.Contains("test-secret"))
            throw new InvalidOperationException("503 incorrectly diagnosed as an account issue.");
        using var handler = new FakeGeminiHandler([503, 503, 200]);
        using var client = new HttpClient(handler);
        var pause = new Func<TimeSpan, Task>(_ => Task.CompletedTask);
        var task = (Task)send.Invoke(null, [client, new { contents = Array.Empty<object>() }, "test-secret", pause])!;
        task.GetAwaiter().GetResult();
        var result = task.GetType().GetProperty("Result")!.GetValue(task)!;
        if (handler.Requests.Count != 3 ||
            handler.Requests[0] != "gemini-3.8-flash" ||
            handler.Requests[1] != "gemini-3.8-flash" ||
            handler.Requests[2] != "gemini-3.5-flash" ||
            (string)result.GetType().GetProperty("Text")!.GetValue(result)! != "C1 기둥")
            throw new InvalidOperationException("Gemini bounded retry/fallback failed.");
        using var deniedHandler = new FakeGeminiHandler([403, 200]);
        using var deniedClient = new HttpClient(deniedHandler);
        try
        {
            ((Task)send.Invoke(null, [deniedClient, new { }, "test-secret", pause])!).GetAwaiter().GetResult();
            throw new InvalidOperationException("Gemini 403 unexpectedly succeeded.");
        }
        catch (InvalidOperationException ex) when (ex.Message.Contains("403")) { }
        if (deniedHandler.Requests.Count != 1) throw new InvalidOperationException("Auth failure was retried.");
        using var quotaHandler = new FakeGeminiHandler([429, 200]);
        using var quotaClient = new HttpClient(quotaHandler);
        try
        {
            ((Task)send.Invoke(null, [quotaClient, new { }, "test-secret", pause])!).GetAwaiter().GetResult();
            throw new InvalidOperationException("Gemini 429 unexpectedly succeeded.");
        }
        catch (InvalidOperationException ex) when (ex.Message.Contains("429")) { }
        if (quotaHandler.Requests.Count != 1) throw new InvalidOperationException("Quota failure was retried.");
    }

    private sealed class FakeGeminiHandler(int[] statuses) : HttpMessageHandler
    {
        public List<string> Requests { get; } = [];
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            if (request.Headers.GetValues("x-goog-api-key").Single() != "test-secret")
                throw new InvalidOperationException("Gemini key header was lost.");
            Requests.Add(request.RequestUri!.AbsolutePath.Split('/')[3].Split(':')[0]);
            var status = statuses[Math.Min(Requests.Count - 1, statuses.Length - 1)];
            var body = status == 200 ? "{\"candidates\":[{\"content\":{\"parts\":[{\"text\":\"C1 기둥\"}]}}]}" : "{\"error\":{\"message\":\"secret-value\"}}";
            return Task.FromResult(new HttpResponseMessage((HttpStatusCode)status) { Content = new StringContent(body) });
        }
    }
}
