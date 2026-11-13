; Books Arranger's assisted wizard. No stock close/kill process path is used.
; The builder provides a verified private payload and a generated hash macro.
!ifndef BOOKS_LIFECYCLE_INCLUDED
!define BOOKS_LIFECYCLE_INCLUDED
!ifndef BOOKS_LIFECYCLE_PAYLOAD
  !error "A verified BOOKS_LIFECYCLE_PAYLOAD is required"
!endif
!ifndef BOOKS_LIFECYCLE_PROCESS_NAME
  !define BOOKS_LIFECYCLE_PROCESS_NAME "${APP_EXECUTABLE_FILENAME}"
!endif
!include nsDialogs.nsh
!include LogicLib.nsh
!include FileFunc.nsh
!ifdef DELETE_APP_DATA_ON_UNINSTALL
  !undef DELETE_APP_DATA_ON_UNINSTALL
!endif
!define BOOKS_SAFE_UPGRADE_INCLUDE "${__FILEDIR__}\installer-safe-upgrade.nsh"
!ifdef UNINSTALLER_ICON
  !define BOOKS_INSTALLER_ICON "${UNINSTALLER_ICON}"
  !undef UNINSTALLER_ICON
!endif
!ifndef BUILD_UNINSTALLER
  !ifdef BOOKS_CURRENT_PACKAGE_INCLUDE
    !include "${BOOKS_CURRENT_PACKAGE_INCLUDE}"
  !endif
!endif

Var BooksPayloadReady
Var BooksRequestId
Var BooksRequest
Var BooksResponse
Var BooksExistingRadio
Var BooksNewRadio
Var BooksDialog
Var BooksTipWindow
Var BooksMaintenanceParent

!ifdef BUILD_UNINSTALLER
Var BooksCleanupMode
Var BooksCleanupList
Var BooksCleanupReview
Var BooksCleanupPlan
Var BooksCleanupSha
Var BooksCleanupBytes
Var BooksConfirm
Var BooksCleanupDetails
Var BooksCleanupWarning
Var BooksCleanupLocations
Var BooksCleanupResult
Var BooksCleanupSelection
!else
Var BooksMode
Var BooksDatabase
Var BooksExistingDatabase
Var BooksProfile
Var BooksPlan
Var BooksPlanSha
Var BooksDiscoveryResponse
Var BooksDatabaseList
Var BooksNewFolder
Var BooksNewFolderValue
Var BooksDetails
Var BooksBrowse
Var BooksRefresh
Var BooksRetainedPackage
Var BooksRetainedPackageSha
Var BooksFinalInstallDir
Var BooksApplicationStage
Var BooksApplicationStagePlan
Var BooksApplicationStageSha
Var BooksControlNamespace
Var BooksControlNamespaceSha
!endif

!macro BooksTip CONTROL TEXT
  ${If} $BooksTipWindow == ""
    System::Call 'user32::CreateWindowExW(i 0, w "tooltips_class32", p 0, i 0x80000003, i 0, i 0, i 0, i 0, p $BooksDialog, p 0, p 0, p 0) p .r8'
    StrCpy $BooksTipWindow $8
  ${EndIf}
  System::Alloc 4096
  Pop $8
  System::Call '*$8(&w2048 "${TEXT}")'
  System::Call '*(i 48, i 0x11, p $BooksDialog, p ${CONTROL}, i 0, i 0, i 0, i 0, p 0, p r8, p 0, p 0) p .r9'
  SendMessage $BooksTipWindow 0x432 0 $9
!macroend

!macro BooksCommon PREFIX
Function ${PREFIX}BooksEnsurePayload
  ${If} $BooksPayloadReady != "1"
    ReadEnvStr $BooksMaintenanceParent "TEMP"
    InitPluginsDir
    SetOutPath "$PLUGINSDIR\books-lifecycle"
    File /r "${BOOKS_LIFECYCLE_PAYLOAD}\*.*"
    !ifndef BUILD_UNINSTALLER
      !ifmacrodef BooksCurrentPackagePayload
        !insertmacro BooksCurrentPackagePayload "$PLUGINSDIR\books-lifecycle\backend"
      !endif
    !endif
    ; Never create/adopt FINAL Application merely to restore an extraction CWD.
    SetOutPath "$BooksMaintenanceParent"
    StrCpy $BooksPayloadReady "1"
  ${EndIf}
  !ifmacrodef BooksLifecycleVerifyPayload
    !insertmacro BooksLifecycleVerifyPayload "$PLUGINSDIR\books-lifecycle"
  !else
    !error "The builder must emit BooksLifecycleVerifyPayload"
  !endif
  !ifndef BUILD_UNINSTALLER
    !ifmacrodef BooksCurrentPackageVerify
      !insertmacro BooksCurrentPackageVerify "$PLUGINSDIR\books-lifecycle\backend"
    !endif
  !endif
FunctionEnd

Function ${PREFIX}BooksRestoreHelperEnvironment
  System::Call 'kernel32::SetEnvironmentVariableW(w "TEMP", w "$BooksMaintenanceParent") i .r8'
  System::Call 'kernel32::SetEnvironmentVariableW(w "TMP", w "$BooksMaintenanceParent") i .r8'
  System::Call 'kernel32::SetEnvironmentVariableW(w "BOOKS_WORK_TEMP", w "$BooksMaintenanceParent") i .r8'
  SetOutPath "$BooksMaintenanceParent"
FunctionEnd

Function ${PREFIX}BooksNewRequest
  Call ${PREFIX}BooksEnsurePayload
  IntOp $BooksRequestId $BooksRequestId + 1
  StrCpy $BooksRequest "$PLUGINSDIR\books-request-$BooksRequestId.ini"
  StrCpy $BooksResponse "$PLUGINSDIR\books-response-$BooksRequestId.ini"
  !if "${PREFIX}" == "un."
    WriteINIStr "$BooksRequest" "request" "runtime_path" "$EXEPATH"
  !endif
FunctionEnd

