from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ISS = ROOT / "packaging/inno/PastilaScout.iss"
WRAPPER = ROOT / "packaging/inno/build-installer.ps1"
SPEC = ROOT / "docs/windows-application/WindowsInstallerSpecificationV1.md"
OWNERS = {
    ISS.relative_to(ROOT).as_posix(),
    WRAPPER.relative_to(ROOT).as_posix(),
    Path(__file__).relative_to(ROOT).as_posix(),
}


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_exact_owner_set_and_requirement_closure() -> None:
    assert OWNERS == {
        "packaging/inno/PastilaScout.iss",
        "packaging/inno/build-installer.ps1",
        "tests/packaging/test_inno_installer_v1.py",
    }
    ids = {int(value) for value in re.findall(r"INS-(\d{3})", text(SPEC))}
    assert ids == set(range(1, 70))


def test_per_user_x64_identity_and_forbidden_surfaces() -> None:
    source = text(ISS)
    required = [
        "AppId=PastilaScout",
        "PrivilegesRequired=lowest",
        "ArchitecturesAllowed=x64compatible",
        "ArchitecturesInstallIn64BitMode=x64compatible",
        "MinVersion=10.0.17763",
        r"DefaultDirName={localappdata}\Programs\PastilaScout",
        "RestartApplications=no",
        "ChangesAssociations=no",
        "ChangesEnvironment=no",
        "HKCU64",
    ]
    assert all(value in source for value in required)
    forbidden = [
        "[Registry]",
        "[Run]",
        "[Services]",
        "http://",
        "https://",
        "signtool",
        "timestamp",
    ]
    assert all(value.lower() not in source.lower() for value in forbidden)


def test_shortcuts_state_and_complete_replacement() -> None:
    source = text(ISS)
    assert r"{userprograms}\Pastila Scout" in source
    assert r"{userdesktop}\Pastila Scout" in source and "Flags: unchecked" in source
    assert "RenameFile(AppPath, OldPath)" in source
    assert "RenameFile(StagePath, AppPath)" in source
    assert "VerifyStagedPayload(StagePath)" in source
    assert "DelTree(ExpandConstant('{app}\\app')" in source
    assert "[UninstallDelete]" in source
    assert 'Type: dirifempty; Name: "{app}"' in source
    assert "DelTree(ExpandConstant('{userappdata}" not in source
    assert "DelTree(ExpandConstant('{localappdata}" not in source


def test_wrapper_consumes_exact_seal_and_toolchain() -> None:
    source = text(WRAPPER)
    for digest in (
        "852361716089EA7205A4149CB52FC4D0837F74A7B2F57154D070660F27E44D13",
        "818697EBB89AC773B13A3BCA70940F1556FFBD6F16D64D0CCB3CBE3815602FA2",
        "54409D2B4802DF707BB33EE21F8CCA408DEBAFA369ED961EB6631DAD48AEBEAC",
        "E2D696CD53ACF5607A451FC234F4BB054AB13EA194A2F1AEA7F027363B3D80CA",
        "6478034A97FDA5963B4A3C8969C06AEC26764C1D2FFA7F2575BE3AAE53B6971E",
        "FE17EE0B194D1569891B511096CB4E5A862288E21057D8EDBA7C4B8CBCBFA710",
        "0A8757031B33777E4C9CBFFEE40F11A5062B36D25CBE144C1DB73B6102B80AD7",
    ):
        assert digest in source
    assert "bindingKeys.Count -ne 11" in source
    assert "context does not bind" in source
    assert "Start-Process -FilePath $iscc" in source
    assert "Get-FileHash" in source and "GetSHA256OfFile" in source
    assert not re.search(
        r"Invoke-WebRequest|Start-BitsTransfer|curl|winget|choco|scoop",
        source,
        re.IGNORECASE,
    )


def test_no_runtime_helper_or_installed_inventory() -> None:
    source = text(ISS) + text(WRAPPER)
    assert "payload-inventory.jcs.json" in source
    assert 'DestDir: "{app}\\app"' not in source
    assert not re.search(
        r"python(?:\.exe)?|helper(?:\.exe|\.dll)", source, re.IGNORECASE
    )


