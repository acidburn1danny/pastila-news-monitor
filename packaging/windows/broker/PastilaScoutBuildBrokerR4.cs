using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.ServiceProcess;
using System.Text;
using System.Threading;

internal sealed class PastilaScoutBuildBrokerR4 : ServiceBase
{
    private const string PipeName = "PastilaScout.BuildBroker.R4";
    private const string ConsumerSid = "S-1-5-21-1301541280-2754826440-2262162330-1001";
    private const string BuildRoot = @"C:\PastilaScout-Installer-Build\phase-5.6b\build-20260813-044";
    private const string ToolPath = @"C:\PastilaScout-Installer-Toolchain\phase-5.6b\inno-setup-6-001\toolchain\ISCC.exe";
    private const string ToolSha256 = "0A8757031B33777E4C9CBFFEE40F11A5062B36D25CBE144C1DB73B6102B80AD7";
    private const string ExecutionFlag = @"C:\ProgramData\PastilaScout\BuildBrokerR4\authority\execution-enabled";
    private const string GovernedInput = @"C:\Projects\pastila-news-monitor\packaging\inno\PastilaScout.iss";
    private const string ExecutionAdapter = @"C:\ProgramData\PastilaScout\BuildBrokerR4\config\invoke-build038.ps1";
    private readonly HashSet<string> usedNonces = new HashSet<string>(StringComparer.Ordinal);
    private readonly object nonceLock = new object();
    private Thread worker;
    private volatile bool stopping;

    public PastilaScoutBuildBrokerR4() { ServiceName = "PastilaScoutBuildBrokerR4"; }

    protected override void OnStart(string[] args)
    {
        stopping = false;
        worker = new Thread(Run) { IsBackground = true, Name = "PastilaScoutBuildBrokerR4" };
        worker.Start();
    }

    protected override void OnStop()
    {
        stopping = true;
        try { using (var wake = new NamedPipeClientStream(".", PipeName, PipeDirection.Out)) wake.Connect(250); } catch { }
        if (worker != null) worker.Join(3000);
    }

    private void Run()
    {
        while (!stopping)
        {
            var security = new PipeSecurity();
            security.SetAccessRuleProtection(true, false);
            security.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(WellKnownSidType.LocalSystemSid, null), PipeAccessRights.FullControl, AccessControlType.Allow));
            security.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(WellKnownSidType.BuiltinAdministratorsSid, null), PipeAccessRights.FullControl, AccessControlType.Allow));
            security.AddAccessRule(new PipeAccessRule(new SecurityIdentifier(ConsumerSid), PipeAccessRights.ReadWrite, AccessControlType.Allow));
            using (var pipe = new NamedPipeServerStream(PipeName, PipeDirection.InOut, 1, PipeTransmissionMode.Message, PipeOptions.None, 4096, 4096, security))
            {
                try { pipe.WaitForConnection(); if (!stopping) Handle(pipe); }
                catch { }
            }
        }
    }

    private void Handle(NamedPipeServerStream pipe)
    {
        string callerSid = null;
        try { pipe.RunAsClient(() => callerSid = WindowsIdentity.GetCurrent().User.Value); }
        catch { Reply(pipe, "DENY|CALLER_IDENTITY"); return; }
        if (!String.Equals(callerSid, ConsumerSid, StringComparison.Ordinal)) { Reply(pipe, "DENY|UNAUTHORIZED_CALLER"); return; }
        string request;
        using (var reader = new StreamReader(pipe, new UTF8Encoding(false), false, 4096, true)) request = reader.ReadLine();
        var p = (request ?? "").Split('|');
        if ((p.Length != 7 && p.Length != 9) || p[0] != "R4V1") { Reply(pipe, "DENY|MALFORMED"); return; }
        Guid nonce; long ticks;
        if (!Guid.TryParse(p[1], out nonce) || !Int64.TryParse(p[2], out ticks)) { Reply(pipe, "DENY|MALFORMED"); return; }
        var when = new DateTime(ticks, DateTimeKind.Utc);
        if (Math.Abs((DateTime.UtcNow - when).TotalMinutes) > 2) { Reply(pipe, "DENY|STALE"); return; }
        lock (nonceLock) { if (!usedNonces.Add(nonce.ToString("D"))) { Reply(pipe, "DENY|REPLAY"); return; } }
        if (!ExactPath(p[4], BuildRoot) || !ExactPath(p[5], ToolPath) || !String.Equals(p[6], ToolSha256, StringComparison.OrdinalIgnoreCase)) { Reply(pipe, "DENY|SUBSTITUTION"); return; }
        if (!File.Exists(ToolPath) || !String.Equals(Sha256(ToolPath), ToolSha256, StringComparison.OrdinalIgnoreCase)) { Reply(pipe, "DENY|TOOL_IDENTITY"); return; }
        if (p[3] == "validate") { Reply(pipe, "ACCEPT|VALIDATED|" + callerSid); return; }
        if (p[3] == "build")
        {
            if (!File.Exists(ExecutionFlag)) { Reply(pipe, "DENY|EXECUTION_DISABLED"); return; }
            if (p.Length != 9 || !ExactPath(p[7], GovernedInput) || !File.Exists(GovernedInput) || !String.Equals(Sha256(GovernedInput), p[8], StringComparison.OrdinalIgnoreCase)) { Reply(pipe, "DENY|INPUT_IDENTITY"); return; }
            if (!Monitor.TryEnter(nonceLock)) { Reply(pipe, "DENY|CONCURRENT"); return; }
            try
            {
                if (!File.Exists(ExecutionAdapter)) { Reply(pipe, "DENY|EXECUTION_ADAPTER"); return; }
                var start = new ProcessStartInfo(@"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                    "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" + ExecutionAdapter + "\"")
                    { UseShellExecute = false, CreateNoWindow = true };
                using (var child = Process.Start(start)) { child.WaitForExit(); Reply(pipe, "RESULT|" + child.ExitCode); }
            }
            finally { Monitor.Exit(nonceLock); }
            return;
        }
        Reply(pipe, "DENY|OPERATION");
    }

    private static bool ExactPath(string supplied, string expected)
    {
        try { return String.Equals(Path.GetFullPath(supplied).TrimEnd('\\'), Path.GetFullPath(expected).TrimEnd('\\'), StringComparison.OrdinalIgnoreCase); }
        catch { return false; }
    }

    private static string Sha256(string path)
    {
        using (var hash = System.Security.Cryptography.SHA256.Create())
        using (var stream = File.OpenRead(path)) return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "");
    }

    private static void Reply(Stream pipe, string value)
    {
        var bytes = new UTF8Encoding(false).GetBytes(value + "\n"); pipe.Write(bytes, 0, bytes.Length); pipe.Flush();
    }

    public static void Main() { ServiceBase.Run(new PastilaScoutBuildBrokerR4()); }
}