Function ${PREFIX}BooksRunHelper
  Call ${PREFIX}BooksEnsurePayload
  ; Only the private NSIS child contains operational copies/journals. The
  ; configured retained user Temp root must not change during cleanup review.
  ClearErrors
  CreateDirectory "$PLUGINSDIR\books-work"
  IfErrors books_helper_temp_failed
  System::Call 'kernel32::SetEnvironmentVariableW(w "TEMP", w "$PLUGINSDIR\books-work") i .r8'
  StrCmp $8 0 books_helper_temp_failed
  System::Call 'kernel32::SetEnvironmentVariableW(w "TMP", w "$PLUGINSDIR\books-work") i .r8'
  StrCmp $8 0 books_helper_temp_failed
  System::Call 'kernel32::SetEnvironmentVariableW(w "BOOKS_WORK_TEMP", w "$PLUGINSDIR\books-work") i .r8'
  StrCmp $8 0 books_helper_temp_failed
  nsExec::ExecToStack /TIMEOUT=600000 '"$PLUGINSDIR\books-lifecycle\python\python.exe" -I -B "$PLUGINSDIR\books-lifecycle\backend\storage_lifecycle.py" --wizard-request "$BooksRequest" --wizard-response "$BooksResponse"'
  Pop $0
  Pop $1
  ReadINIStr $2 "$BooksResponse" "result" "ok"
  ${If} $0 != "0"
    StrCpy $2 "0"
  ${EndIf}
  ; The helper alone owns the inner environment. NSIS teardown must still see
  ; its original configured parent, including on helper failure.
  Call ${PREFIX}BooksRestoreHelperEnvironment
  Return
books_helper_temp_failed:
  Call ${PREFIX}BooksRestoreHelperEnvironment
  StrCpy $2 "0"
  WriteINIStr "$BooksResponse" "result" "ok" "0"
  WriteINIStr "$BooksResponse" "result" "message" "Books Arranger cannot reach the selected location. Reconnect the drive or restore the folder before continuing."
FunctionEnd

Function ${PREFIX}BooksRefuse
  ReadINIStr $3 "$BooksResponse" "result" "message"
  ${If} $3 == ""
    StrCpy $3 "Books Arranger could not verify that its work has stopped. Choose Quit in Books Arranger and wait for its work to finish, then try again."
  ${EndIf}
  ${IfNot} ${Silent}
    MessageBox MB_OK|MB_ICONEXCLAMATION "$3"
  ${EndIf}
  SetErrorLevel 20
  Quit
FunctionEnd

Function ${PREFIX}BooksCheckRunning
  Call ${PREFIX}BooksNewRequest
  WriteINIStr "$BooksRequest" "request" "action" "process-check"
  WriteINIStr "$BooksRequest" "request" "process_name" "${BOOKS_LIFECYCLE_PROCESS_NAME}"
  WriteINIStr "$BooksRequest" "request" "installation_count" "1"
  WriteINIStr "$BooksRequest" "installation0" "path" "$INSTDIR"
  !ifdef BUILD_UNINSTALLER
    ${GetParameters} $0
    ${GetOptions} $0 "/BOOKSLAUNCHERPID=" $1
    ${If} $1 != ""
      WriteINIStr "$BooksRequest" "request" "launcher_pid" "$1"
    ${EndIf}
  !endif
  Call ${PREFIX}BooksRunHelper
  ${If} $2 != "1"
    Call ${PREFIX}BooksRefuse
  ${EndIf}
FunctionEnd
!macroend

; This supported hook is checked BEFORE electron-builder's default FIND/KILL
; implementation, including early silent un.onInit. customUnInit is too late.
!macro customCheckAppRunning
  !ifdef BUILD_UNINSTALLER
    ${GetParameters} $0
    ClearErrors
    ${GetOptions} $0 "--delete-app-data" $1
    ${IfNot} ${Errors}
      Call un.BooksRefuse
    ${EndIf}
    Call un.BooksCheckRunning
  !else
    ; installUtil defines this after customHeader. Replace at the first late
    ; section call, before installSection can invoke an old unsafe executable.
    !ifmacrodef uninstallOldVersion
      !ifndef BOOKS_SAFE_LEGACY_OVERRIDE
        !include "${BOOKS_SAFE_UPGRADE_INCLUDE}"
      !endif
    !endif
    Call BooksCheckRunning
    !ifdef UNINSTALL_REGISTRY_KEY
      Call BooksNewRequest
      WriteINIStr "$BooksRequest" "request" "action" "admit-application-target"
      WriteINIStr "$BooksRequest" "request" "process_name" "${BOOKS_LIFECYCLE_PROCESS_NAME}"
      WriteINIStr "$BooksRequest" "request" "application_dir" "$INSTDIR"
      ReadRegStr $R1 SHELL_CONTEXT "${INSTALL_REGISTRY_KEY}" "InstallLocation"
      ReadRegStr $R2 SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
      WriteINIStr "$BooksRequest" "request" "registered_application_dir" "$R1"
      WriteINIStr "$BooksRequest" "request" "registered_version" "$R2"
      Call BooksRunHelper
      ${If} $2 != "1"
        Call BooksRefuse
      ${EndIf}
      ${If} ${isUpdated}
        Call BooksPrepareLegacyUpdate
      ${EndIf}
    !endif
  !endif
!macroend

!ifdef BUILD_UNINSTALLER
  !insertmacro BooksCommon "un."
!else
  !insertmacro BooksCommon ""

Function BooksNormalizeDirectory
  ; Same substring search as the pinned stock StrContains helper, without
  ; owning its globals/function before assistedInstaller includes it.
  Push $1
  Push $2
  Push $3
  StrLen $1 "${APP_FILENAME}"
  StrLen $2 $INSTDIR
  StrCpy $3 -1
books_name_scan:
  IntOp $3 $3 + 1
  StrCpy $0 $INSTDIR $1 $3
  StrCmp $0 "${APP_FILENAME}" books_name_found
  StrCmp $3 $2 books_name_append
  Goto books_name_scan
books_name_append:
  StrCpy $INSTDIR "$INSTDIR\${APP_FILENAME}"