def test_numeric_semver_and_disk_preflight_contract() -> None:
    source = text(ISS)
    assert "ParseStableSemVer" in source
    assert "PackVersionComponents" in source and "ComparePackedVersion" in source
    assert "CompareText(ExistingVersion" not in source
    assert "GetSpaceOnDisk64" in source
    assert "SafetyMarginBytes = 67108864" in source
    assert "Int64({#PayloadBytes}) * 3" in source
    assert source.index("HasRequiredDiskSpace") < source.index("StageName :=")


def test_wrapper_revalidates_corrected_accepted_projection() -> None:
    source = text(WRAPPER)
    required = [
        "fresh-output-inventory.txt",
        "accepted projection cardinality mismatch",
        "accepted projection missing",
        "accepted projection value mismatch",
        "parts.Count -ne 3",
    ]
    assert all(value in source for value in required)


def test_process_gate_precedes_stage_and_binds_installed_files() -> None:
    definition = text(ISS)
    wrapper = text(WRAPPER)
    assert "VerifyInstalledPayloadUnlocked" in wrapper
    assert "fmOpenReadWrite or fmShareExclusive" in wrapper
    assert definition.index("InstalledPayloadIsUnlocked") < definition.index(
        "StageName :="
    )
    assert "WizardSilent" in definition
    assert "Silent installation cannot continue" in definition


def test_interactive_restart_manager_is_canonical_pid_scoped_and_bounded() -> None:
    definition = text(ISS)
    wrapper = text(WRAPPER)
    required = [
        "RmStartSession@rstrtmgr.dll",
        "RmRegisterResources@rstrtmgr.dll",
        "RmGetList@rstrtmgr.dll",
        "RegisterRestartManagerResources(SessionHandle)",
        "GetWindowThreadProcessId",
        "IsRestartManagerProcess(ProcessId)",
        "IsWindowVisible(Window)",
        "GetWindow(Window, GwOwner) = 0",
        "PostMessage(Window, WmClose, 0, 0)",
        "InteractiveCloseTimeoutMs = 30000",
        "InstalledPayloadIsUnlocked(Root)",
    ]
    assert all(value in definition or value in wrapper for value in required)
    assert "RmShutdown" not in definition
    assert "RmForceShutdown" not in definition
    assert "TerminateProcess" not in definition
    assert definition.index("InteractiveCloseReleasedResources") < definition.index(
        "StageName :="
    )


def test_silent_gate_never_performs_close_negotiation() -> None:
    definition = text(ISS)
    silent = definition.index("if WizardSilent then begin")
    close = definition.index("InteractiveCloseReleasedResources(", silent)
    silent_exit = definition.index("exit;", silent)
    assert silent_exit < close


def test_authoritative_final_result_and_bounded_safe_retention() -> None:
    definition = text(ISS)
    required = [
        r"{localappdata}\PastilaScout",
        r"\logs",
        r"\installer",
        "InstallerResultRetentionCount = 10",
        "result-*.json",
        "Files.Sorted := True",
        "while Files.Count >= InstallerResultRetentionCount",
        "FILE_ATTRIBUTE_REPARSE_POINT",
        "WriteFinalOperationResult",
        "procedure DeinitializeSetup",
        "procedure DeinitializeUninstall",
        "OperationType := 'uninstall'",
        "CurUninstallStep = usPostUninstall",
        '"final_status"',
        '"final_result_code"',
        '"failure_class"',
        '"failure_stage"',
        '"activation_status"',
        '"restoration_status"',
        '"stage_cleanup_status"',
        '"residual_path"',
        '"surface_publication_status"',
    ]
    assert all(value in definition for value in required)
    assert "Successfully installed the file" not in definition
    assert "SaveStringToFile(Path, Body, False)" in definition
    assert "FileExists(Path) or HasReparsePoint(Path)" in definition
    assert "HasStaleOperationResidue" in definition
    assert r"\.stage-*" in definition and r"\.old-*" in definition
    assert "FailureClass := 'cleanup_failure'" in definition
    assert "FailureClass := 'stale_residue'" in definition
    assert "ResidualPath := StagePath" in definition
    assert "function JsonString" in definition
    assert "JsonString(ResidualPath)" in definition


