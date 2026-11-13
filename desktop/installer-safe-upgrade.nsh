; Expanded only AFTER stock installUtil defines uninstallOldVersion, before
; its first call in installSection. Never execute an old uninstaller binary.
!define BOOKS_SAFE_LEGACY_OVERRIDE
!macroundef uninstallOldVersion
!macro uninstallOldVersion ROOT_KEY
  ReadRegStr $R1 ${ROOT_KEY} "${UNINSTALL_REGISTRY_KEY}" "InstallLocation"
  ${If} $R1 != ""
    ReadRegStr $R2 ${ROOT_KEY} "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
    Call BooksNewRequest
    ${If} $R2 == "0.27.0"
      WriteINIStr "$BooksRequest" "request" "action" "retire-legacy-package"
    ${Else}
      WriteINIStr "$BooksRequest" "request" "action" "retire-owned-package"
    ${EndIf}
    WriteINIStr "$BooksRequest" "request" "installation_dir" "$R1"
    WriteINIStr "$BooksRequest" "request" "version" "$R2"
    WriteINIStr "$BooksRequest" "request" "process_name" "${BOOKS_LIFECYCLE_PROCESS_NAME}"
    Call BooksRunHelper
    ${If} $2 != "1"
      Call BooksRefuse
    ${EndIf}
    ReadINIStr $BooksRetainedPackage "$BooksResponse" "result" "receipt"
    ReadINIStr $BooksRetainedPackageSha "$BooksResponse" "result" "receipt_sha256"
  ${EndIf}
  !ifdef BOOKS_EXACT_APP_EXTRACTION
    ${If} $BooksApplicationStagePlan == ""
      StrCpy $BooksFinalInstallDir $INSTDIR
      Call BooksPrepareApplicationStage
    ${EndIf}
    ; installSection's SetOutPath happens BEFORE installApplicationFiles. It
    ; must also address the private stage, never create/write the final name.
    StrCpy $INSTDIR $BooksApplicationStage
  !endif
  StrCpy $R0 0
  ClearErrors
!macroend

!ifmacrodef installApplicationFiles
  !define BOOKS_EXACT_APP_EXTRACTION
  !macroundef installApplicationFiles
  !macro installApplicationFiles
    ; Extract solely into a new private sibling, then verify/publish without
    ; replacement. Stock registry and shortcuts see only the FINAL directory.
    ${If} $BooksApplicationStagePlan == ""
      StrCpy $BooksFinalInstallDir $INSTDIR
      Call BooksPrepareApplicationStage
    ${EndIf}
    StrCpy $INSTDIR $BooksApplicationStage
    SetOutPath $INSTDIR
    !ifdef APP_BUILD_DIR
      File /r "${APP_BUILD_DIR}\*.*"
    !else
      !ifdef APP_PACKAGE_URL
        !error "Books Arranger requires a complete pinned offline package"
      !endif
      !insertmacro extractEmbeddedAppPackage
    !endif
    File "/oname=${UNINSTALL_FILENAME}" "${UNINSTALLER_OUT_FILE}"
    !ifdef BOOKS_INSTALLER_ICON
      File /oname=uninstallerIcon.ico "${BOOKS_INSTALLER_ICON}"
    !endif
    Call BooksPublishApplicationStage
    StrCpy $INSTDIR $BooksFinalInstallDir
    SetOutPath $INSTDIR
  !macroend
!endif