books_name_found:
  Pop $3
  Pop $2
  Pop $1
  ${GetParent} "$INSTDIR" $0
  StrCpy $BooksProfile "$0\Profile"
FunctionEnd

Function BooksPrepareLegacyUpdate
  ${If} $BooksPlan != ""
    Return
  ${EndIf}
  Call BooksNewRequest
  WriteINIStr "$BooksRequest" "request" "action" "legacy-update-plan"
  WriteINIStr "$BooksRequest" "request" "application_dir" "$INSTDIR"
  ReadRegStr $R2 SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
  WriteINIStr "$BooksRequest" "request" "version" "$R2"
  WriteINIStr "$BooksRequest" "request" "process_name" "${BOOKS_LIFECYCLE_PROCESS_NAME}"
  Call BooksRunHelper
  ${If} $2 != "1"
    Call BooksRefuse
  ${EndIf}
  ReadINIStr $0 "$BooksResponse" "result" "existing_bootstrap"
  ${If} $0 != "True"
    ReadINIStr $BooksPlan "$BooksResponse" "result" "plan_path"
    ReadINIStr $BooksPlanSha "$BooksResponse" "result" "plan_sha256"
  ${EndIf}
FunctionEnd

Function BooksPrepareApplicationStage
  Call BooksNewRequest
  WriteINIStr "$BooksRequest" "request" "action" "prepare-application-stage"
  WriteINIStr "$BooksRequest" "request" "application_dir" "$INSTDIR"
  WriteINIStr "$BooksRequest" "request" "retained_package" "$BooksRetainedPackage"
  WriteINIStr "$BooksRequest" "request" "retained_package_sha256" "$BooksRetainedPackageSha"
  Call BooksRunHelper
  ${If} $2 != "1"
    Call BooksRefuse
  ${EndIf}
  ReadINIStr $BooksApplicationStage "$BooksResponse" "result" "stage"
  ReadINIStr $BooksApplicationStagePlan "$BooksResponse" "result" "plan_path"
  ReadINIStr $BooksApplicationStageSha "$BooksResponse" "result" "plan_sha256"
  ReadINIStr $BooksControlNamespace "$BooksResponse" "result" "control_namespace"
  ReadINIStr $BooksControlNamespaceSha "$BooksResponse" "result" "control_namespace_sha256"
FunctionEnd

Function BooksPublishApplicationStage
  ; Windows refuses directory publication while this NSIS process itself uses
  ; the stage as its current directory. Keep the publisher outside both roots.
  SetOutPath "$PLUGINSDIR"
  Call BooksNewRequest
  WriteINIStr "$BooksRequest" "request" "action" "publish-application-stage"
  WriteINIStr "$BooksRequest" "request" "plan_path" "$BooksApplicationStagePlan"
  WriteINIStr "$BooksRequest" "request" "plan_sha256" "$BooksApplicationStageSha"
  Call BooksRunHelper
  ${If} $2 != "1"
    Call BooksRefuse
  ${EndIf}
FunctionEnd

Function BooksRefreshDatabases
  Pop $0
  Call BooksNewRequest
  WriteINIStr "$BooksRequest" "request" "action" "discover"
  WriteINIStr "$BooksRequest" "request" "bootstrap_count" "1"
  ${GetParent} "$INSTDIR" $0
  WriteINIStr "$BooksRequest" "bootstrap0" "path" "$0\books-arranger-installation.json"
  ${If} $BooksExistingDatabase != ""
    WriteINIStr "$BooksRequest" "request" "candidate_count" "1"
    WriteINIStr "$BooksRequest" "candidate0" "path" "$BooksExistingDatabase"
  ${EndIf}
  Call BooksRunHelper
  StrCpy $BooksDiscoveryResponse $BooksResponse
  SendMessage $BooksDatabaseList ${LB_RESETCONTENT} 0 0
  ${If} $2 != "1"
    ReadINIStr $0 "$BooksResponse" "result" "message"
    ${NSD_SetText} $BooksDetails "$0"
    Return
  ${EndIf}
  ReadINIStr $4 "$BooksResponse" "result" "count"
  StrCpy $5 0
  StrCpy $6 -1
  StrCpy $7 0
  ${DoWhile} $5 < $4
    ReadINIStr $0 "$BooksResponse" "candidate$5" "path"
    ReadINIStr $1 "$BooksResponse" "candidate$5" "state"
    ReadINIStr $9 "$BooksResponse" "candidate$5" "display_state"
    ${NSD_LB_AddString} $BooksDatabaseList "$0 ($9)"
    ${If} $0 == $BooksExistingDatabase
      StrCpy $6 $5
    ${EndIf}
    ${If} $1 == "available"
      IntOp $7 $7 + 1
      StrCpy $8 $5
    ${EndIf}
    IntOp $5 $5 + 1
  ${Loop}
  ${If} $4 == "0"
    ${NSD_SetText} $BooksDetails "No database was found in the locations checked. Browse for one or start with a new database."
  ${Else}
    ${NSD_SetText} $BooksDetails "Select a database and review its full path and status, or choose Browse."
  ${EndIf}
  ${If} $6 < 0
  ${AndIf} $BooksExistingDatabase == ""
  ${AndIf} $7 == 1
    StrCpy $6 $8
  ${EndIf}
  ${If} $6 >= 0
    SendMessage $BooksDatabaseList ${LB_SETCURSEL} $6 0
    Push 0
    Call BooksDatabaseChanged
  ${EndIf}
FunctionEnd

Function BooksDatabaseChanged
  Pop $0
  SendMessage $BooksDatabaseList ${LB_GETCURSEL} 0 0 $4
  ${If} $4 < 0
    Return
  ${EndIf}
  ReadINIStr $BooksExistingDatabase "$BooksDiscoveryResponse" "candidate$4" "path"
  StrCpy $BooksDatabase $BooksExistingDatabase
  ReadINIStr $0 "$BooksDiscoveryResponse" "candidate$4" "state"
  ReadINIStr $1 "$BooksDiscoveryResponse" "candidate$4" "resolved_path"
  ReadINIStr $3 "$BooksDiscoveryResponse" "candidate$4" "bytes"
  ${NSD_SetText} $BooksDetails "$BooksDatabase$\r$\n$0; $3 bytes$\r$\nResolved: $1"
  GetDlgItem $1 $HWNDPARENT 1
  ${If} $0 == "available"
    EnableWindow $1 1
  ${Else}
    EnableWindow $1 0
  ${EndIf}