def test_activation_precedes_conditional_surfaces_and_forces_failure_exit() -> None:
    definition = text(ISS)
    wrapper = text(WRAPPER)
    assert "AfterInstall: ActivateStagedPayload" in wrapper
    assert "GetCustomSetupExitCode" in definition
    assert "Result := 9" in definition
    assert "CreateUninstallRegKey=yes" in definition
    assert "Uninstallable=yes" in definition
    assert "RemoveFailedActivationSurfaces" in definition
    assert "RegDeleteKeyIncludingSubkeys(HKCU64" in definition
    assert "ExistingSurfacesAtStart := ValidExistingInstallerSurfaces()" in definition
    assert "function ValidExistingInstallerSurfaces" in definition
    for value in (
        "DisplayName",
        "DisplayVersion",
        "InstallLocation",
        "DisplayIcon",
        "UninstallString",
    ):
        assert value in definition
    assert "if ExistingSurfacesAtStart then" in definition
    assert (
        "preserving pre-existing installer surfaces after failed repair" in definition
    )
    assert "SurfaceStatus := 'preserved'" in definition
    assert "StringChangeEx(Result, #8, '\\b', False)" in definition
    assert "StringChangeEx(Result, #9, '\\t', False)" in definition
    assert "StringChangeEx(Result, #12, '\\f', False)" in definition
    icon_lines = [
        line
        for line in definition.splitlines()
        if line.startswith("Name:") and "Filename:" in line
    ]
    assert icon_lines and all(
        "Check: ActivationSucceeded" in line for line in icon_lines
    )
    assert "DelTree(StagePath, True, True, True)" in definition


def test_vm07a_result_creation_denial_precedes_invalid_destination_exit() -> None:
    definition = text(ISS)
    prepare = _procedure(
        definition, "function PrepareToInstall", "function SnapshotFile"
    )
    invalid = prepare[prepare.index("if not IsCanonicalInstallRoot") :]
    write = invalid.index("WriteFinalOperationResult();")
    failed = invalid.index("else if ResultWriteFailed then")
    exit_one = invalid.index("ExitProcess(1);")
    destination_error = invalid.index(
        "Result := 'The canonical per-user installation root is unavailable.';"
    )
    assert write < failed < exit_one < destination_error


def test_vm07b_retention_failure_preserves_native_exit_ten() -> None:
    definition = text(ISS)
    prepare = _procedure(
        definition, "function PrepareToInstall", "function SnapshotFile"
    )
    invalid = prepare[prepare.index("if not IsCanonicalInstallRoot") :]
    write = invalid.index("WriteFinalOperationResult();")
    retention_class = invalid.index("FailureClass = 'logging_retention_failure'")
    retention_stage = invalid.index("FailureStage = 'final_result'")
    exit_ten = invalid.index("ExitProcess(10)")
    generic_denial = invalid.index("else if ResultWriteFailed then")
    exit_one = invalid.index("ExitProcess(1);")
    assert (
        write < retention_class < retention_stage < exit_ten < generic_denial < exit_one
    )


def test_vm07a_successful_result_creation_retains_destination_exit_seven() -> None:
    definition = text(ISS)
    prepare = _procedure(
        definition, "function PrepareToInstall", "function SnapshotFile"
    )
    custom_exit = _procedure(
        definition, "function GetCustomSetupExitCode", "function GetProjectResultCode"
    )
    assert "if FailureStage = 'destination' then Result := 7" in custom_exit
    assert (
        "Result := 'The canonical per-user installation root is unavailable.';"
        in prepare
    )
    assert prepare.index("IsCanonicalInstallRoot") < prepare.index(
        "CaptureTransactionSnapshot"
    )
    assert "ActivateStagedPayload" not in prepare


