namespace Himec.ChangeCore;

public sealed class ChangeInstruction
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string SourceText { get; set; } = "";
    public string Action { get; set; } = "move";
    public string? TargetHandle { get; set; }
    public string? TargetDrawing { get; set; }
    public double DxMm { get; set; }
    public double DyMm { get; set; }
    public string Status { get; set; } = "needs_review";
    public string InterpretationMode { get; set; } = "local_rule";
    public string? Reviewer { get; set; }
    public DateTimeOffset? ReviewedAt { get; set; }
    public DateTimeOffset? ExecutedAt { get; set; }
}