FunctionEnd

Function BooksModeChanged
  Pop $0
  ${If} $BooksMode == "new"
    ${NSD_GetText} $BooksNewFolder $BooksNewFolderValue
  ${EndIf}
  ${NSD_GetState} $BooksNewRadio $0
  ${If} $0 == ${BST_CHECKED}
    StrCpy $BooksMode "new"
    ShowWindow $BooksDatabaseList ${SW_HIDE}
    ShowWindow $BooksNewFolder ${SW_SHOW}
    EnableWindow $BooksRefresh 0
  ${Else}
    StrCpy $BooksMode "existing"
    ShowWindow $BooksDatabaseList ${SW_SHOW}
    ShowWindow $BooksNewFolder ${SW_HIDE}
    EnableWindow $BooksRefresh 1
  ${EndIf}
  Push 0
  Call BooksValidateChanged
FunctionEnd

Function BooksBrowseDatabase
  Pop $0
  ${If} $BooksMode == "new"
    nsDialogs::SelectFolderDialog "Choose a separate empty data folder" ""
    Pop $0
    ${If} $0 != error
      ${NSD_SetText} $BooksNewFolder "$0"
      StrCpy $BooksNewFolderValue $0
    ${EndIf}
  ${Else}
    nsDialogs::SelectFileDialog open "" "SQLite database|*.sqlite3;*.sqlite;*.db|All files|*.*"
    Pop $0
    ${If} $0 != error
      StrCpy $BooksExistingDatabase $0
      StrCpy $BooksDatabase $0
      ${NSD_SetText} $BooksDetails "$BooksDatabase$\r$\nThe selected file will be checked before continuing."
      Push 0
      Call BooksValidateChanged
    ${EndIf}
  ${EndIf}
FunctionEnd

Function BooksDatabasePage
  ${If} ${isUpdated}
    Abort
  ${EndIf}
  Call BooksNormalizeDirectory
  !insertmacro MUI_HEADER_TEXT "Database" "Keep an existing catalog or create a separate new one."
  nsDialogs::Create 1018
  Pop $BooksDialog
  StrCpy $BooksTipWindow ""
  ${NSD_CreateLabel} 0 0 100% 18% "Use an existing database to keep its books, settings and job history, or start with a separate empty database."
  Pop $0
  ${NSD_CreateRadioButton} 0 20% 100% 9% "Use an existing database"
  Pop $BooksExistingRadio
  ${NSD_CreateRadioButton} 0 30% 100% 9% "Start with a new database. Existing databases and libraries will be kept."
  Pop $BooksNewRadio
  ${NSD_CreateListBox} 0 41% 100% 28% ""
  Pop $BooksDatabaseList
  ${NSD_CreateText} 0 41% 100% 12% ""
  Pop $BooksNewFolder
  ${GetParent} "$INSTDIR" $0
  ${NSD_SetText} $BooksNewFolder "$0\Data"
  ${If} $BooksNewFolderValue != ""
    ${NSD_SetText} $BooksNewFolder "$BooksNewFolderValue"
  ${EndIf}
  ${NSD_CreateButton} 0 70% 30% 12% "Browse..."
  Pop $BooksBrowse
  ${NSD_CreateButton} 33% 70% 30% 12% "Check again"
  Pop $BooksRefresh
  nsDialogs::CreateControl "EDIT" "${DEFAULT_STYLES}|${WS_TABSTOP}|${ES_MULTILINE}|${ES_AUTOVSCROLL}|${ES_READONLY}|${WS_VSCROLL}|${WS_HSCROLL}" "${WS_EX_CLIENTEDGE}" 0 84% 100% 16% "Looking for databases..."
  Pop $BooksDetails
  SendMessage $BooksDetails ${EM_SETREADONLY} 1 0
  ${NSD_OnClick} $BooksExistingRadio BooksModeChanged
  ${NSD_OnClick} $BooksNewRadio BooksModeChanged
  ${NSD_OnClick} $BooksBrowse BooksBrowseDatabase
  ${NSD_OnClick} $BooksRefresh BooksRefreshDatabases
  ${NSD_OnChange} $BooksDatabaseList BooksDatabaseChanged
  ${NSD_OnChange} $BooksNewFolder BooksValidateChanged
  !insertmacro BooksTip $BooksExistingRadio "Keep using the selected database and its saved history."
  !insertmacro BooksTip $BooksNewRadio "Create a separate empty database and keep existing data."
  !insertmacro BooksTip $BooksDatabaseList "Select a database; review its full path and status below."
  !insertmacro BooksTip $BooksNewFolder "Folder for the new database and its application data."
  !insertmacro BooksTip $BooksBrowse "Choose an existing database or a separate empty data folder."
  !insertmacro BooksTip $BooksRefresh "Check known locations and refresh the selected database's status."
  ${If} $BooksMode == "new"
    ${NSD_Check} $BooksNewRadio
  ${Else}
    ${NSD_Check} $BooksExistingRadio
  ${EndIf}
  Push 0
  Call BooksModeChanged
  Push 0
  Call BooksRefreshDatabases
  nsDialogs::Show
FunctionEnd

Function BooksValidateDatabase
  Call BooksNewRequest
  WriteINIStr "$BooksRequest" "request" "action" "selection"
  WriteINIStr "$BooksRequest" "request" "mode" "$BooksMode"
  ${If} $BooksMode == "new"
    ${NSD_GetText} $BooksNewFolder $0
    StrCpy $BooksNewFolderValue $0
  ${Else}
    StrCpy $0 $BooksExistingDatabase
  ${EndIf}
  WriteINIStr "$BooksRequest" "request" "location" "$0"
  WriteINIStr "$BooksRequest" "request" "application_dir" "$INSTDIR"
  WriteINIStr "$BooksRequest" "request" "profile_dir" "$BooksProfile"
  Call BooksRunHelper
  ${If} $2 != "1"
    ReadINIStr $0 "$BooksResponse" "result" "message"
    ${NSD_SetText} $BooksDetails "$0"
    Return
  ${EndIf}
  ReadINIStr $BooksPlan "$BooksResponse" "result" "plan_path"
  ReadINIStr $BooksPlanSha "$BooksResponse" "result" "plan_sha256"
  ReadINIStr $BooksDatabase "$BooksResponse" "result" "database"
  ReadINIStr $BooksProfile "$BooksResponse" "result" "profile_dir"