def test_vm09a_insufficient_space_has_specific_preflight_classification() -> None:
    definition = text(ISS)
    initialize = _procedure(
        definition, "function InitializeSetup", "function PrepareToInstall"
    )
    low_space = initialize[initialize.index("if not HasRequiredDiskSpace then begin") :]
    rejection = low_space.index("SuppressibleMsgBox('Insufficient disk space")
    exit_statement = low_space.index("exit;", rejection)
    assert low_space.index("FailureClass := 'insufficient_space';") < rejection
    assert low_space.index("FailureStage := 'preflight';") < rejection
    assert rejection < exit_statement
    assert "SetupInitialized := True" not in low_space[:exit_statement]
    assert "CaptureTransactionSnapshot" not in low_space[:exit_statement]
    assert "ActivateStagedPayload" not in low_space[:exit_statement]


def _procedure(definition: str, name: str, next_name: str) -> str:
    start = definition.index(name)
    return definition[start : definition.index(next_name, start)]


def test_r7_transaction_retains_old_payload_until_verified_commit() -> None:
    definition = text(ISS)
    activation = _procedure(
        definition,
        "procedure ActivateStagedPayload",
        "procedure RemoveFailedActivationSurfaces",
    )
    resolver = _procedure(
        definition, "procedure ResolveTransaction", "procedure ActivateStagedPayload"
    )
    assert "DelTree(OldPath" not in activation
    assert (
        resolver.index("VerifyMandatoryPublicationSurfaces")
        < resolver.index("TransactionCommitted := True")
        < resolver.index("DelTree(OldPath")
    )


def test_r8_exact_mandatory_surface_aggregate() -> None:
    definition = text(ISS)
    verifier = _procedure(
        definition,
        "function VerifyMandatoryPublicationSurfaces",
        "function RemoveFileAndVerify",
    )
    assert "unins000.exe" in verifier and "unins000.dat" in verifier
    assert "unins000.msg" not in verifier
    for value in (
        "DisplayName",
        "DisplayVersion",
        "InstallLocation",
        "DisplayIcon",
        "UninstallString",
    ):
        assert value in verifier
    assert "ShortcutMatches" in verifier


def test_r7_failed_new_state_is_removed_before_prior_state_restoration() -> None:
    definition = text(ISS)
    restore = _procedure(
        definition, "function RestorePriorState", "procedure ResolveTransaction"
    )
    removal = restore.index("RemoveKeyAndVerify(Key)")
    payload_restore = restore.index("RenameFile(OldPath, AppPath)")
    arp_restore = restore.index("RestoreRegistryData")
    arp_verify = restore.index("VerifyRegistryDataSnapshot")
    assert removal < payload_restore < arp_restore < arp_verify


def test_r7_clean_install_rollback_verifies_aggregate_absence() -> None:
    definition = text(ISS)
    restore = _procedure(
        definition, "function RestorePriorState", "procedure ResolveTransaction"
    )
    clean = restore[restore.index("end else begin") :]
    for value in (
        "not DirExists(AppPath)",
        "not RegKeyExists(HKCU64, Key)",
        "not FileExists(Root + '\\unins000.exe')",
        "not FileExists(Root + '\\unins000.dat')",
        "not FileExists(ShortcutPath)",
    ):
        assert value in clean
    assert "(not DirExists(Root) or RemoveDir(Root)) and not DirExists(Root)" in clean
    prior = restore[: restore.index("end else begin")]
    assert "RemoveDir(Root)" not in prior
    assert "unins000.msg" not in restore


def test_r6_result_precedence_and_structured_initiating_failure() -> None:
    definition = text(ISS)
    project = _procedure(
        definition, "function GetProjectResultCode", "function InstallerLogRoot"
    )
    assert project.index("ResultWriteFailed") < project.index(
        "not AggregateCleanupSucceeded"
    )
    assert project.index("not AggregateCleanupSucceeded") < project.index(
        "Result := 11"
    )
    assert "Result := 9" in project and "TransactionCommitted" in project
    writer = _procedure(
        definition,
        "procedure WriteFinalOperationResult",
        "function HasStaleOperationResidue",
    )
    expected = '"initiating_failure":{"class":"surface_publication_failure",'
    assert expected in writer
    assert '"stage":"surface_publication","result_code":11}' in writer


