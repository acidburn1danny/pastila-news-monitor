#ifndef PayloadFilesInclude
  #error PayloadFilesInclude is required
#endif
#ifndef PayloadVerifyInclude
  #error PayloadVerifyInclude is required
#endif
#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif
#ifndef FrozenIcon
  #error FrozenIcon is required
#endif
#ifndef PayloadBytes
  #error PayloadBytes is required
#endif

[Setup]
AppId=PastilaScout
AppName=Pastila Scout
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\PastilaScout
DefaultGroupName=Pastila Scout
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
DisableProgramGroupPage=yes
UsePreviousAppDir=no
UsePreviousGroup=no
UninstallDisplayName=Pastila Scout
UninstallDisplayIcon={app}\app\PastilaScout.exe
Uninstallable=yes
CreateUninstallRegKey=yes
SetupIconFile={#FrozenIcon}
OutputDir={#OutputDir}
#ifdef PASTILA_VM01A_TEST_INSTRUMENTATION
OutputBaseFilename=PastilaScout-{#AppVersion}-VM01A-Test-Setup
#elif defined(PASTILA_VM05_TEST_INSTRUMENTATION)
OutputBaseFilename=PastilaScout-{#AppVersion}-VM05-Test-Setup
#else
OutputBaseFilename=PastilaScout-{#AppVersion}-Setup
#endif
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
RestartApplications=no
CloseApplications=yes
CloseApplicationsFilter=PastilaScout.exe,pastila-scout.exe
AllowCancelDuringInstall=yes
ChangesAssociations=no
ChangesEnvironment=no

[Tasks]
Name: desktopicon; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
#include PayloadFilesInclude

[Icons]
Name: "{userprograms}\Pastila Scout"; Filename: "{app}\app\PastilaScout.exe"; WorkingDir: "{app}"; IconFilename: "{app}\app\PastilaScout.exe"; Check: ActivationSucceeded
Name: "{userdesktop}\Pastila Scout"; Filename: "{app}\app\PastilaScout.exe"; WorkingDir: "{app}"; IconFilename: "{app}\app\PastilaScout.exe"; Tasks: desktopicon; Check: ActivationSucceeded

[UninstallDelete]
Type: dirifempty; Name: "{app}"

[Code]
const
  AppDirectoryName = 'app';
  StateRoaming = 'PastilaScout';
  StateLocal = 'PastilaScout';
  SafetyMarginBytes = 67108864;
  InstallerOverheadBytes = 16777216;
  ErrorSuccess = 0;
  ErrorMoreData = 234;
  WmClose = $0010;
  GwOwner = 4;
  InteractiveCloseTimeoutMs = 30000;
  InstallerResultRetentionCount = 10;
#ifdef PASTILA_VM05_TEST_INSTRUMENTATION
  Vm05BarrierTimeoutMs = 120000;
  SynchronizeAccess = $00100000;
  ErrorAlreadyExists = 183;
#endif
#ifdef PASTILA_VM01A_TEST_INSTRUMENTATION
  Vm01aBarrierTimeoutMs = 120000;
  Vm01aSynchronizeAccess = $00100000;
  Vm01aErrorAlreadyExists = 183;
#endif

type
#ifdef PASTILA_VM01A_TEST_INSTRUMENTATION
  TVm01aFileTime = record
    LowDateTime: LongWord;
    HighDateTime: LongWord;
  end;
#endif
  TRmUniqueProcess = record
    ProcessId: LongWord;
    ProcessStartTimeLow: LongWord;
    ProcessStartTimeHigh: LongWord;
  end;
  TRmProcessInfo = record
    Process: TRmUniqueProcess;
    AppName: array[0..256] of Char;
    ServiceShortName: array[0..63] of Char;
    ApplicationType: LongWord;
    AppStatus: LongWord;
    SessionId: LongWord;
    Restartable: LongBool;
  end;
  TRmProcessInfoArray = array of TRmProcessInfo;
  TProcessIdArray = array of LongWord;

var
  StageName: String;
  OldName: String;
  ActivationComplete: Boolean;
  ActivationFailureMessage: String;
  RestartManagerProcessIds: TProcessIdArray;
  SetupInitialized: Boolean;
  ResultWritten: Boolean;
  ResultWriteFailed: Boolean;
  OperationType: String;
  FailureClass: String;
  FailureStage: String;
  RestorationStatus: String;
  StageCleanupStatus: String;
  ExistingSurfacesAtStart: Boolean;
  ResidualPath: String;
  TransactionSnapshotTaken: Boolean;
  TransactionResolved: Boolean;
  TransactionCommitted: Boolean;
  PublicationFailed: Boolean;
  AggregateCleanupSucceeded: Boolean;
  PriorPayloadExisted: Boolean;
  PriorArpExisted: Boolean;
  PriorUninstallerExeExisted: Boolean;
  PriorUninstallerDatExisted: Boolean;
  PriorShortcutExisted: Boolean;
  PriorArpDisplayName: String;
  PriorArpDisplayVersion: String;
  PriorArpInstallLocation: String;
  PriorArpDisplayIcon: String;
  PriorArpUninstallString: String;
  TransactionSnapshotRoot: String;
  InitiatingFailurePresent: Boolean;
  PriorPayloadGuiSha256: String;
  PriorPayloadCliSha256: String;

function GetFileAttributesW(lpFileName: String): Longint;
  external 'GetFileAttributesW@kernel32.dll stdcall';
function GetTickCount64(): Int64;
  external 'GetTickCount64@kernel32.dll stdcall';
procedure ExitProcess(ExitCode: LongWord);
  external 'ExitProcess@kernel32.dll stdcall';
function RmStartSession(var SessionHandle: LongWord; SessionFlags: LongWord;
  SessionKey: String): LongWord;
  external 'RmStartSession@rstrtmgr.dll stdcall';
function RmRegisterResources(SessionHandle, FileCount: LongWord;
  var Filenames: LongWord; ApplicationCount: LongWord; Applications: LongWord;
  ServiceCount: LongWord; Services: LongWord): LongWord;
  external 'RmRegisterResources@rstrtmgr.dll stdcall';
function RmGetList(SessionHandle: LongWord; var ProcessInfoNeeded,
  ProcessInfoCount: LongWord; var ProcessInfo: TRmProcessInfo;
  var RebootReasons: LongWord): LongWord;
  external 'RmGetList@rstrtmgr.dll stdcall';
function RmEndSession(SessionHandle: LongWord): LongWord;
  external 'RmEndSession@rstrtmgr.dll stdcall';
function EnumWindows(Callback, Data: LongWord): Boolean;
  external 'EnumWindows@user32.dll stdcall';
function GetWindowThreadProcessId(Window: HWND; var ProcessId: LongWord): LongWord;
  external 'GetWindowThreadProcessId@user32.dll stdcall';
function GetWindow(Window: HWND; Command: LongWord): HWND;
  external 'GetWindow@user32.dll stdcall';
function IsWindowVisible(Window: HWND): Boolean;
  external 'IsWindowVisible@user32.dll stdcall';
function PostMessage(Window: HWND; Message: LongWord; WParam, LParam: LongWord): Boolean;
  external 'PostMessageW@user32.dll stdcall';
#ifdef PASTILA_VM05_TEST_INSTRUMENTATION
function CreateEvent(SecurityAttributes: LongWord; ManualReset, InitialState: Boolean;
  Name: String): LongWord;
  external 'CreateEventW@kernel32.dll stdcall';
function OpenEvent(DesiredAccess: LongWord; InheritHandle: Boolean;
  Name: String): LongWord;
  external 'OpenEventW@kernel32.dll stdcall';
function SetEvent(EventHandle: LongWord): Boolean;
  external 'SetEvent@kernel32.dll stdcall';
function WaitForSingleObject(Handle: LongWord; Milliseconds: LongWord): LongWord;
  external 'WaitForSingleObject@kernel32.dll stdcall';
function CloseHandle(Handle: LongWord): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';
function GetLastError(): LongWord;
  external 'GetLastError@kernel32.dll stdcall';
#endif
#ifdef PASTILA_VM01A_TEST_INSTRUMENTATION
function Vm01aCreateEvent(SecurityAttributes: LongWord; ManualReset,
  InitialState: Boolean; Name: String): LongWord;
  external 'CreateEventW@kernel32.dll stdcall';
function Vm01aOpenEvent(DesiredAccess: LongWord; InheritHandle: Boolean;
  Name: String): LongWord;
  external 'OpenEventW@kernel32.dll stdcall';
function Vm01aSetEvent(EventHandle: LongWord): Boolean;
  external 'SetEvent@kernel32.dll stdcall';
function Vm01aWaitForSingleObject(Handle: LongWord;
  Milliseconds: LongWord): LongWord;
  external 'WaitForSingleObject@kernel32.dll stdcall';
function Vm01aCloseHandle(Handle: LongWord): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';
function Vm01aGetLastError(): LongWord;
  external 'GetLastError@kernel32.dll stdcall';
function GetCurrentProcessId(): LongWord;
  external 'GetCurrentProcessId@kernel32.dll stdcall';
function Vm01aGetCurrentProcess(): LongWord;
  external 'GetCurrentProcess@kernel32.dll stdcall';
function Vm01aGetProcessTimes(ProcessHandle: LongWord;
  var CreationTime, ExitTime, KernelTime, UserTime: TVm01aFileTime): Boolean;
  external 'GetProcessTimes@kernel32.dll stdcall';
#endif

procedure RegisterRestartManagerResource(const SessionHandle: LongWord;
  const Filename: String); forward;
procedure RecordActivationFailure(const MessageText: String); forward;
procedure WriteFinalOperationResult(); forward;

#ifdef PASTILA_VM05_TEST_INSTRUMENTATION
function Vm05Barrier(const BarrierId: String): Boolean;
var
  ArrivedHandle, ContinueHandle, WaitResult: LongWord;
  ArrivedName, ContinueName: String;
begin
  Result := False;
  ArrivedName := 'Local\PastilaScout_VM05_' + BarrierId + '_Arrived';
  ContinueName := 'Local\PastilaScout_VM05_' + BarrierId + '_Continue';
  ArrivedHandle := CreateEvent(0, False, False, ArrivedName);
  if ArrivedHandle = 0 then begin
    Log('Phase 5.6B VM-05 test barrier could not create its arrival event: ' + BarrierId);
    exit;
  end;
  try
    if GetLastError() = ErrorAlreadyExists then begin
      Log('Phase 5.6B VM-05 test barrier rejected a stale arrival event: ' + BarrierId);
      exit;
    end;
    ContinueHandle := OpenEvent(SynchronizeAccess, False, ContinueName);
    if ContinueHandle = 0 then begin
      Log('Phase 5.6B VM-05 test barrier controller is absent: ' + BarrierId);
      exit;
    end;
    try
      if not SetEvent(ArrivedHandle) then begin
        Log('Phase 5.6B VM-05 test barrier could not signal arrival: ' + BarrierId);
        exit;
      end;
      WaitResult := WaitForSingleObject(ContinueHandle, Vm05BarrierTimeoutMs);
      if WaitResult <> 0 then begin
        Log('Phase 5.6B VM-05 test barrier timed out or failed: ' + BarrierId);
        exit;
      end;
      Result := True;
    finally
      CloseHandle(ContinueHandle);
    end;
  finally
    CloseHandle(ArrivedHandle);
  end;
end;

procedure RecordVm05BarrierFailure(const BarrierId: String);
begin
  RecordActivationFailure('VM-05 test barrier ' + BarrierId + ' failed closed.');
  FailureClass := 'test_instrumentation_failure';
  FailureStage := 'vm05_barrier_' + Lowercase(BarrierId);
end;
#endif

#ifdef PASTILA_VM01A_TEST_INSTRUMENTATION
function Vm01aBarrier(const StagePath: String): Boolean;
var
  ProcessId, ArrivedHandle, ContinueHandle, WaitResult: LongWord;
  SessionIdentity, ArrivedName, ContinueName, StageIdentityPath: String;
  CreationTime, ExitTime, KernelTime, UserTime: TVm01aFileTime;
begin
  Result := False;
  ProcessId := GetCurrentProcessId();
  if not Vm01aGetProcessTimes(Vm01aGetCurrentProcess(), CreationTime,
      ExitTime, KernelTime, UserTime) then begin
    Log('Phase 5.6B VM-01A test barrier could not bind process creation time.');
    exit;
  end;
  SessionIdentity := IntToStr(ProcessId) + '_' +
    IntToStr(CreationTime.HighDateTime) + '_' +
    IntToStr(CreationTime.LowDateTime);
  ArrivedName := 'Local\PastilaScout_VM01A_' + SessionIdentity + '_VerifiedStageReady';
  ContinueName := 'Local\PastilaScout_VM01A_' + SessionIdentity + '_Continue';
  StageIdentityPath := ExpandConstant('{tmp}\PastilaScout-VM01A-' +
    SessionIdentity + '-verified-stage.txt');
  if FileExists(StageIdentityPath) then begin
    Log('Phase 5.6B VM-01A test barrier rejected stale stage identity.');
    exit;
  end;
  if not SaveStringToFile(StageIdentityPath, StagePath, False) then begin
    DeleteFile(StageIdentityPath);
    Log('Phase 5.6B VM-01A test barrier could not publish stage identity.');
    exit;
  end;
  ArrivedHandle := Vm01aCreateEvent(0, False, False, ArrivedName);
  if ArrivedHandle = 0 then begin
    DeleteFile(StageIdentityPath);
    Log('Phase 5.6B VM-01A test barrier could not create its ready event.');
    exit;
  end;
  try
    if Vm01aGetLastError() = Vm01aErrorAlreadyExists then begin
      Log('Phase 5.6B VM-01A test barrier rejected a stale ready event.');
      exit;
    end;
    ContinueHandle := Vm01aOpenEvent(Vm01aSynchronizeAccess, False,
      ContinueName);
    if ContinueHandle = 0 then begin
      Log('Phase 5.6B VM-01A test barrier controller is absent.');
      exit;
    end;
    try
      if not Vm01aSetEvent(ArrivedHandle) then begin
        Log('Phase 5.6B VM-01A test barrier could not signal readiness.');
        exit;
      end;
      WaitResult := Vm01aWaitForSingleObject(ContinueHandle,
        Vm01aBarrierTimeoutMs);
      if WaitResult <> 0 then begin
        Log('Phase 5.6B VM-01A test barrier timed out or failed.');
        exit;
      end;
      Result := True;
    finally
      Vm01aCloseHandle(ContinueHandle);
    end;
  finally
    Vm01aCloseHandle(ArrivedHandle);
    if not DeleteFile(StageIdentityPath) then begin
      Log('Phase 5.6B VM-01A test barrier could not remove stage identity.');
      Result := False;
    end;
  end;
end;

procedure RecordVm01aBarrierFailure();
begin
  RecordActivationFailure('VM-01A test barrier failed closed.');
  FailureClass := 'test_instrumentation_failure';
  FailureStage := 'vm01a_barrier';
end;
#endif

#include PayloadVerifyInclude

function IsCanonicalInstallRoot(const Value: String): Boolean;
begin
  Result := CompareText(RemoveBackslashUnlessRoot(ExpandFileName(Value)),
    RemoveBackslashUnlessRoot(ExpandConstant('{localappdata}\Programs\PastilaScout'))) = 0;
end;

function HasReparsePoint(const Path: String): Boolean;
var
  Attr: Longint;
begin
  Attr := GetFileAttributesW(Path);
  Result := (Attr <> -1) and ((Attr and $400) <> 0);
end;

function ParseStableSemVer(const Value: String; var Packed: Int64): Boolean;
var
  Parts: TArrayOfString;
  I, J, Number: Integer;
begin
  Result := False;
  Parts := StringSplit(Value, ['.'], stAll);
  if GetArrayLength(Parts) <> 3 then exit;
  for I := 0 to 2 do begin
    if (Length(Parts[I]) = 0) or ((Length(Parts[I]) > 1) and (Parts[I][1] = '0')) then exit;
    for J := 1 to Length(Parts[I]) do
      if (Parts[I][J] < '0') or (Parts[I][J] > '9') then exit;
    Number := StrToIntDef(Parts[I], -1);
    if (Number < 0) or (Number > 65535) then exit;
  end;
  Packed := PackVersionComponents(StrToInt(Parts[0]), StrToInt(Parts[1]), StrToInt(Parts[2]), 0);
  Result := True;
end;

function HasRequiredDiskSpace: Boolean;
var
  FreeBytes, TotalBytes, RequiredBytes: Int64;
begin
  Result := False;
  if not GetSpaceOnDisk64(ExpandConstant('{localappdata}'), FreeBytes, TotalBytes) then exit;
  RequiredBytes := (Int64({#PayloadBytes}) * 3) + SafetyMarginBytes + InstallerOverheadBytes;
  Log(Format('Phase 5.6B disk preflight: free=%d required=%d', [FreeBytes, RequiredBytes]));
  Result := FreeBytes >= RequiredBytes;
end;

function InstalledPayloadIsUnlocked(const Root: String): Boolean;
begin
  Result := VerifyInstalledPayloadUnlocked(Root);
end;

procedure RegisterRestartManagerResource(const SessionHandle: LongWord;
  const Filename: String);
var
  FilenameBuffer: String;
  FilenamePointer: LongWord;
  ResultCode: LongWord;
begin
  FilenameBuffer := Filename;
  FilenamePointer := CastStringToInteger(FilenameBuffer);
  ResultCode := RmRegisterResources(SessionHandle, 1, FilenamePointer, 0, 0, 0, 0);
  if ResultCode <> ErrorSuccess then
    RaiseException(Format('Restart Manager resource registration failed: %d', [ResultCode]));
end;

function IsRestartManagerProcess(const ProcessId: LongWord): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 0 to GetArrayLength(RestartManagerProcessIds) - 1 do
    if RestartManagerProcessIds[I] = ProcessId then begin
      Result := True;
      exit;
    end;
end;

function RequestOrdinaryClose(Window: HWND; Data: LongWord): Boolean;
var
  ProcessId: LongWord;
begin
  Result := True;
  ProcessId := 0;
  GetWindowThreadProcessId(Window, ProcessId);
  if IsRestartManagerProcess(ProcessId) and IsWindowVisible(Window) and
     (GetWindow(Window, GwOwner) = 0) then begin
    Log(Format('Phase 5.6B ordinary close requested for Restart Manager PID %d.', [ProcessId]));
    PostMessage(Window, WmClose, 0, 0);
  end;
end;

function DiscoverAndRequestOrdinaryClose(): Boolean;
var
  SessionHandle, ResultCode, Needed, Count, RebootReasons: LongWord;
  SessionKey: String;
  ProcessInfo: TRmProcessInfoArray;
  I: Integer;
begin
  Result := False;
  SessionHandle := 0;
  SetLength(SessionKey, 32);
  ResultCode := RmStartSession(SessionHandle, 0, SessionKey);
  if ResultCode <> ErrorSuccess then begin
    Log(Format('Phase 5.6B Restart Manager session failed: %d', [ResultCode]));
    exit;
  end;
  try
    RegisterRestartManagerResources(SessionHandle);
    Needed := 0;
    Count := 1;
    RebootReasons := 0;
    SetArrayLength(ProcessInfo, Count);
    ResultCode := RmGetList(SessionHandle, Needed, Count, ProcessInfo[0], RebootReasons);
    if ResultCode = ErrorMoreData then begin
      Count := Needed;
      SetArrayLength(ProcessInfo, Count);
      ResultCode := RmGetList(SessionHandle, Needed, Count, ProcessInfo[0], RebootReasons);
    end;
    if ResultCode <> ErrorSuccess then begin
      Log(Format('Phase 5.6B Restart Manager discovery failed: %d', [ResultCode]));
      exit;
    end;
    SetArrayLength(RestartManagerProcessIds, Count);
    for I := 0 to Count - 1 do
      RestartManagerProcessIds[I] := ProcessInfo[I].Process.ProcessId;
    if Count > 0 then
      EnumWindows(CreateCallback(@RequestOrdinaryClose), 0);
    Result := True;
  finally
    RmEndSession(SessionHandle);
  end;
end;

function InteractiveCloseReleasedResources(const Root: String): Boolean;
var
  StartTick: Int64;
begin
  Result := False;
  if not DiscoverAndRequestOrdinaryClose then exit;
  StartTick := GetTickCount64();
  repeat
    if InstalledPayloadIsUnlocked(Root) then begin
      Log(Format('Phase 5.6B interactive close completed in %d ms.', [GetTickCount64() - StartTick]));
      Result := True;
      exit;
    end;
    Sleep(100);
  until GetTickCount64() - StartTick >= InteractiveCloseTimeoutMs;
  Log('Phase 5.6B interactive close timed out at the 30000 ms bound.');
end;

function ActivationSucceeded: Boolean;
begin
  Result := ActivationComplete;
end;

procedure RecordActivationFailure(const MessageText: String);
begin
  ActivationComplete := False;
  ActivationFailureMessage := MessageText;
  if StageCleanupStatus = 'failed' then begin
    FailureClass := 'cleanup_failure';
    FailureStage := 'cleanup';
  end else begin
    FailureClass := 'activation_failure';
    FailureStage := 'activation';
  end;
  Log('Phase 5.6B activation failure: ' + MessageText);
end;

function GetCustomSetupExitCode: Integer;
begin
  if FailureStage = 'destination' then Result := 7
  else if ResultWriteFailed then Result := 10
  else if FailureStage = 'cleanup' then Result := 9
  else if PublicationFailed then Result := 4
  else if SetupInitialized and ActivationComplete and not TransactionCommitted then Result := 4
  else if ActivationComplete then Result := 0
  else if SetupInitialized then Result := 9
  else Result := 1;
end;

function GetProjectResultCode: Integer;
begin
  if FailureStage = 'destination' then Result := 7
  else if ResultWriteFailed then Result := 10
  else if FailureStage = 'cleanup' then Result := 9
  else if PublicationFailed and not AggregateCleanupSucceeded then Result := 9
  else if PublicationFailed then Result := 11
  else if TransactionCommitted then Result := 0
  else if SetupInitialized then Result := 9
  else Result := 1;
end;

function DisposeTransactionSnapshot(): Boolean;
begin
  Result := (TransactionSnapshotRoot = '') or
    ((not DirExists(TransactionSnapshotRoot) or
      DelTree(TransactionSnapshotRoot, True, True, True)) and
     not DirExists(TransactionSnapshotRoot));
end;

function InstallerLogRoot(var Root: String): Boolean;
var
  StateRoot, LogsRoot: String;
begin
  Result := False;
  StateRoot := ExpandConstant('{localappdata}\PastilaScout');
  LogsRoot := StateRoot + '\logs';
  Root := LogsRoot + '\installer';
  if HasReparsePoint(StateRoot) or HasReparsePoint(LogsRoot) or
     HasReparsePoint(Root) then begin
    Log('Phase 5.6B final-result root rejected because a governed component is a reparse point.');
    exit;
  end;
  if not ForceDirectories(Root) then begin
    Log('Phase 5.6B final-result root creation failed.');
    exit;
  end;
  Result := not HasReparsePoint(Root);
end;

function PruneInstallerResults(const Root: String): Boolean;
var
  FindRec: TFindRec;
  Files: TStringList;
  Path: String;
begin
  Result := False;
  Files := TStringList.Create;
  try
    Files.Sorted := True;
    if FindFirst(Root + '\result-*.json', FindRec) then begin
      try
        repeat
          if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY = 0) and
             (FindRec.Attributes and FILE_ATTRIBUTE_REPARSE_POINT = 0) then
            Files.Add(FindRec.Name);
        until not FindNext(FindRec);
      finally
        FindClose(FindRec);
      end;
    end;
    while Files.Count >= InstallerResultRetentionCount do begin
      Path := Root + '\' + Files[0];
      if HasReparsePoint(Path) or not DeleteFile(Path) then begin
        Log('Phase 5.6B final-result retention failed safely at: ' + Path);
        exit;
      end;
      Files.Delete(0);
    end;
    Result := True;
  finally
    Files.Free;
  end;
end;

function JsonString(const Value: String): String;
begin
  Result := Value;
  StringChangeEx(Result, '\', '\\', False);
  StringChangeEx(Result, '"', '\"', False);
  StringChangeEx(Result, #8, '\b', False);
  StringChangeEx(Result, #9, '\t', False);
  StringChangeEx(Result, #13, '\r', False);
  StringChangeEx(Result, #10, '\n', False);
  StringChangeEx(Result, #12, '\f', False);
  Result := '"' + Result + '"';
end;

procedure WriteFinalOperationResult();
var
  Root, Path, Status, ActivationStatus, SurfaceStatus: String;
  ExitCode: Integer;
  Body: AnsiString;
begin
  if ResultWritten then exit;
  ResultWritten := True;
  ExitCode := GetProjectResultCode;
  if OperationType = 'uninstall' then begin
    if ActivationComplete then ExitCode := 0 else ExitCode := 1;
  end;
  if ExitCode = 0 then Status := 'success' else Status := 'failure';
  if OperationType = 'uninstall' then begin
    ActivationStatus := 'not_applicable';
    if ActivationComplete then SurfaceStatus := 'removed'
    else SurfaceStatus := 'removal_incomplete';
  end else if PublicationFailed then begin
    ActivationStatus := 'activated';
    SurfaceStatus := 'not_published';
  end else if TransactionCommitted then begin
    ActivationStatus := 'activated';
    SurfaceStatus := 'published';
  end else begin
    ActivationStatus := 'not_activated';
    if ExistingSurfacesAtStart then SurfaceStatus := 'preserved'
    else SurfaceStatus := 'not_published';
  end;
  if not InstallerLogRoot(Root) then begin
    ResultWriteFailed := True;
    exit;
  end;
  if not PruneInstallerResults(Root) then begin
    ResultWriteFailed := True;
    FailureClass := 'logging_retention_failure';
    FailureStage := 'final_result';
    ExitCode := 10;
    Status := 'failure';
  end;
  Path := Root + '\result-' + GetDateTimeString('yyyymmddhhnnsszzz', '-', '-') + '.json';
  if FileExists(Path) or HasReparsePoint(Path) then begin
    ResultWriteFailed := True;
    Log('Phase 5.6B authoritative final-result collision rejected: ' + Path);
    exit;
  end;
  Body := '{' +
    '"operation":' + JsonString(OperationType) + ',' +
    '"final_status":' + JsonString(Status) + ',' +
    '"final_result_code":' + IntToStr(ExitCode) + ',' +
    '"failure_class":' + JsonString(FailureClass) + ',' +
    '"failure_stage":' + JsonString(FailureStage) + ',' +
    '"activation_status":' + JsonString(ActivationStatus) + ',' +
    '"restoration_status":' + JsonString(RestorationStatus) + ',' +
    '"stage_cleanup_status":' + JsonString(StageCleanupStatus) + ',' +
    '"residual_path":' + JsonString(ResidualPath) + ',' +
    '"surface_publication_status":' + JsonString(SurfaceStatus);
  if InitiatingFailurePresent then
    Body := Body + ',"initiating_failure":{"class":"surface_publication_failure",' +
      '"stage":"surface_publication","result_code":11}';
  Body := Body + '}' + #13#10;
  if not SaveStringToFile(Path, Body, False) then begin
    ResultWriteFailed := True;
    Log('Phase 5.6B authoritative final-result write failed: ' + Path);
  end else
    Log('Phase 5.6B authoritative final-result written: ' + Path);
end;

function HasStaleOperationResidue(const Root: String; var ResiduePath: String): Boolean;
var
  FindRec: TFindRec;
begin
  Result := False;
  if FindFirst(Root + '\.stage-*', FindRec) then begin
    try
      repeat
        if FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY <> 0 then begin
          ResiduePath := Root + '\' + FindRec.Name;
          Result := True;
          exit;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
  if FindFirst(Root + '\.old-*', FindRec) then begin
    try
      repeat
        if FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY <> 0 then begin
          ResiduePath := Root + '\' + FindRec.Name;
          Result := True;
          exit;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

function ValidExistingInstallerSurfaces(): Boolean;
var
  Key, Root, Value, Version: String;
  PackedVersion: Int64;
begin
  Result := False;
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\PastilaScout_is1';
  Root := ExpandConstant('{localappdata}\Programs\PastilaScout');
  if not DirExists(Root + '\app') or
     not FileExists(Root + '\app\PastilaScout.exe') or
     not FileExists(Root + '\app\pastila-scout.exe') or
     not FileExists(Root + '\unins000.exe') then exit;
  if not RegQueryStringValue(HKCU64, Key, 'DisplayName', Value) or
     (Value <> 'Pastila Scout') then exit;
  if not RegQueryStringValue(HKCU64, Key, 'DisplayVersion', Version) or
     not ParseStableSemVer(Version, PackedVersion) then exit;
  if not RegQueryStringValue(HKCU64, Key, 'InstallLocation', Value) or
     (CompareText(RemoveBackslashUnlessRoot(Value), Root) <> 0) then exit;
  if not RegQueryStringValue(HKCU64, Key, 'DisplayIcon', Value) or
     (CompareText(Value, Root + '\app\PastilaScout.exe') <> 0) then exit;
  if not RegQueryStringValue(HKCU64, Key, 'UninstallString', Value) or
     (CompareText(Value, '"' + Root + '\unins000.exe"') <> 0) then exit;
  Result := True;
end;

function InitializeSetup(): Boolean;
var
  ExistingVersion, StalePath: String;
  ExistingPacked, CandidatePacked: Int64;
begin
  Result := False;
  SetupInitialized := False;
  ResultWritten := False;
  ResultWriteFailed := False;
  ActivationComplete := False;
  ActivationFailureMessage := '';
  FailureClass := 'preflight_failure';
  FailureStage := 'initialize';
  RestorationStatus := 'not_required';
  StageCleanupStatus := 'not_created';
  ResidualPath := '';
  if DirExists(ExpandConstant('{localappdata}\Programs\PastilaScout\app')) then
    OperationType := 'repair'
  else OperationType := 'install';
  ExistingSurfacesAtStart := ValidExistingInstallerSurfaces();
  Log('Phase 5.6B preflight: architecture');
  if not IsWin64 then begin
    SuppressibleMsgBox('Pastila Scout requires native 64-bit Windows.', mbCriticalError, MB_OK, IDOK);
    exit;
  end;
  Log('Phase 5.6B preflight: canonical root');
  if not IsCanonicalInstallRoot(ExpandConstant('{localappdata}\Programs\PastilaScout')) then begin
    SuppressibleMsgBox('The canonical per-user installation root is unavailable.', mbCriticalError, MB_OK, IDOK);
    exit;
  end;
  Log('Phase 5.6B preflight: reparse ancestors');
  if HasReparsePoint(ExpandConstant('{localappdata}\Programs')) or
     HasReparsePoint(ExpandConstant('{localappdata}\Programs\PastilaScout')) then begin
    SuppressibleMsgBox('Installation refused because the destination contains a reparse point.', mbCriticalError, MB_OK, IDOK);
    exit;
  end;
  StalePath := '';
  if HasStaleOperationResidue(ExpandConstant('{localappdata}\Programs\PastilaScout'),
      StalePath) then begin
    FailureClass := 'stale_residue';
    FailureStage := 'preflight';
    ResidualPath := StalePath;
    SuppressibleMsgBox('Installation refused because stale installer residue requires safe cleanup: ' +
      StalePath, mbCriticalError, MB_OK, IDOK);
    exit;
  end;
  if not HasRequiredDiskSpace then begin
    FailureClass := 'insufficient_space';
    FailureStage := 'preflight';
    SuppressibleMsgBox('Insufficient disk space for verified staging, bounded rollback, overhead, and the 64 MiB safety margin.', mbCriticalError, MB_OK, IDOK);
    exit;
  end;
  Log('Phase 5.6B preflight: registered version');
  if not ParseStableSemVer('{#AppVersion}', CandidatePacked) then begin
    SuppressibleMsgBox('The installer version is not a valid stable semantic version.', mbCriticalError, MB_OK, IDOK);
    exit;
  end;
  if DirExists(ExpandConstant('{localappdata}\Programs\PastilaScout\app')) and
     not InstalledPayloadIsUnlocked(ExpandConstant('{localappdata}\Programs\PastilaScout\app')) then begin
    if WizardSilent then begin
      FailureClass := 'running_application';
      FailureStage := 'process_gate';
      SuppressibleMsgBox('Pastila Scout is running. Silent installation cannot continue.', mbCriticalError, MB_OK, IDOK);
      exit;
    end;
    Log('Phase 5.6B interactive preflight: canonical resources are locked; bounded ordinary close required.');
    if not InteractiveCloseReleasedResources(
        ExpandConstant('{localappdata}\Programs\PastilaScout\app')) then begin
      FailureClass := 'running_application';
      FailureStage := 'interactive_close_timeout';
      SuppressibleMsgBox('Pastila Scout did not close within 30 seconds. Installation has not changed the application.', mbCriticalError, MB_OK, IDOK);
      exit;
    end;
  end;
  if RegQueryStringValue(HKCU64,
      'Software\Microsoft\Windows\CurrentVersion\Uninstall\PastilaScout_is1',
      'DisplayVersion', ExistingVersion) then begin
    if not ParseStableSemVer(ExistingVersion, ExistingPacked) then begin
      SuppressibleMsgBox('The registered Pastila Scout version is malformed; installation cannot continue safely.', mbCriticalError, MB_OK, IDOK);
      exit;
    end;
    if ComparePackedVersion(ExistingPacked, CandidatePacked) > 0 then begin
      FailureClass := 'downgrade_rejected';
      FailureStage := 'version_policy';
      SuppressibleMsgBox('A newer Pastila Scout version is already installed; downgrade is not permitted.', mbCriticalError, MB_OK, IDOK);
      exit;
    end;
  end;
  StageName := '.stage-' + GetDateTimeString('yyyymmddhhnnsszzz', '-', '-');
  OldName := '.old-' + GetDateTimeString('yyyymmddhhnnsszzz', '-', '-');
  SetupInitialized := True;
  FailureClass := '';
  FailureStage := '';
  TransactionSnapshotTaken := False;
  TransactionResolved := False;
  TransactionCommitted := False;
  PublicationFailed := False;
  AggregateCleanupSucceeded := False;
  InitiatingFailurePresent := False;
  Result := True;
end;

function CaptureTransactionSnapshot(): Boolean; forward;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if not IsCanonicalInstallRoot(ExpandConstant('{app}')) then begin
    FailureClass := 'preflight_failure';
    FailureStage := 'destination';
    WriteFinalOperationResult();
    if (FailureClass = 'logging_retention_failure') and
       (FailureStage = 'final_result') then
      ExitProcess(10)
    else if ResultWriteFailed then
      ExitProcess(1);
    Result := 'The canonical per-user installation root is unavailable.';
  end else if not CaptureTransactionSnapshot then begin
    if PublicationFailed then begin
      WriteFinalOperationResult();
      ExitProcess(GetCustomSetupExitCode);
    end;
    FailureClass := 'preflight_failure';
    FailureStage := 'transaction_snapshot';
    WriteFinalOperationResult();
    Result := 'Unable to capture the transactional installation baseline.';
  end;
end;

function SnapshotFile(const Source, Name: String; var Existed: Boolean): Boolean;
begin
  Existed := FileExists(Source);
  Result := not Existed or FileCopy(Source, TransactionSnapshotRoot + '\' + Name, False);
end;

function PowerShellSingleQuoted(const Value: String): String;
begin
  Result := Value;
  StringChangeEx(Result, '''', '''''', True);
  Result := '''' + Result + '''';
end;

function WritePayloadInventory(const AppPath, OutputPath, ScriptName: String): Boolean;
var
  ScriptPath, Script: String;
  ExitCode: Integer;
begin
  ScriptPath := TransactionSnapshotRoot + '\' + ScriptName;
  Script := '$ErrorActionPreference=''Stop'';' +
    '$root=' + PowerShellSingleQuoted(AppPath) + ';' +
    '$out=' + PowerShellSingleQuoted(OutputPath) + ';' +
    '$rows=Get-ChildItem -LiteralPath $root -File -Recurse | Sort-Object FullName | ForEach-Object {' +
    '$rel=$_.FullName.Substring($root.Length).TrimStart(''\'');' +
    '''{0}|{1}|{2}'' -f $rel,$_.Length,(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash};' +
    '[IO.File]::WriteAllLines($out,$rows,[Text.UTF8Encoding]::new($false))';
  Result := SaveStringToFile(ScriptPath, Script, False) and
    Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
      '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + ScriptPath + '"',
      '', SW_HIDE, ewWaitUntilTerminated, ExitCode) and (ExitCode = 0) and FileExists(OutputPath);
end;

function ExportRegistryData(const OutputPath: String): Boolean;
var
  ExitCode: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\reg.exe'),
    'export "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\PastilaScout_is1" "' +
      OutputPath + '" /y /reg:64',
    '', SW_HIDE, ewWaitUntilTerminated, ExitCode) and (ExitCode = 0) and
    FileExists(OutputPath);
end;

function SnapshotRegistryData(): Boolean;
begin
  Result := ExportRegistryData(TransactionSnapshotRoot + '\arp.reg');
end;

function RestoreRegistryData(): Boolean;
var
  ExitCode: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\reg.exe'),
    'import "' + TransactionSnapshotRoot + '\arp.reg" /reg:64',
    '', SW_HIDE, ewWaitUntilTerminated, ExitCode) and (ExitCode = 0);
end;

function VerifyRegistryDataSnapshot(): Boolean;
var
  RestoredPath: String;
begin
  RestoredPath := TransactionSnapshotRoot + '\arp-restored.reg';
  Result := ExportRegistryData(RestoredPath) and
    (CompareText(GetSHA256OfFile(TransactionSnapshotRoot + '\arp.reg'),
      GetSHA256OfFile(RestoredPath)) = 0);
end;

function ShortcutMatches(const Path, Target, Arguments, WorkingDirectory: String): Boolean;
var
  Shell, Shortcut: Variant;
begin
  Result := False;
  if not FileExists(Path) then exit;
  try
    Shell := CreateOleObject('WScript.Shell');
    Shortcut := Shell.CreateShortcut(Path);
    Result := (CompareText(Shortcut.TargetPath, Target) = 0) and
      (Shortcut.Arguments = Arguments) and
      (CompareText(RemoveBackslashUnlessRoot(Shortcut.WorkingDirectory),
        RemoveBackslashUnlessRoot(WorkingDirectory)) = 0);
  except
    Result := False;
  end;
end;

function CaptureTransactionSnapshot(): Boolean;
var
  Root, AppPath, Key, ShortcutPath, PublicationProbe: String;
begin
  Result := False;
  Root := ExpandConstant('{app}');
  AppPath := Root + '\app';
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\PastilaScout_is1';
  ShortcutPath := ExpandConstant('{userprograms}\Pastila Scout.lnk');
  TransactionSnapshotRoot := ExpandConstant('{tmp}\PastilaScout-' + StageName + '-surface-snapshot');
  if DirExists(TransactionSnapshotRoot) or not ForceDirectories(TransactionSnapshotRoot) then exit;
  PriorPayloadExisted := DirExists(AppPath);
  if PriorPayloadExisted then begin
    if not FileExists(AppPath + '\PastilaScout.exe') or
       not FileExists(AppPath + '\pastila-scout.exe') then exit;
    PriorPayloadGuiSha256 := GetSHA256OfFile(AppPath + '\PastilaScout.exe');
    PriorPayloadCliSha256 := GetSHA256OfFile(AppPath + '\pastila-scout.exe');
    if not WritePayloadInventory(AppPath, TransactionSnapshotRoot + '\payload.inventory',
      'capture-payload-inventory.ps1') then exit;
  end;
  PriorArpExisted := RegKeyExists(HKCU64, Key);
  if (not PriorPayloadExisted) and PriorArpExisted then begin
    PublicationProbe := 'Phase56BPublicationWriteProbe';
    if RegValueExists(HKCU64, Key, PublicationProbe) or
       not RegWriteStringValue(HKCU64, Key, PublicationProbe, 'probe') or
       not RegDeleteValue(HKCU64, Key, PublicationProbe) then begin
      PublicationFailed := True;
      FailureClass := 'surface_publication_failure';
      FailureStage := 'surface_publication';
      exit;
    end;
  end;
  if PriorPayloadExisted then begin
    if not PriorArpExisted or
       not RegQueryStringValue(HKCU64, Key, 'DisplayName', PriorArpDisplayName) or
       not RegQueryStringValue(HKCU64, Key, 'DisplayVersion', PriorArpDisplayVersion) or
       not RegQueryStringValue(HKCU64, Key, 'InstallLocation', PriorArpInstallLocation) or
       not RegQueryStringValue(HKCU64, Key, 'DisplayIcon', PriorArpDisplayIcon) or
       not RegQueryStringValue(HKCU64, Key, 'UninstallString', PriorArpUninstallString) or
       not SnapshotRegistryData then exit;
  end;
  if not SnapshotFile(Root + '\unins000.exe', 'unins000.exe', PriorUninstallerExeExisted) or
     not SnapshotFile(Root + '\unins000.dat', 'unins000.dat', PriorUninstallerDatExisted) or
     not SnapshotFile(ShortcutPath, 'Pastila Scout.lnk', PriorShortcutExisted) then exit;
  if PriorPayloadExisted and
     (not PriorUninstallerExeExisted or not PriorUninstallerDatExisted or
      not PriorShortcutExisted or
      not ShortcutMatches(ShortcutPath, AppPath + '\PastilaScout.exe', '', Root)) then exit;
  TransactionSnapshotTaken := True;
  Result := True;
end;

function VerifyMandatoryPublicationSurfaces(): Boolean;
var
  Root, Key, Value: String;
begin
  Root := ExpandConstant('{app}');
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\PastilaScout_is1';
  Result := ActivationComplete and DirExists(Root + '\app') and
    FileExists(Root + '\app\PastilaScout.exe') and
    FileExists(Root + '\app\pastila-scout.exe') and
    RegQueryStringValue(HKCU64, Key, 'DisplayName', Value) and (Value = 'Pastila Scout') and
    RegQueryStringValue(HKCU64, Key, 'DisplayVersion', Value) and (Value = '{#AppVersion}') and
    RegQueryStringValue(HKCU64, Key, 'InstallLocation', Value) and
      (CompareText(RemoveBackslashUnlessRoot(Value), Root) = 0) and
    RegQueryStringValue(HKCU64, Key, 'DisplayIcon', Value) and
      (CompareText(Value, Root + '\app\PastilaScout.exe') = 0) and
    RegQueryStringValue(HKCU64, Key, 'UninstallString', Value) and
      (CompareText(Value, '"' + Root + '\unins000.exe"') = 0) and
    FileExists(Root + '\unins000.exe') and FileExists(Root + '\unins000.dat') and
    ShortcutMatches(ExpandConstant('{userprograms}\Pastila Scout.lnk'),
      Root + '\app\PastilaScout.exe', '', Root);
#ifdef PASTILA_INSTALLER_REPAIR_CAR_FORCE_PUBLICATION_FAILURE
  Result := False;
#endif
end;

function RemoveFileAndVerify(const Path: String): Boolean;
begin
  Result := (not FileExists(Path) or DeleteFile(Path)) and not FileExists(Path);
end;

function RemoveKeyAndVerify(const Key: String): Boolean;
begin
  Result := (not RegKeyExists(HKCU64, Key) or
    RegDeleteKeyIncludingSubkeys(HKCU64, Key)) and not RegKeyExists(HKCU64, Key);
end;

function RestoreFileAndVerify(const Snapshot, Destination: String; Existed: Boolean): Boolean;
begin
  if Existed then
    Result := FileCopy(Snapshot, Destination, False) and FileExists(Destination) and
      (CompareText(GetSHA256OfFile(Snapshot), GetSHA256OfFile(Destination)) = 0)
  else
    Result := RemoveFileAndVerify(Destination);
end;

function RestorePriorState(): Boolean;
var
  Root, AppPath, OldPath, Key, ShortcutPath, Value, RestoredInventory: String;
begin
  Root := ExpandConstant('{app}'); AppPath := Root + '\app'; OldPath := Root + '\' + OldName;
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\PastilaScout_is1';
  ShortcutPath := ExpandConstant('{userprograms}\Pastila Scout.lnk');
  Result := RemoveKeyAndVerify(Key) and
    RemoveFileAndVerify(Root + '\unins000.exe') and
    RemoveFileAndVerify(Root + '\unins000.dat') and
    RemoveFileAndVerify(ShortcutPath) and
    (not DirExists(AppPath) or DelTree(AppPath, True, True, True));
  if not Result then exit;
  if PriorPayloadExisted then begin
    Result := RenameFile(OldPath, AppPath) and
      (CompareText(GetSHA256OfFile(AppPath + '\PastilaScout.exe'), PriorPayloadGuiSha256) = 0) and
      (CompareText(GetSHA256OfFile(AppPath + '\pastila-scout.exe'), PriorPayloadCliSha256) = 0) and
      RestoreFileAndVerify(TransactionSnapshotRoot + '\unins000.exe', Root + '\unins000.exe', PriorUninstallerExeExisted) and
      RestoreFileAndVerify(TransactionSnapshotRoot + '\unins000.dat', Root + '\unins000.dat', PriorUninstallerDatExisted) and
      RestoreFileAndVerify(TransactionSnapshotRoot + '\Pastila Scout.lnk', ShortcutPath, PriorShortcutExisted);
    if not Result then exit;
    RestoredInventory := TransactionSnapshotRoot + '\payload-restored.inventory';
    Result := WritePayloadInventory(AppPath, RestoredInventory,
      'verify-payload-inventory.ps1') and
      (CompareText(GetSHA256OfFile(TransactionSnapshotRoot + '\payload.inventory'),
        GetSHA256OfFile(RestoredInventory)) = 0);
    if not Result then exit;
#ifdef PASTILA_INSTALLER_REPAIR_CAR_FORCE_ROLLBACK_FAILURE
    DeleteFile(TransactionSnapshotRoot + '\arp.reg');
#endif
    Result := RestoreRegistryData and
      RegQueryStringValue(HKCU64, Key, 'DisplayName', Value) and (Value = PriorArpDisplayName) and
      RegQueryStringValue(HKCU64, Key, 'DisplayVersion', Value) and (Value = PriorArpDisplayVersion) and
      RegQueryStringValue(HKCU64, Key, 'InstallLocation', Value) and (Value = PriorArpInstallLocation) and
      RegQueryStringValue(HKCU64, Key, 'DisplayIcon', Value) and (Value = PriorArpDisplayIcon) and
      RegQueryStringValue(HKCU64, Key, 'UninstallString', Value) and (Value = PriorArpUninstallString) and
      VerifyRegistryDataSnapshot and
      RegQueryStringValue(HKCU64, Key, 'DisplayName', Value) and (Value = PriorArpDisplayName) and
      RegQueryStringValue(HKCU64, Key, 'DisplayVersion', Value) and (Value = PriorArpDisplayVersion) and
      RegQueryStringValue(HKCU64, Key, 'InstallLocation', Value) and (Value = PriorArpInstallLocation) and
      RegQueryStringValue(HKCU64, Key, 'DisplayIcon', Value) and (Value = PriorArpDisplayIcon) and
      RegQueryStringValue(HKCU64, Key, 'UninstallString', Value) and (Value = PriorArpUninstallString) and
      ShortcutMatches(ShortcutPath, AppPath + '\PastilaScout.exe', '', Root);
  end else begin
    Result := not DirExists(AppPath) and not RegKeyExists(HKCU64, Key) and
      not FileExists(Root + '\unins000.exe') and not FileExists(Root + '\unins000.dat') and
      not FileExists(ShortcutPath);
    if DirExists(OldPath) then Result := False;
    if Result then
      Result := (not DirExists(Root) or RemoveDir(Root)) and not DirExists(Root);
  end;
end;

function RestorePriorPublicationSurfaces(): Boolean;
var
  Root, Key, ShortcutPath: String;
begin
  Root := ExpandConstant('{app}');
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\PastilaScout_is1';
  ShortcutPath := ExpandConstant('{userprograms}\Pastila Scout.lnk');
  Result := RemoveKeyAndVerify(Key) and
    RemoveFileAndVerify(Root + '\unins000.exe') and
    RemoveFileAndVerify(Root + '\unins000.dat') and
    RemoveFileAndVerify(ShortcutPath) and
    RestoreFileAndVerify(TransactionSnapshotRoot + '\unins000.exe',
      Root + '\unins000.exe', PriorUninstallerExeExisted) and
    RestoreFileAndVerify(TransactionSnapshotRoot + '\unins000.dat',
      Root + '\unins000.dat', PriorUninstallerDatExisted) and
    RestoreFileAndVerify(TransactionSnapshotRoot + '\Pastila Scout.lnk',
      ShortcutPath, PriorShortcutExisted) and RestoreRegistryData and
    VerifyRegistryDataSnapshot and
    ShortcutMatches(ShortcutPath, Root + '\app\PastilaScout.exe', '', Root);
end;

function BooleanText(const Value: Boolean): String;
begin
  if Value then Result := 'true' else Result := 'false';
end;

function SealRestorationEvidence(): Boolean;
var
  Root, Path, Key, ShortcutPath, PayloadPriorHash, PayloadRestoredHash,
    ExePriorHash, ExeRestoredHash, DatPriorHash, DatRestoredHash,
  ShortcutPriorHash, ShortcutRestoredHash, ArpDataHash, Topology: String;
  Body: AnsiString;
begin
  Result := False;
  if not InstallerLogRoot(Root) then exit;
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\PastilaScout_is1';
  ShortcutPath := ExpandConstant('{userprograms}\Pastila Scout.lnk');
  if PriorPayloadExisted then begin
    Topology := 'upgrade';
    if not FileExists(TransactionSnapshotRoot + '\payload.inventory') or
       not FileExists(TransactionSnapshotRoot + '\payload-restored.inventory') or
       not FileExists(TransactionSnapshotRoot + '\arp.reg') then exit;
    PayloadPriorHash := GetSHA256OfFile(TransactionSnapshotRoot + '\payload.inventory');
    PayloadRestoredHash := GetSHA256OfFile(TransactionSnapshotRoot + '\payload-restored.inventory');
    ArpDataHash := GetSHA256OfFile(TransactionSnapshotRoot + '\arp.reg');
    if PriorUninstallerExeExisted then begin
      ExePriorHash := GetSHA256OfFile(TransactionSnapshotRoot + '\unins000.exe');
      ExeRestoredHash := GetSHA256OfFile(ExpandConstant('{app}\unins000.exe'));
    end;
    if PriorUninstallerDatExisted then begin
      DatPriorHash := GetSHA256OfFile(TransactionSnapshotRoot + '\unins000.dat');
      DatRestoredHash := GetSHA256OfFile(ExpandConstant('{app}\unins000.dat'));
    end;
    if PriorShortcutExisted then begin
      ShortcutPriorHash := GetSHA256OfFile(TransactionSnapshotRoot + '\Pastila Scout.lnk');
      ShortcutRestoredHash := GetSHA256OfFile(ShortcutPath);
    end;
  end else begin
    Topology := 'clean_install';
    if DirExists(ExpandConstant('{app}\app')) or RegKeyExists(HKCU64, Key) or
       FileExists(ExpandConstant('{app}\unins000.exe')) or
       FileExists(ExpandConstant('{app}\unins000.dat')) or FileExists(ShortcutPath) then exit;
  end;
  Path := Root + '\transaction-restoration-' +
    GetDateTimeString('yyyymmddhhnnsszzz', '-', '-') + '.json';
  if FileExists(Path) or HasReparsePoint(Path) then exit;
  Body := '{"schema":"pastila-scout-transaction-restoration-v1",' +
    '"topology":' + JsonString(Topology) + ',' +
    '"payload":{"prior_inventory_sha256":' + JsonString(PayloadPriorHash) +
      ',"restored_inventory_sha256":' + JsonString(PayloadRestoredHash) +
      ',"verified":true},' +
    '"arp":{"prior_present":' + BooleanText(PriorArpExisted) +
      ',"complete_registry_data_sha256":' + JsonString(ArpDataHash) +
      ',"values_types_subkeys_verified":true,' +
      '"security_policy":"inherited_hkcu_product_key_not_mutated"},' +
    '"unins000_exe":{"prior_present":' + BooleanText(PriorUninstallerExeExisted) +
      ',"prior_sha256":' + JsonString(ExePriorHash) + ',"restored_sha256":' +
      JsonString(ExeRestoredHash) + ',"verified":true},' +
    '"unins000_dat":{"prior_present":' + BooleanText(PriorUninstallerDatExisted) +
      ',"prior_sha256":' + JsonString(DatPriorHash) + ',"restored_sha256":' +
      JsonString(DatRestoredHash) + ',"verified":true},' +
    '"start_menu":{"prior_present":' + BooleanText(PriorShortcutExisted) +
      ',"prior_sha256":' + JsonString(ShortcutPriorHash) + ',"restored_sha256":' +
      JsonString(ShortcutRestoredHash) + ',"properties_verified":true},' +
    '"required_absence_verified":' + BooleanText(not PriorPayloadExisted) + ',' +
    '"aggregate_verified":true,' +
    '"restoration_status":' + JsonString(RestorationStatus) + ',' +
    '"unins000_msg":"absent_not_applicable"}';
  Result := SaveStringToFile(Path, String(Body), False) and FileExists(Path) and
    not HasReparsePoint(Path) and (GetSHA256OfFile(Path) <> '');
end;

procedure ResolveTransaction();
var
  OldPath: String;
begin
  if TransactionResolved or not SetupInitialized or not ActivationComplete or
     not TransactionSnapshotTaken then exit;
  TransactionResolved := True;
  OldPath := ExpandConstant('{app}\' + OldName);
  if VerifyMandatoryPublicationSurfaces then begin
    TransactionCommitted := True;
    if DirExists(OldPath) and not DelTree(OldPath, True, True, True) then begin
      FailureClass := 'cleanup_failure'; FailureStage := 'cleanup';
      StageCleanupStatus := 'failed'; ResidualPath := OldPath;
    end else if not DisposeTransactionSnapshot then begin
      FailureClass := 'cleanup_failure'; FailureStage := 'cleanup';
      StageCleanupStatus := 'failed'; ResidualPath := TransactionSnapshotRoot;
    end;
  end else begin
    PublicationFailed := True;
    FailureClass := 'surface_publication_failure'; FailureStage := 'surface_publication';
    AggregateCleanupSucceeded := RestorePriorState;
    if AggregateCleanupSucceeded then begin
      if PriorPayloadExisted then RestorationStatus := 'restored'
      else RestorationStatus := 'not_required';
      AggregateCleanupSucceeded := SealRestorationEvidence;
      if AggregateCleanupSucceeded then
        AggregateCleanupSucceeded := DisposeTransactionSnapshot;
      if AggregateCleanupSucceeded then
        StageCleanupStatus := 'removed'
      else begin
        InitiatingFailurePresent := True;
        FailureClass := 'cleanup_failure'; FailureStage := 'cleanup';
        StageCleanupStatus := 'failed'; ResidualPath := TransactionSnapshotRoot;
      end;
    end else begin
      InitiatingFailurePresent := True;
      FailureClass := 'cleanup_failure'; FailureStage := 'cleanup';
      RestorationStatus := 'failed'; StageCleanupStatus := 'failed';
      ResidualPath := ExpandConstant('{app}');
    end;
  end;
end;

procedure ActivateStagedPayload();
var
  Root, StagePath, AppPath, OldPath: String;
  HadOld: Boolean;
#ifdef PASTILA_VM05_TEST_INSTRUMENTATION
  Vm05BarrierCFailed: Boolean;
#endif
begin
  Root := ExpandConstant('{app}');
  StagePath := Root + '\' + StageName;
  AppPath := Root + '\' + AppDirectoryName;
  OldPath := Root + '\' + OldName;
#ifdef PASTILA_VM05_TEST_INSTRUMENTATION
  Vm05BarrierCFailed := False;
#endif
  if not VerifyStagedPayload(StagePath) then begin
    if DelTree(StagePath, True, True, True) then StageCleanupStatus := 'removed'
    else begin StageCleanupStatus := 'failed'; ResidualPath := StagePath; end;
    RecordActivationFailure('Staged payload verification failed before activation.');
    exit;
  end;
#ifdef PASTILA_VM01A_TEST_INSTRUMENTATION
  if not Vm01aBarrier(StagePath) then begin
    if DelTree(StagePath, True, True, True) then StageCleanupStatus := 'removed'
    else begin StageCleanupStatus := 'failed'; ResidualPath := StagePath; end;
    RecordVm01aBarrierFailure();
    exit;
  end;
#endif
  HadOld := DirExists(AppPath);
  if HadOld and not RenameFile(AppPath, OldPath) then begin
    if DelTree(StagePath, True, True, True) then StageCleanupStatus := 'removed'
    else begin StageCleanupStatus := 'failed'; ResidualPath := StagePath; end;
    RecordActivationFailure('Unable to preserve the previous application payload.');
    exit;
  end;
#ifdef PASTILA_VM05_TEST_INSTRUMENTATION
  if HadOld and not Vm05Barrier('A') then begin
    if RenameFile(OldPath, AppPath) then RestorationStatus := 'restored'
    else RestorationStatus := 'failed';
    if DelTree(StagePath, True, True, True) then StageCleanupStatus := 'removed'
    else begin StageCleanupStatus := 'failed'; ResidualPath := StagePath; end;
    RecordVm05BarrierFailure('A');
    exit;
  end;
  if HadOld and not Vm05Barrier('B') then begin
    if RenameFile(OldPath, AppPath) then RestorationStatus := 'restored'
    else RestorationStatus := 'failed';
    if DelTree(StagePath, True, True, True) then StageCleanupStatus := 'removed'
    else begin StageCleanupStatus := 'failed'; ResidualPath := StagePath; end;
    RecordVm05BarrierFailure('B');
    exit;
  end;
#endif
  if not RenameFile(StagePath, AppPath) then begin
    if HadOld then begin
#ifdef PASTILA_VM05_TEST_INSTRUMENTATION
      if not Vm05Barrier('C') then begin
        Vm05BarrierCFailed := True;
        RestorationStatus := 'failed';
      end
      else
#endif
      if RenameFile(OldPath, AppPath) then RestorationStatus := 'restored'
      else RestorationStatus := 'failed';
    end;
    if DelTree(StagePath, True, True, True) then StageCleanupStatus := 'removed'
    else begin StageCleanupStatus := 'failed'; ResidualPath := StagePath; end;
#ifdef PASTILA_VM05_TEST_INSTRUMENTATION
    if Vm05BarrierCFailed then RecordVm05BarrierFailure('C')
    else
#endif
      RecordActivationFailure('Unable to activate the verified application payload.');
    exit;
  end;
  ActivationComplete := True;
  StageCleanupStatus := 'removed';
  Log('Phase 5.6B activation completed before surface publication.');
end;

procedure RemoveFailedActivationSurfaces();
begin
  RegDeleteKeyIncludingSubkeys(HKCU64,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\PastilaScout_is1');
  DeleteFile(ExpandConstant('{app}\unins000.exe'));
  DeleteFile(ExpandConstant('{app}\unins000.dat'));
  DeleteFile(ExpandConstant('{userprograms}\Pastila Scout.lnk'));
  DeleteFile(ExpandConstant('{userdesktop}\Pastila Scout.lnk'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and not ActivationComplete then begin
    if ExistingSurfacesAtStart then
      Log('Phase 5.6B preserving pre-existing installer surfaces after failed repair.')
    else begin
      Log('Phase 5.6B removing newly created installer surfaces after failed installation.');
      RemoveFailedActivationSurfaces();
    end;
  end else if CurStep = ssPostInstall then begin
    ResolveTransaction();
    WriteFinalOperationResult();
  end;
end;

procedure DeinitializeSetup();
begin
  if SetupInitialized and TransactionSnapshotTaken and not ActivationComplete and
     PriorPayloadExisted then begin
    AggregateCleanupSucceeded := RestorePriorPublicationSurfaces;
    if AggregateCleanupSucceeded then begin
      RestorationStatus := 'restored';
      AggregateCleanupSucceeded := DisposeTransactionSnapshot;
    end;
    if not AggregateCleanupSucceeded then begin
      FailureClass := 'cleanup_failure';
      FailureStage := 'cleanup';
      RestorationStatus := 'failed';
      StageCleanupStatus := 'failed';
      ResidualPath := TransactionSnapshotRoot;
    end;
  end else
    ResolveTransaction();
  WriteFinalOperationResult();
end;

function InitializeUninstall(): Boolean;
begin
  OperationType := 'uninstall';
  SetupInitialized := True;
  ResultWritten := False;
  ResultWriteFailed := False;
  ActivationComplete := False;
  FailureClass := 'uninstall_failure';
  FailureStage := 'uninstall';
  RestorationStatus := 'not_applicable';
  StageCleanupStatus := 'not_required';
  Result := IsCanonicalInstallRoot(ExpandConstant('{app}')) and
    not HasReparsePoint(ExpandConstant('{app}'));
  if not Result then
    MsgBox('Uninstall refused: canonical ownership or reparse validation failed.', mbCriticalError, MB_OK);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then begin
    if not DelTree(ExpandConstant('{app}\app'), True, True, True) then
      RaiseException('Application payload removal failed.');
  end else if CurUninstallStep = usPostUninstall then begin
    ActivationComplete := True;
    FailureClass := '';
    FailureStage := '';
  end;
end;

procedure DeinitializeUninstall();
begin
  WriteFinalOperationResult();
end;