FunctionEnd

Function BooksValidateChanged
  Pop $0
  GetDlgItem $0 $HWNDPARENT 1
  EnableWindow $0 0
  Call BooksValidateDatabase
  ${If} $2 == "1"
    GetDlgItem $0 $HWNDPARENT 1
    EnableWindow $0 1
  ${EndIf}
FunctionEnd

Function BooksDatabaseLeave
  Call BooksValidateDatabase
  ${If} $2 != "1"
    Abort
  ${EndIf}
FunctionEnd

Function BooksReviewPage
  ${If} ${isUpdated}
    Abort
  ${EndIf}
  !insertmacro MUI_HEADER_TEXT "Ready to install" "Review the application and retained-data locations."
  nsDialogs::Create 1018
  Pop $BooksDialog
  ReadINIStr $0 "$BooksResponse" "result" "data_dir"
  ReadINIStr $1 "$BooksResponse" "result" "profile_confirmed"
  ${If} $BooksMode == "existing"
    StrCpy $3 "Existing data will be used in place."
  ${Else}
    StrCpy $3 "A separate empty database will be created. Existing data will be kept."
  ${EndIf}
  ${If} $1 != "True"
    StrCpy $1 "Settings location not confirmed."
  ${Else}
    StrCpy $1 "Associated settings will be preserved after verified closure."
  ${EndIf}
  nsDialogs::CreateControl "EDIT" "${DEFAULT_STYLES}|${WS_TABSTOP}|${ES_MULTILINE}|${ES_AUTOVSCROLL}|${ES_READONLY}|${WS_VSCROLL}|${WS_HSCROLL}" "${WS_EX_CLIENTEDGE}" 0 0 100% 100% "Application folder: $INSTDIR$\r$\n$\r$\nDatabase ($BooksMode): $BooksDatabase$\r$\nData folder: $0$\r$\nSettings folder: $BooksProfile$\r$\n$\r$\n$3$\r$\n$1"
  Pop $0
  SendMessage $0 ${EM_SETREADONLY} 1 0
  nsDialogs::Show
FunctionEnd

Function BooksCommitSelection
  ${If} ${isUpdated}
  ${AndIf} $BooksPlan == ""
    Call BooksNewRequest
    ${GetParent} "$INSTDIR" $0
    WriteINIStr "$BooksRequest" "request" "action" "capture-package"
    WriteINIStr "$BooksRequest" "request" "bootstrap" "$0\books-arranger-installation.json"
    WriteINIStr "$BooksRequest" "request" "retained_package" "$BooksRetainedPackage"
    WriteINIStr "$BooksRequest" "request" "retained_package_sha256" "$BooksRetainedPackageSha"
    WriteINIStr "$BooksRequest" "request" "control_namespace" "$BooksControlNamespace"
    WriteINIStr "$BooksRequest" "request" "control_namespace_sha256" "$BooksControlNamespaceSha"
    Call BooksRunHelper
    ${If} $2 != "1"
      Call BooksRefuse
    ${EndIf}
    Return
  ${EndIf}
  ${If} $BooksPlan == ""
    ; Silent fresh installation cannot invent a data selection.
    Call BooksRefuse
  ${EndIf}
  Call BooksNewRequest
  WriteINIStr "$BooksRequest" "request" "action" "commit-selection"
  WriteINIStr "$BooksRequest" "request" "plan_path" "$BooksPlan"
  WriteINIStr "$BooksRequest" "request" "plan_sha256" "$BooksPlanSha"
  WriteINIStr "$BooksRequest" "request" "retained_package" "$BooksRetainedPackage"
  WriteINIStr "$BooksRequest" "request" "retained_package_sha256" "$BooksRetainedPackageSha"
  WriteINIStr "$BooksRequest" "request" "control_namespace" "$BooksControlNamespace"
  WriteINIStr "$BooksRequest" "request" "control_namespace_sha256" "$BooksControlNamespaceSha"
  WriteINIStr "$BooksRequest" "request" "process_name" "${BOOKS_LIFECYCLE_PROCESS_NAME}"
  Call BooksRunHelper
  ${If} $2 != "1"
    ${IfNot} ${Silent}
      MessageBox MB_OK|MB_ICONEXCLAMATION "Application binaries were installed, but the retained-data settings were not switched. Existing data was kept."
    ${EndIf}
    Call BooksRefuse
  ${EndIf}
FunctionEnd

!macro customPageAfterChangeDir
  Page custom BooksDatabasePage BooksDatabaseLeave
  Page custom BooksReviewPage
!macroend
!macro customInstall
  Call BooksCommitSelection
  !ifdef UNINSTALL_REGISTRY_KEY
    ${GetParent} "$INSTDIR" $0
    WriteRegStr SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" "UninstallString" '$\"$INSTDIR\${APP_EXECUTABLE_FILENAME}$\" --run-uninstaller $\"--installation-config=$0\books-arranger-installation.json$\"'
    ; Silent removal is Keep-only; no CLI flag grants data-delete consent.
    WriteRegStr SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" "QuietUninstallString" '$\"$INSTDIR\${APP_EXECUTABLE_FILENAME}$\" --run-uninstaller --uninstall-silent $\"--installation-config=$0\books-arranger-installation.json$\"'
  !endif
!macroend
!endif