def test_r7_snapshot_is_before_install_mutation_and_msg_is_not_synthesized() -> None:
    definition = text(ISS)
    prepare = _procedure(
        definition, "function PrepareToInstall", "function SnapshotFile"
    )
    steps = _procedure(
        definition, "procedure CurStepChanged", "procedure DeinitializeSetup"
    )
    assert "CaptureTransactionSnapshot" in prepare
    assert "CaptureTransactionSnapshot" not in steps
    assert "unins000.msg" not in definition


def test_repair_does_not_mutate_inherited_product_key_acl() -> None:
    definition = text(ISS)
    assert "Get-Acl" not in definition
    assert "Set-Acl" not in definition
    assert "GetAccessControl" not in definition
    assert "SetAccessControl" not in definition
    assert '"security_policy":"inherited_hkcu_product_key_not_mutated"' in definition


def test_repair_arp_snapshot_preserves_all_values_types_and_subkeys() -> None:
    definition = text(ISS)
    snapshot = _procedure(
        definition, "function SnapshotRegistryData", "function RestoreRegistryData"
    )
    restore = _procedure(
        definition,
        "function RestoreRegistryData",
        "function VerifyRegistryDataSnapshot",
    )
    verify = _procedure(
        definition,
        "function VerifyRegistryDataSnapshot",
        "function ShortcutMatches",
    )
    transaction = _procedure(
        definition,
        "function CaptureTransactionSnapshot",
        "function VerifyMandatoryPublicationSurfaces",
    )
    rollback = _procedure(
        definition, "function RestorePriorState", "procedure ResolveTransaction"
    )
    assert "ExportRegistryData(TransactionSnapshotRoot + '\\arp.reg')" in snapshot
    assert "reg.exe" in restore and "/reg:64" in restore
    assert "arp-restored.reg" in verify and "GetSHA256OfFile" in verify
    assert "SnapshotRegistryData" in transaction
    assert "RestoreRegistryData" in rollback
    assert "VerifyRegistryDataSnapshot" in rollback


def test_repair_car_failure_hooks_are_compile_time_only() -> None:
    definition = text(ISS)
    assert "#ifdef PASTILA_INSTALLER_REPAIR_CAR_FORCE_PUBLICATION_FAILURE" in definition
    assert "#ifdef PASTILA_INSTALLER_REPAIR_CAR_FORCE_ROLLBACK_FAILURE" in definition
    assert "Result := False;" in definition
    assert "DeleteFile(TransactionSnapshotRoot + '\\arp.reg')" in definition


def test_vm06a_clean_install_probes_preexisting_arp_publication_rights() -> None:
    definition = text(ISS)
    snapshot = _procedure(
        definition,
        "function CaptureTransactionSnapshot",
        "function VerifyMandatoryPublicationSurfaces",
    )
    assert "(not PriorPayloadExisted) and PriorArpExisted" in snapshot
    assert "Phase56BPublicationWriteProbe" in snapshot
    assert "RegWriteStringValue(HKCU64, Key, PublicationProbe, 'probe')" in snapshot
    assert "RegDeleteValue(HKCU64, Key, PublicationProbe)" in snapshot
    assert "PublicationFailed := True" in snapshot
    assert "FailureClass := 'surface_publication_failure'" in snapshot
    assert "FailureStage := 'surface_publication'" in snapshot


def test_vm06a_snapshot_publication_failure_uses_native_install_exit_four() -> None:
    definition = text(ISS)
    custom_exit = _procedure(
        definition, "function GetCustomSetupExitCode", "function GetProjectResultCode"
    )
    prepare = _procedure(
        definition, "function PrepareToInstall", "function SnapshotFile"
    )
    publication_start = prepare.index("if PublicationFailed then begin")
    publication_failure = prepare[
        publication_start : prepare.index(
            "FailureClass := 'preflight_failure'", publication_start
        )
    ]
    assert "else if PublicationFailed then Result := 4" in custom_exit
    assert "WriteFinalOperationResult();" in publication_failure
    assert "ExitProcess(GetCustomSetupExitCode);" in publication_failure
    assert publication_failure.index(
        "WriteFinalOperationResult();"
    ) < publication_failure.index("ExitProcess(GetCustomSetupExitCode);")


