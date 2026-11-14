; Opt-in diagnostic sink supplied by the reviewed launcher. Never overwrite.
!ifndef BOOKS_REFUSAL_INCLUDED
!define BOOKS_REFUSAL_INCLUDED
Var BooksRefusalEvidence
Var BooksRefusalHandle
Var BooksRefusalDirectory
Var BooksRefusalStatus
Var BooksRefusalSuffix
Var BooksRefusalIndex
Var BooksRefusalChar
Var BooksRefusalCode
Var BooksRefusalPath
Var BooksRefusalDetails
Var BooksRefusalType
Var BooksLastHelperAction
Var BooksLastHelperExit
Var BooksLastHelperOutput

!macro BooksRefusalSupport PREFIX
Function ${PREFIX}BooksPersistRefusal
  StrCpy $BooksRefusalStatus "disabled"
  ReadEnvStr $BooksRefusalEvidence "BOOKS_INSTALL_EVIDENCE"
  ${If} $BooksRefusalEvidence == ""
    Return
  ${EndIf}
  StrCpy $BooksRefusalStatus "failed"
  ; The operator retains every ancestor and this freshly created directory.
  ; Only the launcher's direct-root UUID namespace is an admissible sink.
  StrCpy $8 $BooksRefusalEvidence 35
  ${If} $8 != "I:\Books-Arranger-Install-Evidence-"
    Return
  ${EndIf}
  StrLen $8 $BooksRefusalEvidence
  ${If} $8 != 71
    Return
  ${EndIf}
  StrCpy $BooksRefusalSuffix $BooksRefusalEvidence "" 35
  StrCpy $BooksRefusalIndex 0
  ${DoWhile} $BooksRefusalIndex < 36
    StrCpy $BooksRefusalChar $BooksRefusalSuffix 1 $BooksRefusalIndex
    ${If} $BooksRefusalIndex == 8
    ${OrIf} $BooksRefusalIndex == 13
    ${OrIf} $BooksRefusalIndex == 18
    ${OrIf} $BooksRefusalIndex == 23
      ${If} $BooksRefusalChar != "-"
        Return
      ${EndIf}
    ${Else}
      StrCpy $7 0
      ${DoWhile} $7 < 16
        StrCpy $8 "0123456789abcdef" 1 $7
        ${If} $8 == $BooksRefusalChar
          ${ExitDo}
        ${EndIf}
        IntOp $7 $7 + 1
      ${Loop}
      ${If} $7 == 16
        Return
      ${EndIf}
    ${EndIf}
    IntOp $BooksRefusalIndex $BooksRefusalIndex + 1
  ${Loop}
  System::Call 'kernel32::GetFileAttributesW(w "$BooksRefusalEvidence") i .r8'
  ${If} $8 == -1
    Return
  ${EndIf}
  IntOp $9 $8 & 0x410
  ${If} $9 != 16
    Return
  ${EndIf}
  System::Call 'kernel32::CreateFileW(w "$BooksRefusalEvidence", i 0x81, i 1, p 0, i 3, i 0x02200000, p 0) p .r9'
  ${If} $9 == -1
    Return
  ${EndIf}
  StrCpy $BooksRefusalDirectory $9
  System::Alloc 52
  Pop $6
  ${If} $6 == 0
    System::Call 'kernel32::CloseHandle(p $BooksRefusalDirectory) i .r8'
    Return
  ${EndIf}
  System::Call 'kernel32::GetFileInformationByHandle(p $BooksRefusalDirectory, p r6) i .r8'
  System::Call '*$6(i .r7)'
  System::Free $6
  IntOp $7 $7 & 0x410
  ${If} $8 == 0
  ${OrIf} $7 != 16
    System::Call 'kernel32::CloseHandle(p $BooksRefusalDirectory) i .r8'
    Return
  ${EndIf}
  System::Call 'kernel32::GetFinalPathNameByHandleW(p $BooksRefusalDirectory, w .r8, i ${NSIS_MAX_STRLEN}, i 0) i .r7'
  ${If} $7 == 0
  ${OrIf} $7 >= ${NSIS_MAX_STRLEN}
  ${OrIf} $8 != "\\?\$BooksRefusalEvidence"
    System::Call 'kernel32::CloseHandle(p $BooksRefusalDirectory) i .r8'
    Return
  ${EndIf}
  ReadINIStr $BooksRefusalCode "$BooksResponse" "result" "code"
  ReadINIStr $BooksRefusalPath "$BooksResponse" "result" "path"
  ReadINIStr $BooksRefusalDetails "$BooksResponse" "result" "details"
  ReadINIStr $BooksRefusalType "$BooksResponse" "result" "exception_type"
  ; CREATE_NEW + OPEN_REPARSE_POINT: a prior result or raced leaf is kept.
  System::Call 'kernel32::CreateFileW(w "$BooksRefusalEvidence\installer-refusal.txt", i 0x40000000, i 1, p 0, i 1, i 0x00200000, p 0) p .r9'
  ${If} $9 == -1
    System::Call 'kernel32::CloseHandle(p $BooksRefusalDirectory) i .r8'
    Return
  ${EndIf}
  StrCpy $BooksRefusalHandle $9
  ClearErrors
  FileWriteUTF16LE /BOM $BooksRefusalHandle "schema=books-installer-refusal-v1$\r$\nmessage=$3$\r$\ncode=$BooksRefusalCode$\r$\nexception_type=$BooksRefusalType$\r$\ndetails=$BooksRefusalDetails$\r$\npath=$BooksRefusalPath$\r$\naction=$BooksLastHelperAction$\r$\nhelper_exit=$BooksLastHelperExit$\r$\nhelper_output=$BooksLastHelperOutput$\r$\n"
  ${IfNot} ${Errors}
    StrCpy $BooksRefusalStatus "written"
  ${EndIf}
  System::Call 'kernel32::FlushFileBuffers(p $BooksRefusalHandle) i .r8'
  ${If} $8 == 0
    StrCpy $BooksRefusalStatus "failed"
  ${EndIf}
  System::Call 'kernel32::CloseHandle(p $BooksRefusalHandle) i .r8'
  ${If} $8 == 0
    StrCpy $BooksRefusalStatus "failed"
  ${EndIf}
  System::Call 'kernel32::CloseHandle(p $BooksRefusalDirectory) i .r8'
  ${If} $8 == 0
    StrCpy $BooksRefusalStatus "failed"
  ${EndIf}
FunctionEnd
!macroend
!endif