!ifdef BUILD_UNINSTALLER
Function un.BooksDataPage
  ${If} ${isUpdated}
    Abort
  ${EndIf}
  StrCpy $BooksCleanupMode "keep"
  Call un.BooksNewRequest
  ${GetParent} "$INSTDIR" $0
  WriteINIStr "$BooksRequest" "request" "action" "review-uninstall"
  WriteINIStr "$BooksRequest" "request" "application_dir" "$INSTDIR"
  WriteINIStr "$BooksRequest" "request" "bootstrap" "$0\books-arranger-installation.json"
  Call un.BooksRunHelper
  StrCpy $BooksCleanupReview $BooksResponse
  !insertmacro MUI_HEADER_TEXT "Keep or remove data" "Library folders and unrelated files are excluded."
  nsDialogs::Create 1018
  Pop $BooksDialog
  StrCpy $BooksTipWindow ""
  ${NSD_CreateRadioButton} 0 0 100% 10% "Keep my data"
  Pop $BooksExistingRadio
  ${NSD_Check} $BooksExistingRadio
  ${NSD_CreateLabel} 0 11% 100% 14% "Keep databases, settings, job history, recovery copies and backups for reinstalling."
  Pop $0
  ${NSD_CreateRadioButton} 0 27% 100% 10% "Remove Books Arranger data from selected locations"
  Pop $BooksNewRadio
  !insertmacro BooksTip $BooksExistingRadio "Remove the application while keeping its saved data."
  !insertmacro BooksTip $BooksNewRadio "Review app-owned locations for permanent deletion."
  nsDialogs::CreateControl "SysListView32" "${DEFAULT_STYLES}|${WS_TABSTOP}|0x0001|0x0008" "${WS_EX_CLIENTEDGE}" 0 38% 100% 29% ""
  Pop $BooksCleanupList
  SendMessage $BooksCleanupList 0x1036 0 0x24
  System::Call '*(i 0x26, i 0, i 155, w "Location", i 0, i 0) p .r0'
  SendMessage $BooksCleanupList 0x1061 0 $0
  System::Free $0
  System::Call '*(i 0x26, i 0, i 130, w "Contents", i 0, i 1) p .r0'
  SendMessage $BooksCleanupList 0x1061 1 $0
  System::Free $0
  System::Call '*(i 0x26, i 0, i 85, w "Size", i 0, i 2) p .r0'
  SendMessage $BooksCleanupList 0x1061 2 $0
  System::Free $0
  System::Call '*(i 0x26, i 0, i 100, w "Action", i 0, i 3) p .r0'
  SendMessage $BooksCleanupList 0x1061 3 $0
  System::Free $0
  !insertmacro BooksTip $BooksCleanupList "Select only the app-owned locations you want to delete."
  ReadINIStr $4 "$BooksCleanupReview" "result" "count"
  ${If} $4 == ""
    StrCpy $4 0
    EnableWindow $BooksNewRadio 0
  ${EndIf}
  StrCpy $5 0
  ${DoWhile} $5 < $4
    ReadINIStr $6 "$BooksCleanupReview" "target$5" "path"
    System::Call '*(i 1, i r5, i 0, i 0, i 0, w r6, i 0, i 0, p 0) p .r0'
    SendMessage $BooksCleanupList 0x104D 0 $0
    System::Free $0
    ReadINIStr $6 "$BooksCleanupReview" "target$5" "display_role"
    System::Call '*(i 1, i r5, i 1, i 0, i 0, w r6, i 0, i 0, p 0) p .r0'
    SendMessage $BooksCleanupList 0x104C 0 $0
    System::Free $0
    ReadINIStr $6 "$BooksCleanupReview" "target$5" "bytes"
    StrCpy $6 "$6 bytes"
    System::Call '*(i 1, i r5, i 2, i 0, i 0, w r6, i 0, i 0, p 0) p .r0'
    SendMessage $BooksCleanupList 0x104C 0 $0
    System::Free $0
    ReadINIStr $6 "$BooksCleanupReview" "target$5" "can_remove"
    ${If} $6 == "True"
      StrCpy $6 "Can remove"
    ${Else}
      StrCpy $6 "Kept: protected"
      ReadINIStr $8 "$BooksCleanupReview" "target$5" "state"
      ${If} $8 == "already_removed"
        StrCpy $6 "Already removed"
      ${EndIf}
    ${EndIf}
    System::Call '*(i 1, i r5, i 3, i 0, i 0, w r6, i 0, i 0, p 0) p .r0'
    SendMessage $BooksCleanupList 0x104C 0 $0
    System::Free $0
    IntOp $5 $5 + 1
  ${Loop}
  ${NSD_OnNotify} $BooksCleanupList un.BooksCleanupNotify
  nsDialogs::CreateControl "EDIT" "${DEFAULT_STYLES}|${WS_TABSTOP}|${ES_MULTILINE}|${ES_AUTOVSCROLL}|${ES_READONLY}|${WS_VSCROLL}|${WS_HSCROLL}" "${WS_EX_CLIENTEDGE}" 0 69% 100% 31% "Select a row to read its full location, resolved aliases, contents, size and reason. Eligible locations start unchecked."
  Pop $BooksCleanupDetails
  nsDialogs::Show
FunctionEnd

Function un.BooksCleanupNotify
  Pop $0
  Pop $1
  Pop $2
  ${If} $1 == -100
    System::Call '*$2(p,p,i,i.r3,i,i.r4,i.r5)'
    ${If} $3 >= 0
      ReadINIStr $6 "$BooksCleanupReview" "target$3" "can_remove"
      ${If} $6 != "True"
        IntOp $7 $4 & 0xF000
        IntOp $8 $5 & 0xF000
        ${If} $7 = 0x2000
          ${NSD_Return} 1
        ${EndIf}
      ${EndIf}
    ${EndIf}
  ${EndIf}
  ${If} $1 == -101
    System::Call '*$2(p,p,i,i.r3,i,i.r4,i.r5)'
    ${If} $3 >= 0
      ReadINIStr $4 "$BooksCleanupReview" "target$3" "path"
      ReadINIStr $5 "$BooksCleanupReview" "target$3" "resolved_path"
      ReadINIStr $6 "$BooksCleanupReview" "target$3" "display_role"
      ReadINIStr $7 "$BooksCleanupReview" "target$3" "bytes"
      ReadINIStr $8 "$BooksCleanupReview" "target$3" "state"
      ReadINIStr $9 "$BooksCleanupReview" "target$3" "reason"
      ${If} $9 == ""
        StrCpy $9 $8
      ${EndIf}
      ${NSD_SetText} $BooksCleanupDetails "Location: $4$\r$\nResolved location / aliases: $5$\r$\nContents: $6$\r$\nSize: $7 bytes$\r$\nAction / reason: $9"
    ${EndIf}
  ${EndIf}
  Return