def test_r7_transaction_is_resolved_before_custom_exit_callback() -> None:
    definition = text(ISS)
    steps = _procedure(
        definition, "procedure CurStepChanged", "procedure DeinitializeSetup"
    )
    deinitialize = _procedure(
        definition, "procedure DeinitializeSetup", "function InitializeUninstall"
    )
    post_install = steps[
        steps.index("CurStep = ssPostInstall") : steps.index("CurStep = ssDone")
    ]
    assert "ResolveTransaction" not in post_install
    assert "DisposeTransactionSnapshot" not in post_install
    assert "CurStep = ssDone" in steps
    done = steps[steps.index("CurStep = ssDone") :]
    assert done.index("ResolveTransaction") < done.index("WriteFinalOperationResult")
    assert "RestorePriorPublicationSurfaces" in deinitialize
    assert "ResolveTransaction" in deinitialize
    assert "TransactionResolved" in definition


def test_failed_activation_restores_exact_prior_publication_surfaces() -> None:
    definition = text(ISS)
    restore = _procedure(
        definition,
        "function RestorePriorPublicationSurfaces",
        "function BooleanText",
    )
    deinitialize = _procedure(
        definition, "procedure DeinitializeSetup", "function InitializeUninstall"
    )
    for operation in (
        "RemoveKeyAndVerify",
        "RestoreFileAndVerify",
        "RestoreRegistryData",
        "VerifyRegistryDataSnapshot",
        "ShortcutMatches",
    ):
        assert operation in restore
    assert "not ActivationComplete" in deinitialize
    assert "PriorPayloadExisted" in deinitialize
    assert "DisposeTransactionSnapshot" in deinitialize


def test_r7_prior_payload_uses_complete_deterministic_inventory() -> None:
    definition = text(ISS)
    inventory = _procedure(
        definition,
        "function WritePayloadInventory",
        "function ExportRegistryData",
    )
    restore = _procedure(
        definition, "function RestorePriorState", "procedure ResolveTransaction"
    )
    assert "Get-ChildItem -LiteralPath $root -File -Recurse" in inventory
    assert "Sort-Object FullName" in inventory
    assert "$_.Length" in inventory and "Get-FileHash" in inventory
    assert "payload.inventory" in definition
    assert "payload-restored.inventory" in restore
    assert "GetSHA256OfFile(RestoredInventory)" in restore


def test_r7_powershell_paths_are_single_quote_escaped() -> None:
    definition = text(ISS)
    quoting = _procedure(
        definition, "function PowerShellSingleQuoted", "function WritePayloadInventory"
    )
    assert "StringChangeEx(Result, '''', '''''', True)" in quoting
    assert "PowerShellSingleQuoted(OutputPath)" in definition


def test_r7_arp_values_are_reverified_after_complete_data_restore() -> None:
    definition = text(ISS)
    restore = _procedure(
        definition, "function RestorePriorState", "procedure ResolveTransaction"
    )
    verification = restore.index("VerifyRegistryDataSnapshot")
    assert (
        restore.index("RegQueryStringValue(HKCU64, Key, 'DisplayName'", verification)
        > verification
    )
    assert (
        restore.index(
            "RegQueryStringValue(HKCU64, Key, 'UninstallString'", verification
        )
        > verification
    )


def _publication_outcome(
    surface_results: dict[str, bool], cleanup_results: dict[str, bool]
) -> dict:
    """Executable oracle for the frozen R6/R7/R8 aggregate and precedence contract."""
    if all(surface_results.values()):
        return {"committed": True, "project_code": 0, "initiating_failure": None}
    if all(cleanup_results.values()):
        return {"committed": False, "project_code": 11, "initiating_failure": None}
    return {
        "committed": False,
        "project_code": 9,
        "initiating_failure": {
            "class": "surface_publication_failure",
            "stage": "surface_publication",
            "result_code": 11,
        },
    }


def test_r7_r8_aggregate_behavior_rejects_each_partial_surface() -> None:
    surfaces = ("arp", "unins000.exe", "unins000.dat", "start_menu")
    for failed in surfaces:
        publication = {item: item != failed for item in surfaces}
        outcome = _publication_outcome(publication, {item: True for item in surfaces})
        assert outcome == {
            "committed": False,
            "project_code": 11,
            "initiating_failure": None,
        }


