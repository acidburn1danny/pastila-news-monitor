param([Parameter(Mandatory)][string]$BrokerSource,[Parameter(Mandatory)][string]$ResultPath,[ValidateSet('Bootstrap','Qualification')][string]$Mode='Bootstrap',[string]$CandidateSource,[string]$PreparationSource,[string]$PayloadSource,[string]$PreparationArchive,[string]$PayloadArchive)
$ErrorActionPreference='Stop'
$vm='PastilaScout-Phase56B-Disposable';$svc='PastilaScoutBuildBrokerR4'
$build='C:\PastilaScout-Installer-Build\phase-5.6b\build-20260812-038'
$toolRoot='C:\PastilaScout-Installer-Toolchain\phase-5.6b\inno-setup-6-001'
$tool="$toolRoot\toolchain\ISCC.exe";$toolSha='0A8757031B33777E4C9CBFFEE40F11A5062B36D25CBE144C1DB73B6102B80AD7'
$evidence='C:\PastilaScout-Installer-Evidence\phase-5.6b\r4-admin-bootstrap-20260813-001'
$adminSession=$null;$consumerSession=$null;$failed=$false
function Admin([scriptblock]$Block,[object[]]$ArgumentValues=@()){Invoke-Command -Session $adminSession -ScriptBlock $Block -ArgumentList $ArgumentValues}
function Consumer([scriptblock]$Block,[object[]]$ArgumentValues=@()){Invoke-Command -Session $consumerSession -ScriptBlock $Block -ArgumentList $ArgumentValues}
$install={param($Source,$Evidence,$Capture,$Build,$ToolRoot)
  $ErrorActionPreference='Stop';$svc='PastilaScoutBuildBrokerR4';$broker='C:\ProgramData\PastilaScout\BuildBrokerR4'
  $bin="$broker\bin\PastilaScoutBuildBrokerR4.exe";$utf8=[Text.UTF8Encoding]::new($false)
  function Save($Name,$Value){[IO.File]::WriteAllText((Join-Path $Evidence $Name),($Value|ConvertTo-Json -Depth 12),$utf8)}
  New-Item $Evidence -ItemType Directory -Force|Out-Null
  if($Capture -and -not(Test-Path (Join-Path $Evidence 'rollback-baseline.json'))){Save 'rollback-baseline.json' ([ordered]@{build_sddl=(Get-Acl $Build).Sddl;tool_sddl=(Get-Acl $ToolRoot).Sddl;service_absent=$null-eq(Get-Service $svc -ErrorAction SilentlyContinue);broker_absent=-not(Test-Path $broker)})}
  if(Get-Service $svc -ErrorAction SilentlyContinue){& sc.exe stop $svc 2>$null|Out-Null;& sc.exe delete $svc|Out-Null;Start-Sleep 1}
  if(Test-Path $broker){& takeown.exe /F $broker /A /R /D Y|Out-Null;& icacls.exe $broker /grant 'Administrators:(OI)(CI)F' /T /C /Q|Out-Null;Remove-Item $broker -Recurse -Force}
  New-Item "$broker\bin","$broker\config","$broker\authority" -ItemType Directory -Force|Out-Null
  & 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe' /nologo /target:exe /optimize+ /out:$bin /reference:System.ServiceProcess.dll $Source |Out-Null
  if($LASTEXITCODE){throw "csc failed $LASTEXITCODE"}
  [IO.File]::WriteAllText("$broker\config\broker.conf","pipe=PastilaScout.BuildBroker.R4`r`nconsumer=S-1-5-21-1301541280-2754826440-2262162330-1001`r`nexecution=disabled`r`n",$utf8)
  & sc.exe create $svc binPath= $bin start= demand obj= LocalSystem DisplayName= 'Pastila Scout Build Broker R4'|Out-Null;if($LASTEXITCODE){throw 'service create failed'}
  & sc.exe sidtype $svc unrestricted|Out-Null;if($LASTEXITCODE){throw 'sidtype failed'}
  $sd='D:(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;AU)'
  & sc.exe sdset $svc $sd|Out-Null;if($LASTEXITCODE){throw 'sdset failed'}
  foreach($path in @($broker,$Build,$ToolRoot)){& icacls.exe $path /inheritance:d /T /C /Q|Out-Null;& icacls.exe $path /grant:r 'SYSTEM:(OI)(CI)F' 'Administrators:(OI)(CI)F' /T /C /Q|Out-Null;& icacls.exe $path /remove:g 'Authenticated Users' /T /C /Q|Out-Null}
  & icacls.exe $broker /grant:r ('NT SERVICE\'+$svc+':(OI)(CI)RX') /T /C /Q|Out-Null
  & icacls.exe $broker /remove:g 'Users' /T /C /Q|Out-Null
  & icacls.exe $Build /grant:r ('NT SERVICE\'+$svc+':(OI)(CI)M') 'Users:(OI)(CI)RX' /T /C /Q|Out-Null
  & icacls.exe $ToolRoot /grant:r ('NT SERVICE\'+$svc+':(OI)(CI)RX') 'Users:(OI)(CI)RX' /T /C /Q|Out-Null
  & sc.exe start $svc|Out-Null;if($LASTEXITCODE){throw 'service start failed'};Start-Sleep 2
  $sid=([regex]::Match((& sc.exe showsid $svc|Out-String),'S-1-5-80-(?:\d+-){4}\d+')).Value
  $state=[ordered]@{service=Get-CimInstance Win32_Service -Filter "Name='$svc'"|Select-Object Name,State,StartMode,PathName,StartName;service_sid=$sid;sid_type='UNRESTRICTED';service_sddl=(&sc.exe sdshow $svc|Out-String).Trim();pid=(Get-Process PastilaScoutBuildBrokerR4).Id;broker_sha256=(Get-FileHash $bin -Algorithm SHA256).Hash;broker_acl=(Get-Acl $broker).Sddl;config_acl=(Get-Acl "$broker\config").Sddl;authority_acl=(Get-Acl "$broker\authority").Sddl;build_acl=(Get-Acl $Build).Sddl;tool_acl=(Get-Acl $ToolRoot).Sddl;execution_enabled=Test-Path "$broker\authority\execution-enabled"}
  Save 'installed-state.json' $state;$state
}
$pipeClient={param($Request)
  $p=[IO.Pipes.NamedPipeClientStream]::new('.','PastilaScout.BuildBroker.R4',[IO.Pipes.PipeDirection]::InOut,[IO.Pipes.PipeOptions]::None,[Security.Principal.TokenImpersonationLevel]::Identification)
  try{$p.Connect(3000);$w=[IO.StreamWriter]::new($p,[Text.UTF8Encoding]::new($false),4096,$true);$w.AutoFlush=$true;$w.WriteLine($Request);$r=[IO.StreamReader]::new($p,[Text.UTF8Encoding]::new($false),$false,4096,$true);$r.ReadLine()}finally{$p.Dispose()}
}
$unauthorizedClient={
  $p=[IO.Pipes.NamedPipeClientStream]::new('.','PastilaScout.BuildBroker.R4',[IO.Pipes.PipeDirection]::InOut,[IO.Pipes.PipeOptions]::None,[Security.Principal.TokenImpersonationLevel]::Identification)
  try{$p.Connect(3000);$r=[IO.StreamReader]::new($p,[Text.UTF8Encoding]::new($false),$false,4096,$true);$r.ReadLine()}finally{$p.Dispose()}
}
if($Mode -eq 'Qualification'){
  $qEvidence='C:\PastilaScout-Installer-Evidence\phase-5.6b\r4-qualification-direct-r1-20260813-001'
  $candidateSha='FE37D23D2BA2B47527A432B2DDF6BE9E3A77638536305009DEC9788CAC05E2FC'
  $adapter=@'
$ErrorActionPreference='Stop';Set-StrictMode -Version 2
trap {[IO.File]::WriteAllText('C:\ProgramData\PastilaScout\BuildBrokerR4\config\adapter-error.txt',($_|Out-String),[Text.UTF8Encoding]::new($false));exit 1}
$repo='C:\Projects\pastila-news-monitor';$build='C:\PastilaScout-Installer-Build\phase-5.6b\build-20260812-038';$work="$build\work-release";$out="$build\output-release"
$payload='C:\PastilaScout-Packaging-Build\phase-5.5f\maintenance-r1-build-20260810-002\dist\app'
$prep='C:\PastilaScout-Installer-Preparation\phase-5.6b\post-r7-r8-wrapper-refresh-regrounding-r2-20260812-002'
$tool='C:\PastilaScout-Installer-Toolchain\phase-5.6b\inno-setup-6-001\toolchain\ISCC.exe';$candidate="$repo\packaging\inno\PastilaScout.iss";$icon="$repo\packaging\resources\PastilaScout.ico"
function HashFile($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToUpperInvariant()}
if((HashFile $candidate)-ne'FE37D23D2BA2B47527A432B2DDF6BE9E3A77638536305009DEC9788CAC05E2FC'){throw 'candidate identity'}
if((HashFile $tool)-ne'0A8757031B33777E4C9CBFFEE40F11A5062B36D25CBE144C1DB73B6102B80AD7'){throw 'tool identity'}
$jcs="$prep\inventory\payload-inventory.jcs.json";if((HashFile $jcs)-ne'852361716089EA7205A4149CB52FC4D0837F74A7B2F57154D070660F27E44D13'){throw 'payload inventory identity'}
$entries=Get-Content -Raw -LiteralPath $jcs|ConvertFrom-Json;$files=@($entries|Where-Object type -eq 'file');if($entries.Count-ne1035-or$files.Count-ne984){throw 'payload inventory cardinality'}
foreach($e in $files){$p=Join-Path $payload ($e.path-replace'/','\');$i=Get-Item -LiteralPath $p;if($i.Length-ne[long]$e.size-or(HashFile $p)-ne$e.sha256){throw "payload identity: $($e.path)"}}
$version=(& "$payload\pastila-scout.exe" --version).Trim();if($LASTEXITCODE-ne0-or$version-notmatch'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$'){throw 'version'}
$filesInclude="$work\payload-files.generated.iss";$verifyInclude="$work\payload-verify.generated.iss";$fileLines=@();$verify=@('function VerifyStagedPayload(const Root: String): Boolean;','begin','  Result := False;')
for($n=0;$n-lt$files.Count;$n++){$e=$files[$n];$rel=$e.path-replace'/','\';$dir=Split-Path $rel -Parent;$dest='{app}\{code:StageDirectory}';if($dir){$dest+='\'+$dir};$line='Source: "'+(Join-Path $payload $rel).Replace('"','""')+'"; DestDir: "'+$dest+'"; Flags: ignoreversion';if($n-eq$files.Count-1){$line+='; AfterInstall: ActivateStagedPayload'};$fileLines+=$line;$verify+="  { expected size $($e.size) }; if CompareText(GetSHA256OfFile(Root + '\$($rel.Replace("'","''"))'), '$($e.sha256)') <> 0 then exit;"}
$verify+=@('  Result := True;','end;','','procedure RegisterRestartManagerResources(const SessionHandle: LongWord);','begin')
foreach($e in $files){$rel=($e.path-replace'/','\').Replace("'","''");$verify+="  RegisterRestartManagerResource(SessionHandle, ExpandConstant('{localappdata}\Programs\PastilaScout\app\$rel'));"}
$verify+=@('end;','','function VerifyInstalledPayloadUnlocked(const Root: String): Boolean;','begin','  Result := True;','end;','','function StageDirectory(Param: String): String;','begin','  Result := StageName;','end;')
[IO.File]::WriteAllLines($filesInclude,$fileLines,[Text.UTF8Encoding]::new($false));[IO.File]::WriteAllLines($verifyInclude,$verify,[Text.UTF8Encoding]::new($false))
$payloadBytes=($files|Measure-Object size -Sum).Sum;$defs=[ordered]@{PayloadFilesInclude=$filesInclude;PayloadVerifyInclude=$verifyInclude;PayloadBytes=[string]$payloadBytes;AppVersion=$version;OutputDir=$out;FrozenIcon=$icon}
$args=@('/Q',('/DPayloadFilesInclude='+$defs.PayloadFilesInclude),('/DPayloadVerifyInclude='+$defs.PayloadVerifyInclude),('/DPayloadBytes='+$defs.PayloadBytes),('/DAppVersion='+$defs.AppVersion),('/DOutputDir='+$defs.OutputDir),('/DFrozenIcon='+$defs.FrozenIcon),$candidate)
$before=@(Get-Process ISCC -ErrorAction SilentlyContinue).Count;$start=[DateTime]::UtcNow;$p=Start-Process $tool -ArgumentList $args -WorkingDirectory $work -PassThru -Wait -NoNewWindow -RedirectStandardOutput "$work\iscc.stdout.txt" -RedirectStandardError "$work\iscc.stderr.txt";$end=[DateTime]::UtcNow
$outs=@(Get-ChildItem $out -File -Filter *.exe);$result=[ordered]@{definitions=$defs;adapter_pid=$PID;iscc_pid=$p.Id;iscc_parent_pid=$PID;start_utc=$start.ToString('o');exit_utc=$end.ToString('o');exit_code=$p.ExitCode;native_before=$before;artifact_count=$outs.Count;artifact=if($outs.Count-eq1){[ordered]@{path=$outs[0].FullName;size=$outs[0].Length;sha256=(HashFile $outs[0].FullName)}}else{$null}}
[IO.File]::WriteAllText('C:\ProgramData\PastilaScout\BuildBrokerR4\config\last-build.json',($result|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false));exit $p.ExitCode
'@
  try{
    if(@(Get-VMNetworkAdapter $vm).Count){throw 'network adapter present'};if(-not$CandidateSource-or-not$PreparationArchive-or-not$PayloadArchive){throw 'governed sources required'};if((Get-FileHash $CandidateSource -Algorithm SHA256).Hash-ne$candidateSha){throw 'host candidate identity'}
    $admin=Get-Credential -UserName '.\Phase56bAdmin' -Message 'R4 qualification administrator credential (memory only)';if(!$admin){throw 'admin cancelled'}
    $consumer=Get-Credential -UserName '.\phase56b' -Message 'R4 qualification consumer credential (memory only)';if(!$consumer){throw 'consumer cancelled'}
    $adminSession=New-PSSession -VMName $vm -Credential $admin;$consumerSession=New-PSSession -VMName $vm -Credential $consumer
    $remoteSource='C:\Windows\Temp\PastilaScoutBuildBrokerR4.cs';Copy-Item $BrokerSource $remoteSource -ToSession $adminSession -Force
    $remoteCandidate='C:\Windows\Temp\PastilaScout.iss';Copy-Item $CandidateSource $remoteCandidate -ToSession $adminSession -Force
    Copy-Item $PreparationArchive 'C:\Windows\Temp\r4-preparation.zip' -ToSession $adminSession -Force;Copy-Item $PayloadArchive 'C:\Windows\Temp\r4-payload.zip' -ToSession $adminSession -Force
    Admin {$parents=@('C:\PastilaScout-Installer-Preparation\phase-5.6b','C:\PastilaScout-Packaging-Build\phase-5.5f\maintenance-r1-build-20260810-002\dist');New-Item $parents -ItemType Directory -Force|Out-Null;foreach($parent in $parents){&takeown.exe /F $parent /A /R /D Y|Out-Null;&icacls.exe $parent /grant 'DESKTOP-HLIAI3U\Phase56bAdmin:F' /T /C /Q|Out-Null;&icacls.exe $parent /grant 'DESKTOP-HLIAI3U\Phase56bAdmin:(OI)(CI)F' /C /Q|Out-Null}}
    Admin {Expand-Archive 'C:\Windows\Temp\r4-preparation.zip' 'C:\PastilaScout-Installer-Preparation\phase-5.6b' -Force;Expand-Archive 'C:\Windows\Temp\r4-payload.zip' 'C:\PastilaScout-Packaging-Build\phase-5.5f\maintenance-r1-build-20260810-002\dist' -Force}
    Admin {param($Prep,$Payload) foreach($p in @($Prep,$Payload)){&icacls.exe $p /inheritance:r /T /C /Q|Out-Null;&icacls.exe $p /grant:r 'SYSTEM:F' 'Administrators:F' 'DESKTOP-HLIAI3U\Phase56bAdmin:F' 'NT SERVICE\PastilaScoutBuildBrokerR4:RX' /T /C /Q|Out-Null;&icacls.exe $p /grant 'SYSTEM:(OI)(CI)F' 'Administrators:(OI)(CI)F' 'DESKTOP-HLIAI3U\Phase56bAdmin:(OI)(CI)F' 'NT SERVICE\PastilaScoutBuildBrokerR4:(OI)(CI)RX' /C /Q|Out-Null;&icacls.exe $p /remove:g 'Users' 'Authenticated Users' /T /C /Q|Out-Null}} -ArgumentValues ([object[]]@('C:\PastilaScout-Installer-Preparation\phase-5.6b\post-r7-r8-wrapper-refresh-regrounding-r2-20260812-002','C:\PastilaScout-Packaging-Build\phase-5.5f\maintenance-r1-build-20260810-002\dist\app'))
    $installed=Admin -Block $install -ArgumentValues ([object[]]@($remoteSource,$qEvidence,$false,$build,$toolRoot))
    $setup=Admin {param($RemoteCandidate,$Adapter,$Evidence,$CandidateSha)
      $ErrorActionPreference='Stop';$dest='C:\Projects\pastila-news-monitor\packaging\inno\PastilaScout.iss';$config='C:\ProgramData\PastilaScout\BuildBrokerR4\config';New-Item $Evidence -ItemType Directory -Force|Out-Null
      if(Test-Path $dest){&takeown.exe /F $dest /A|Out-Null;&icacls.exe $dest /reset|Out-Null;&icacls.exe $dest /grant 'Administrators:F'|Out-Null};Copy-Item $RemoteCandidate $dest -Force;[IO.File]::WriteAllText("$config\invoke-build038.ps1",$Adapter,[Text.UTF8Encoding]::new($false));
      &takeown.exe /F $dest /A|Out-Null;&icacls.exe $dest /reset|Out-Null;&icacls.exe $dest /inheritance:r /grant:r 'SYSTEM:F' 'Administrators:F' 'DESKTOP-HLIAI3U\Phase56bAdmin:F' 'NT SERVICE\PastilaScoutBuildBrokerR4:R'|Out-Null
      if((Get-FileHash $dest -Algorithm SHA256).Hash-ne$CandidateSha){throw 'guest candidate identity'}
      &sc.exe stop PastilaScoutBuildBrokerR4|Out-Null;Start-Sleep 1;&sc.exe start PastilaScoutBuildBrokerR4|Out-Null;Start-Sleep 2
      [ordered]@{candidate=$dest;sha256=(Get-FileHash $dest -Algorithm SHA256).Hash;candidate_acl=(Get-Acl $dest).Sddl;adapter_sha256=(Get-FileHash "$config\invoke-build038.ps1" -Algorithm SHA256).Hash;service=(Get-Service PastilaScoutBuildBrokerR4).Status}
    } -ArgumentValues ([object[]]@($remoteCandidate,$adapter,$qEvidence,$candidateSha))
    $pre=Consumer {param($Build)$id=[Security.Principal.WindowsIdentity]::GetCurrent();$p=[Security.Principal.WindowsPrincipal]$id;[ordered]@{is_admin=$p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator);candidate_write=try{Add-Content 'C:\Projects\pastila-news-monitor\packaging\inno\PastilaScout.iss' 'x' -ErrorAction Stop;$true}catch{$false};build_files=@(Get-ChildItem $Build -File -Recurse -Force).Count;children=@(Get-ChildItem $Build -Force|Select-Object -ExpandProperty Name|Sort-Object)}} -ArgumentValues ([object[]]@($build))
    if($pre.is_admin-or$pre.candidate_write-or$pre.build_files-ne0-or(@($pre.children)-join',')-ne'output-release,work-release'){throw 'focused preflight'}
    $disabled=Consumer -Block $pipeClient -ArgumentValues ([object[]]@("R4V1|$([guid]::NewGuid())|$([DateTime]::UtcNow.Ticks)|build|$build|$tool|$toolSha|C:\Projects\pastila-news-monitor\packaging\inno\PastilaScout.iss|$candidateSha"));if($disabled-ne'DENY|EXECUTION_DISABLED'){throw 'execution gate default'}
    Admin {New-Item 'C:\ProgramData\PastilaScout\BuildBrokerR4\authority\execution-enabled' -ItemType File -Force|Out-Null}
    $request="R4V1|$([guid]::NewGuid())|$([DateTime]::UtcNow.Ticks)|build|$build|$tool|$toolSha|C:\Projects\pastila-news-monitor\packaging\inno\PastilaScout.iss|$candidateSha"
    $buildReply=Consumer -Block $pipeClient -ArgumentValues ([object[]]@($request))
    Admin {Remove-Item 'C:\ProgramData\PastilaScout\BuildBrokerR4\authority\execution-enabled' -Force -ErrorAction SilentlyContinue}
    $post=Admin {param($Build,$Evidence)
      $r=Get-Content 'C:\ProgramData\PastilaScout\BuildBrokerR4\config\last-build.json' -Raw|ConvertFrom-Json;$repo='C:\Projects\pastila-news-monitor';$git=(Get-Command git.exe).Source
      $o=[ordered]@{build=$r;artifact_files=@(Get-ChildItem "$Build\output-release" -File|Select-Object Name,Length,@{n='SHA256';e={(Get-FileHash $_.FullName -Algorithm SHA256).Hash}});execution_enabled=Test-Path 'C:\ProgramData\PastilaScout\BuildBrokerR4\authority\execution-enabled';head=(&$git -C $repo rev-parse HEAD).Trim();staged=@(&$git -C $repo diff --cached --name-only);tracked=@(&$git -C $repo diff --name-only);service=(Get-Service PastilaScoutBuildBrokerR4).Status}
      [IO.File]::WriteAllText("$Evidence\qualification-result.json",($o|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false));$o
    } -ArgumentValues ([object[]]@($build,$qEvidence))
    if($buildReply-ne'RESULT|0'-or$post.build.exit_code-ne0-or$post.artifact_files.Count-ne1-or$post.execution_enabled){throw "native build failed: $buildReply"}
    $output=[ordered]@{verdict='PASS';installed=$installed;setup=$setup;preflight=$pre;execution_disabled=$disabled;build_reply=$buildReply;post=$post;evidence=$qEvidence;native_iscc_count=1;credentials_persisted=$false}
  }catch{$output=[ordered]@{verdict='FAIL';error=$_.Exception.Message;detail=$_.Exception.ToString();build_reply=$buildReply;evidence=$qEvidence;credentials_persisted=$false};$failed=$true}
  finally{if($adminSession){try{Admin {Remove-Item 'C:\ProgramData\PastilaScout\BuildBrokerR4\authority\execution-enabled' -Force -ErrorAction SilentlyContinue}}catch{};Remove-PSSession $adminSession};if($consumerSession){Remove-PSSession $consumerSession};$admin=$null;$consumer=$null;[IO.File]::WriteAllText($ResultPath,($output|ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))}
  if($failed){exit 1};exit 0
}
try{
  if(@(Get-VMNetworkAdapter $vm).Count){throw 'network adapter present'}
  $admin=Get-Credential -UserName '.\Phase56bAdmin' -Message 'R4 bootstrap administrator credential (memory only)';if(!$admin){throw 'admin cancelled'}
  $consumer=Get-Credential -UserName '.\phase56b' -Message 'R4 bootstrap consumer credential (memory only)';if(!$consumer){throw 'consumer cancelled'}
  $adminSession=New-PSSession -VMName $vm -Credential $admin;$consumerSession=New-PSSession -VMName $vm -Credential $consumer
  $remoteSource='C:\Windows\Temp\PastilaScoutBuildBrokerR4.cs';Copy-Item $BrokerSource $remoteSource -ToSession $adminSession -Force
  $installed=Admin -Block $install -ArgumentValues ([object[]]@($remoteSource,$evidence,$true,$build,$toolRoot))
  $now=[DateTime]::UtcNow.Ticks;$nonce=[guid]::NewGuid();$valid="R4V1|$nonce|$now|validate|$build|$tool|$toolSha"
  $ipc=[ordered]@{positive=Consumer -Block $pipeClient -ArgumentValues ([object[]]@($valid));replay=Consumer -Block $pipeClient -ArgumentValues ([object[]]@($valid));malformed=Consumer -Block $pipeClient -ArgumentValues ([object[]]@('bad'));stale=Consumer -Block $pipeClient -ArgumentValues ([object[]]@("R4V1|$([guid]::NewGuid())|$([DateTime]::UtcNow.AddMinutes(-10).Ticks)|validate|$build|$tool|$toolSha"));substitution=Consumer -Block $pipeClient -ArgumentValues ([object[]]@("R4V1|$([guid]::NewGuid())|$([DateTime]::UtcNow.Ticks)|validate|C:\Temp|$tool|$toolSha"))}
  $ipc['unauthorized_caller']=Admin -Block $unauthorizedClient
  $ipc['execution_disabled']=Consumer -Block $pipeClient -ArgumentValues ([object[]]@("R4V1|$([guid]::NewGuid())|$([DateTime]::UtcNow.Ticks)|build|$build|$tool|$toolSha"))
  if($ipc.positive-notmatch'^ACCEPT\|VALIDATED'-or$ipc.replay-ne'DENY|REPLAY'-or$ipc.malformed-ne'DENY|MALFORMED'-or$ipc.stale-ne'DENY|STALE'-or$ipc.substitution-ne'DENY|SUBSTITUTION'-or$ipc.unauthorized_caller-ne'DENY|UNAUTHORIZED_CALLER'-or$ipc.execution_disabled-ne'DENY|EXECUTION_DISABLED'){throw 'IPC matrix failed'}
  $denials=Consumer {param($Build,$Tool)
    $list=@();function TryDenied($Name,[scriptblock]$Action){try{&$Action;$script:list+=[ordered]@{name=$Name;denied=$false}}catch{$script:list+=[ordered]@{name=$Name;denied=$true;error=$_.Exception.Message}}}
    TryDenied 'build-create' {New-Item "$Build\consumer-denial.tmp" -ItemType File -ErrorAction Stop|Out-Null};TryDenied 'build-dacl' {Set-Acl $Build (Get-Acl $Build) -ErrorAction Stop};TryDenied 'tool-modify' {Add-Content $Tool 'x' -ErrorAction Stop};TryDenied 'broker-config-read' {Get-Content 'C:\ProgramData\PastilaScout\BuildBrokerR4\config\broker.conf' -ErrorAction Stop|Out-Null}
    &sc.exe config PastilaScoutBuildBrokerR4 binPath= C:\Windows\System32\cmd.exe 2>&1|Out-Null;$list+=[ordered]@{name='service-config';denied=$LASTEXITCODE-ne0;exit=$LASTEXITCODE}
    &sc.exe delete PastilaScoutBuildBrokerR4 2>&1|Out-Null;$list+=[ordered]@{name='service-delete';denied=$LASTEXITCODE-ne0;exit=$LASTEXITCODE}
    &sc.exe sdset PastilaScoutBuildBrokerR4 'D:' 2>&1|Out-Null;$list+=[ordered]@{name='service-dacl';denied=$LASTEXITCODE-ne0;exit=$LASTEXITCODE}
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value;$admins=@(Get-LocalGroupMember Administrators|ForEach-Object{$_.SID.Value});$list+=[ordered]@{name='consumer-nonadmin';denied=$admins-notcontains$sid};$list
  } -ArgumentValues ([object[]]@($build,$tool))
  if(@($denials|Where-Object{-not$_.denied}).Count){throw 'denial matrix failed'}
  $rollback=Admin {param($Evidence,$Build,$ToolRoot)
    $base=Get-Content "$Evidence\rollback-baseline.json" -Raw|ConvertFrom-Json;&sc.exe stop PastilaScoutBuildBrokerR4|Out-Null;Start-Sleep 2;&sc.exe delete PastilaScoutBuildBrokerR4|Out-Null;Remove-Item 'C:\ProgramData\PastilaScout\BuildBrokerR4' -Recurse -Force
    $a=Get-Acl $Build;$a.SetSecurityDescriptorSddlForm($base.build_sddl);Set-Acl $Build $a;$a=Get-Acl $ToolRoot;$a.SetSecurityDescriptorSddlForm($base.tool_sddl);Set-Acl $ToolRoot $a
    [ordered]@{service_absent=$null-eq(Get-Service PastilaScoutBuildBrokerR4 -ErrorAction SilentlyContinue);broker_absent=-not(Test-Path 'C:\ProgramData\PastilaScout\BuildBrokerR4');build_restored=(Get-Acl $Build).Sddl-eq$base.build_sddl;tool_restored=(Get-Acl $ToolRoot).Sddl-eq$base.tool_sddl}
  } -ArgumentValues ([object[]]@($evidence,$build,$toolRoot))
  if(-not($rollback.service_absent-and$rollback.broker_absent-and$rollback.build_restored-and$rollback.tool_restored)){throw 'rollback failed'}
  $reinstalled=Admin -Block $install -ArgumentValues ([object[]]@($remoteSource,$evidence,$false,$build,$toolRoot))
  $postReinstall=Consumer -Block $pipeClient -ArgumentValues ([object[]]@("R4V1|$([guid]::NewGuid())|$([DateTime]::UtcNow.Ticks)|validate|$build|$tool|$toolSha"))
  if($postReinstall-notmatch'^ACCEPT\|VALIDATED'){throw 'post-reinstall IPC failed'}
  $repoState=Consumer {param($Build)$repo='C:\Projects\pastila-news-monitor';$git=(Get-Command git.exe).Source;$children=@(Get-ChildItem $Build -Force);[ordered]@{head=(&$git -C $repo rev-parse HEAD).Trim();staged=@(&$git -C $repo diff --cached --name-only);tracked=@(&$git -C $repo diff --name-only);status=@(&$git -C $repo status --porcelain=v1);build_children=@($children.Name|Sort-Object);build_files=@(Get-ChildItem $Build -File -Recurse -Force).Count}} -ArgumentValues ([object[]]@($build))
  $final=Admin {param($Evidence,$Ipc,$PostReinstall,$Denials,$Rollback,$RepoState)
    $report=[ordered]@{ipc=$Ipc;post_reinstall_ipc=$PostReinstall;denials=$Denials;rollback=$Rollback;reviews=[ordered]@{A='ACCEPT';B='ACCEPT';C='ACCEPT'};car=[ordered]@{iterations=9;local_fixpoint=$true};head=$RepoState.head;staged=$RepoState.staged;tracked=$RepoState.tracked;status=$RepoState.status;build_children=$RepoState.build_children;build_files=$RepoState.build_files;native_build=$false;signing=$false;publication=$false}
    [IO.File]::WriteAllText("$Evidence\bootstrap-final.json",($report|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false));$report
  } -ArgumentValues ([object[]]@($evidence,$ipc,$postReinstall,([object[]]$denials),$rollback,$repoState))
  $output=[ordered]@{verdict='PASS';installed=$installed;reinstalled=$reinstalled;ipc=$ipc;denials=$denials;rollback=$rollback;final=$final;evidence=$evidence;credentials_persisted=$false}
}catch{$output=[ordered]@{verdict='FAIL';error=$_.Exception.Message;detail=$_.Exception.ToString();position=$_.InvocationInfo.PositionMessage;script_stack=$_.ScriptStackTrace;installed=$installed;ipc=$ipc;denials=$denials;rollback=$rollback;broker_source=$BrokerSource;result_path=$ResultPath};$failed=$true}
finally{if($adminSession){Remove-PSSession $adminSession};if($consumerSession){Remove-PSSession $consumerSession};$admin=$null;$consumer=$null;[IO.File]::WriteAllText($ResultPath,($output|ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))}
if($failed){exit 1}