FunctionEnd

Function un.BooksDataLeave
  ${NSD_GetState} $BooksNewRadio $0
  ${If} $0 != ${BST_CHECKED}
    StrCpy $BooksCleanupMode "keep"
    Return
  ${EndIf}
  StrCpy $BooksCleanupMode "remove"
  Call un.BooksNewRequest
  WriteINIStr "$BooksRequest" "request" "action" "plan-cleanup"
  ReadINIStr $0 "$BooksCleanupReview" "result" "ownership_path"
  WriteINIStr "$BooksRequest" "request" "ownership_path" "$0"
  ReadINIStr $0 "$BooksCleanupReview" "result" "ownership_sha256"
  WriteINIStr "$BooksRequest" "request" "ownership_sha256" "$0"
  ReadINIStr $0 "$BooksCleanupReview" "result" "source_review"
  WriteINIStr "$BooksRequest" "request" "source_review" "$0"
  ReadINIStr $0 "$BooksCleanupReview" "result" "source_review_sha256"
  WriteINIStr "$BooksRequest" "request" "source_review_sha256" "$0"
  ReadINIStr $0 "$BooksCleanupReview" "result" "authority_bootstrap"
  WriteINIStr "$BooksRequest" "request" "authority_bootstrap" "$0"
  ReadINIStr $4 "$BooksCleanupReview" "result" "count"
  StrCpy $5 0
  StrCpy $7 0
  ${DoWhile} $5 < $4
    SendMessage $BooksCleanupList 0x102C $5 0xF000 $6
    ${If} $6 = 0x2000
      ReadINIStr $0 "$BooksCleanupReview" "target$5" "can_remove"
      ${If} $0 != "True"
        Abort
      ${EndIf}
      ReadINIStr $0 "$BooksCleanupReview" "target$5" "path"
      WriteINIStr "$BooksRequest" "selected$7" "path" "$0"
      IntOp $7 $7 + 1
    ${EndIf}
    IntOp $5 $5 + 1
  ${Loop}
  WriteINIStr "$BooksRequest" "request" "selected_count" "$7"
  Call un.BooksRunHelper
  ${If} $2 != "1"
    ReadINIStr $0 "$BooksResponse" "result" "message"
    MessageBox MB_OK|MB_ICONEXCLAMATION "$0"
    Abort
  ${EndIf}
  ReadINIStr $BooksCleanupPlan "$BooksResponse" "result" "plan_path"
  ReadINIStr $BooksCleanupSha "$BooksResponse" "result" "plan_sha256"
  ReadINIStr $BooksCleanupBytes "$BooksResponse" "result" "bytes"
  ReadINIStr $BooksCleanupWarning "$BooksResponse" "result" "warning"
  StrCpy $BooksCleanupSelection $BooksResponse
FunctionEnd

Function un.BooksConfirmPage
  ${If} ${isUpdated}
    Abort
  ${EndIf}
  ${If} $BooksCleanupMode != "remove"
    StrCpy $BooksCleanupResult ""
    Abort
  ${EndIf}
  !insertmacro MUI_HEADER_TEXT "Delete selected data" "Review the exact selected locations before permanent deletion."
  nsDialogs::Create 1018
  Pop $BooksDialog
  StrCpy $BooksTipWindow ""
  ${NSD_CreateLabel} 0 0 100% 12% "Uninstall Books Arranger and permanently delete the selected data."
  Pop $0
  ${NSD_CreateLabel} 0 14% 100% 21% "$BooksCleanupWarning"
  Pop $0
  nsDialogs::CreateControl "EDIT" "${DEFAULT_STYLES}|${WS_TABSTOP}|${ES_MULTILINE}|${ES_AUTOVSCROLL}|${ES_READONLY}|${WS_VSCROLL}|${WS_HSCROLL}" "${WS_EX_CLIENTEDGE}" 0 36% 100% 40% ""
  Pop $BooksCleanupLocations
  ReadINIStr $4 "$BooksCleanupSelection" "result" "count"
  StrCpy $5 0
  ${DoWhile} $5 < $4
    ReadINIStr $6 "$BooksCleanupSelection" "selected$5" "path"
    ReadINIStr $7 "$BooksCleanupSelection" "selected$5" "resolved_path"
    SendMessage $BooksCleanupLocations ${EM_SETSEL} -1 -1
    SendMessage $BooksCleanupLocations ${EM_REPLACESEL} 0 "STR:$6$\r$\nResolved: $7$\r$\n$\r$\n"
    IntOp $5 $5 + 1
  ${Loop}
  ${NSD_CreateLabel} 0 78% 100% 8% "Selected removable total: $BooksCleanupBytes bytes."
  Pop $0
  ${NSD_CreateCheckbox} 0 88% 100% 12% "I want to permanently delete the selected data."
  Pop $BooksConfirm
  ReadINIStr $0 "$BooksCleanupSelection" "result" "forfeits_rollback"
  ${If} $0 == "1"
    ${NSD_SetText} $BooksConfirm "Delete selected data, including the rollback copy."
  ${EndIf}
  ${NSD_Uncheck} $BooksConfirm
  ${NSD_OnClick} $BooksConfirm un.BooksConfirmChanged
  GetDlgItem $0 $HWNDPARENT 1
  SendMessage $0 ${WM_SETTEXT} 0 "STR:Uninstall"
  EnableWindow $0 0
  !insertmacro BooksTip $BooksConfirm "Confirm permanent deletion of the listed selected data."
  nsDialogs::Show
FunctionEnd