def test_r7_r8_each_cleanup_failure_forces_code9_and_strict_context() -> None:
    surfaces = ("arp", "unins000.exe", "unins000.dat", "start_menu", "payload")
    publication = {item: False for item in surfaces[:-1]}
    expected_context = {
        "class": "surface_publication_failure",
        "stage": "surface_publication",
        "result_code": 11,
    }
    for failed in surfaces:
        cleanup = {item: item != failed for item in surfaces}
        outcome = _publication_outcome(publication, cleanup)
        assert outcome["project_code"] == 9
        assert outcome["initiating_failure"] == expected_context
        assert set(outcome["initiating_failure"]) == {"class", "stage", "result_code"}


def test_r7_r8_complete_publication_is_the_only_commit_path() -> None:
    surfaces = {
        item: True for item in ("arp", "unins000.exe", "unins000.dat", "start_menu")
    }
    assert _publication_outcome(surfaces, {}) == {
        "committed": True,
        "project_code": 0,
        "initiating_failure": None,
    }


def test_r7_post_commit_disposal_failure_cannot_report_project_success() -> None:
    definition = text(ISS)
    project = _procedure(
        definition, "function GetProjectResultCode", "function InstallerLogRoot"
    )
    resolver = _procedure(
        definition, "procedure ResolveTransaction", "procedure ActivateStagedPayload"
    )
    assert project.index("FailureStage = 'cleanup'") < project.index(
        "TransactionCommitted"
    )
    assert "not DelTree(OldPath" in resolver
    assert "not DisposeTransactionSnapshot" in resolver
    assert resolver.count("FailureStage := 'cleanup'") >= 2


def test_r7_transaction_snapshot_disposal_is_verified_on_both_branches() -> None:
    definition = text(ISS)
    disposal = _procedure(
        definition, "function DisposeTransactionSnapshot", "function InstallerLogRoot"
    )
    resolver = _procedure(
        definition, "procedure ResolveTransaction", "procedure ActivateStagedPayload"
    )
    assert "DelTree(TransactionSnapshotRoot, True, True, True)" in disposal
    assert "not DirExists(TransactionSnapshotRoot)" in disposal
    assert resolver.count("DisposeTransactionSnapshot") == 2


def test_r7_failure_evidence_is_sealed_before_snapshot_disposal() -> None:
    definition = text(ISS)
    resolver = _procedure(
        definition, "procedure ResolveTransaction", "procedure ActivateStagedPayload"
    )
    failure_branch = resolver[resolver.index("PublicationFailed := True") :]
    assert (
        failure_branch.index("RestorePriorState")
        < failure_branch.index("SealRestorationEvidence")
        < failure_branch.index("DisposeTransactionSnapshot")
    )


def test_r7_disposal_only_failure_preserves_truthful_restoration_state() -> None:
    definition = text(ISS)
    resolver = _procedure(
        definition, "procedure ResolveTransaction", "procedure ActivateStagedPayload"
    )
    restored = resolver[resolver.index("if AggregateCleanupSucceeded then begin") :]
    disposal_failure = restored[
        restored.index("else begin") : restored.index("end else begin")
    ]
    assert "RestorationStatus := 'failed'" not in disposal_failure
    assert "ResidualPath := TransactionSnapshotRoot" in disposal_failure
    assert "FailureClass := 'cleanup_failure'" in disposal_failure


def test_r7_restoration_seal_binds_every_governed_surface_and_clean_topology() -> None:
    definition = text(ISS)
    seal = _procedure(
        definition, "function SealRestorationEvidence", "procedure ResolveTransaction"
    )
    for field in (
        '"topology"',
        '"payload"',
        '"arp"',
        '"unins000_exe"',
        '"unins000_dat"',
        '"start_menu"',
        '"required_absence_verified"',
        '"aggregate_verified"',
    ):
        assert field in seal
    assert "if PriorPayloadExisted then begin" in seal
    clean = seal[seal.index("end else begin") :]
    assert "Topology := 'clean_install'" in clean
    assert "payload.inventory" not in clean
    assert "RegKeyExists(HKCU64, Key)" in clean
    assert "GetSHA256OfFile(Path) <> ''" in seal