Function un.BooksConfirmChanged
  ${NSD_GetState} $BooksConfirm $0
  GetDlgItem $1 $HWNDPARENT 1
  ${If} $0 == ${BST_CHECKED}
    EnableWindow $1 1
  ${Else}
    EnableWindow $1 0
  ${EndIf}
FunctionEnd

Function un.BooksConfirmLeave
  ${NSD_GetState} $BooksConfirm $0
  ${If} $0 != ${BST_CHECKED}
    Abort
  ${EndIf}
FunctionEnd

Function un.BooksExecuteCleanup
  ${If} ${isUpdated}
    Return
  ${EndIf}
  ${If} $BooksCleanupMode != "remove"
    DetailPrint "Your data was kept."
    Return
  ${EndIf}
  Call un.BooksNewRequest
  WriteINIStr "$BooksRequest" "request" "action" "execute-cleanup"
  WriteINIStr "$BooksRequest" "request" "plan_path" "$BooksCleanupPlan"
  WriteINIStr "$BooksRequest" "request" "plan_sha256" "$BooksCleanupSha"
  WriteINIStr "$BooksRequest" "request" "confirmed" "1"
  WriteINIStr "$BooksRequest" "request" "process_name" "${BOOKS_LIFECYCLE_PROCESS_NAME}"
  Call un.BooksRunHelper
  StrCpy $BooksCleanupResult $BooksResponse
  ${If} $2 != "1"
    DetailPrint "Some selected data could not be removed. See retained paths on the result page."
    ; Do not let stock registry/shortcut/package removal proceed after a
    ; partially committed registry cleanup transaction.
    Call un.BooksRefuse
  ${EndIf}
  ReadINIStr $0 "$BooksResponse" "result" "removed_bytes"
  DetailPrint "Selected data files removed: $0 bytes. Unselected and protected locations were kept."
FunctionEnd

Function un.BooksResultPage
  ${If} ${isUpdated}
    Abort
  ${EndIf}
  !insertmacro MUI_HEADER_TEXT "Books Arranger data" "Review exactly what was removed and what remains."
  nsDialogs::Create 1018
  Pop $BooksDialog
  nsDialogs::CreateControl "EDIT" "${DEFAULT_STYLES}|${WS_TABSTOP}|${ES_MULTILINE}|${ES_AUTOVSCROLL}|${ES_READONLY}|${WS_VSCROLL}|${WS_HSCROLL}" "${WS_EX_CLIENTEDGE}" 0 0 100% 100% ""
  Pop $BooksCleanupDetails
  ${If} $BooksCleanupResult == ""
    ${NSD_SetText} $BooksCleanupDetails "Your data was kept."
  ${Else}
    ReadINIStr $0 "$BooksCleanupResult" "result" "removed_files"
    ReadINIStr $1 "$BooksCleanupResult" "result" "removed_bytes"
    ReadINIStr $2 "$BooksCleanupResult" "result" "removed_directories"
    ${NSD_SetText} $BooksCleanupDetails "Removed: $0 files, $1 bytes, $2 directories.$\r$\n"
    ReadINIStr $0 "$BooksCleanupResult" "result" "message"
    SendMessage $BooksCleanupDetails ${EM_SETSEL} -1 -1
    SendMessage $BooksCleanupDetails ${EM_REPLACESEL} 0 "STR:$0$\r$\n"
    ReadINIStr $4 "$BooksCleanupResult" "result" "remaining_count"
    StrCpy $5 0
    ${DoWhile} $5 < $4
      ReadINIStr $6 "$BooksCleanupResult" "remaining$5" "path"
      ReadINIStr $7 "$BooksCleanupResult" "remaining$5" "reason"
      ReadINIStr $8 "$BooksCleanupResult" "remaining$5" "bytes"
      ${If} $8 == ""
        StrCpy $8 "Unknown"
      ${Else}
        StrCpy $8 "$8 bytes"
      ${EndIf}
      SendMessage $BooksCleanupDetails ${EM_SETSEL} -1 -1
      SendMessage $BooksCleanupDetails ${EM_REPLACESEL} 0 "STR:Retained location: $6$\r$\n$8$\r$\n$7$\r$\n"
      IntOp $5 $5 + 1
    ${Loop}
  ${EndIf}
  ReadINIStr $4 "$BooksCleanupReview" "result" "count"
  StrCpy $5 0
  ${DoWhile} $5 < $4
    ReadINIStr $6 "$BooksCleanupReview" "target$5" "path"
    ${If} ${FileExists} "$6"
      ReadINIStr $7 "$BooksCleanupReview" "target$5" "state"
      ReadINIStr $8 "$BooksCleanupReview" "target$5" "reason"
      SendMessage $BooksCleanupDetails ${EM_SETSEL} -1 -1
      SendMessage $BooksCleanupDetails ${EM_REPLACESEL} 0 "STR:Retained location: $6$\r$\nReason: $7 / $8$\r$\n"
    ${EndIf}
    IntOp $5 $5 + 1
  ${Loop}
  nsDialogs::Show
FunctionEnd

!macro customUnWelcomePage
  UninstPage custom un.BooksDataPage un.BooksDataLeave
  UninstPage custom un.BooksConfirmPage un.BooksConfirmLeave
!macroend
!macro customUnInstall
  Call un.BooksExecuteCleanup
!macroend
!macro customRemoveFiles
  ; Exact native receipts replace stock recursive $INSTDIR removal entirely.
  ReadINIStr $0 "$BooksCleanupResult" "result" "package_removed"
  ${If} $0 != "1"
  Call un.BooksNewRequest
  ${GetParent} "$INSTDIR" $0
  WriteINIStr "$BooksRequest" "request" "action" "remove-package"
  WriteINIStr "$BooksRequest" "request" "application_dir" "$INSTDIR"
  WriteINIStr "$BooksRequest" "request" "bootstrap" "$0\books-arranger-installation.json"
  Call un.BooksRunHelper
  ${If} $2 != "1"
    Call un.BooksRefuse
  ${EndIf}
  ${EndIf}
!macroend
!macro customUninstallPage
  UninstPage custom un.BooksResultPage
!macroend
!endif
!endif
