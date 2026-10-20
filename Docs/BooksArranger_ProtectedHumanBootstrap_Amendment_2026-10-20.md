# Disabled human bootstrap — explicit trust amendment and CLR/ACL measurement proposal

2026-10-20. Ender DESIGN ONLY under ruling623c14a0c5c2a860b77ac0105091a942193dea068d4341dae61338ff15181baa /commitc5f50a30d746e7a8e4290d34fd48a327b6abf16d. No code/native/process/measurement/admin/UAC/global/ACL mutation/build/RNG action. Sources31 untouched. This proposal is not execution or deployment authority.

**Finite trust chain.** Trusted installed WindowsPowerShell5.1/.NET, freshly eligible protected ProgramFiles ancestry, literal independently reviewed current-source artifact+boundedmanifest bytes and an exclusively human-controlled privileged quiescent operation are the pre-native trust base. ONE absent fixed leaf C:/Program Files/BooksArranger-QA-v2 is created birth-protected. Copy disabled bytes only: same-held boundedmanifest/hash+parse and sources, no-replace files, explicit birthACL, bounded110files/8MiB exact installclosure and separate93files/4MiB runtimeclosure, flush/finalclose/readback/owner/DACL/stream/link/member checks. No code executes during copying, globalhooks unchanged, registrationdisabled, no source removal/partialroot cleanup/adoption. Existing target or privilegedwriter uncertainty STOP. Directory.CreateDirectory(...DirectorySecurity) is NOT atomicabsence/CAS. No protection against an uncooperative administrator is claimed.

**Property deliberately given up before first native verifier.** The human operation does NOT prove native-held full128/birth/ancestor identity or native object continuity. Framework/hash/ACL/path/quiescence evidence is trusted for this initial disabledcopy; never relabel it originalnativecap authority or sandbox/immutability. The future first protected native operation must independently reacquire/check complete installed objects+ancestry/full128/volume/birth/DACL/defaultstreams/link1/bytes before ANY enablement/QA. It needs its own reviewed fixed executable/argv/inputpins and observable originalowner/EOF/checkedclose result. A new writable elevated helper cannot install/authenticate itself. If this explicit reduced human trust is declined, STOP pending an already trusted primitive, not another installer.

## Literal READONLY measurement packet — NOT INVOKED

Purpose: determine actual installed constructoravailability and in-memory normalized birthACL masks before preparing any human copy recipe. No FileStream or Directory creation call is made: reflection obtains MethodInfo/ConstructorInfo only. Two in-memory securitydescriptors/6rules are built and inspected; no Get-Acl/Set-Acl/file/registry/token/process probe, child launch, elevation, Add-Type, policy/security/provider change or external command in the payload. Literal installed PS executable; inherited trustedWindows/CLR startup, no profile. No artifact/root/global path is read or written by this payload.

Expected output: ONE nonauthoritative JSON schema books-clr-acl-measurement-v1, PS/CLR descriptiveversions, exact2overloadbooleans,2ACLobjects(owner/protected/3ACE SID+rawmask+inheritance+propagation+allow/inherited), elapsed_ms and expected_contract_match. Expected OwnerAdmin/protected=true; SYSTEM/Admin masks0x1f01ff, UsersReadAndExecute normalized with Synchronize0x1200a9; fileinheritance0, directoryOICI3, propagation0, explicitAllow. Actual values UNMEASURED; no normalization permits additionalrights. Unsupported CLR/overload or mismatchedflags/masks/owner refuses exit2, never silently chooses another constructor. Success requires actual originaltool exit0+bounded JSON and independent expectedfield checks; JSON alone is not a nativeclosure proof.

Bounds: exactly2reflectionlookups,2descriptors,6ACE additions and atmost6ACE outputs; output<=16384UTF8bytes/error<=512messagechars; success elapsed<=5000ms. Stopwatch is a successpredicate, NOT forced termination. The executable's trustedstartup/CLR calls/stdio can block; no directtool hardtimeout is claimed. This proposes an ORDINARY fixed read-only metadata tool invocation: accept only actual originaltool terminalstatus/stdout as observation, with NO ownedJob/600000ms/nativeclosure guarantee. Senua must separately rule that this finite observation is sufficient. No ownership wrapper/framework is required or proposed. If the deployedguard rejects the exact ordinary invocation, STOP/report that boundary; do not bypass it or recursively build a launcher. Do not fabricate timeout in exec_command schema or use yield_time_ms as executionlimit. Proposed toolenvelope is exec_command with exact command below, cwd C:/Antigravity Projects/Studio Illuminati, shell defaultPowerShell, yield_time_ms10000 and max_output_tokens2500; these last2 govern observation/output only. This document authorizes no process.

PowerShell source SHA256 (UTF8/LF, including finalnewline): **c31e80ef848ce07b6f6d5e14819d18035dea019216aa7dd4021c7a467bb2e495**. Exact prospective defaultPowerShell command:

~~~powershell
& 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe' -NoLogo -NoProfile -NonInteractive -Command @'
$ErrorActionPreference='Stop'
$clock=[Diagnostics.Stopwatch]::StartNew()
try {
 $dc=[IO.Directory].GetMethod('CreateDirectory',[Type[]]@([string],[Security.AccessControl.DirectorySecurity]))
 $fc=[IO.FileStream].GetConstructor([Type[]]@([string],[IO.FileMode],[Security.AccessControl.FileSystemRights],[IO.FileShare],[int],[IO.FileOptions],[Security.AccessControl.FileSecurity]))
 $admin=[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')
 $system=[Security.Principal.SecurityIdentifier]::new('S-1-5-18')
 $users=[Security.Principal.SecurityIdentifier]::new('S-1-5-32-545')
 function Measure-Acl([bool]$directory) {
  $s=if($directory){[Security.AccessControl.DirectorySecurity]::new()}else{[Security.AccessControl.FileSecurity]::new()}
  $s.SetOwner($admin);$s.SetAccessRuleProtection($true,$false)
  $inherit=if($directory){[Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'}else{[Security.AccessControl.InheritanceFlags]::None}
  foreach($sid in @($system,$admin,$users)) {
   $rights=if($sid.Value -eq $users.Value){[Security.AccessControl.FileSystemRights]::ReadAndExecute}else{[Security.AccessControl.FileSystemRights]::FullControl}
   $rule=[Security.AccessControl.FileSystemAccessRule]::new($sid,$rights,$inherit,[Security.AccessControl.PropagationFlags]::None,[Security.AccessControl.AccessControlType]::Allow)
   $s.AddAccessRule($rule)
  }
  $rules=@($s.GetAccessRules($true,$false,[Security.Principal.SecurityIdentifier]))
  if($rules.Count -gt 3){throw 'Unexpected in-memory ACE count'}
  $rows=@();$matches=$rules.Count -eq 3
  foreach($r in $rules) {
   $mask=[uint32][int]$r.FileSystemRights
   $want=if($r.IdentityReference.Value -eq $users.Value){0x1200a9}else{0x1f01ff}
   $ok=$r.IdentityReference.Value -in @($system.Value,$admin.Value,$users.Value) -and $mask -eq $want -and $r.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow -and -not $r.IsInherited -and $r.InheritanceFlags -eq $inherit -and $r.PropagationFlags -eq [Security.AccessControl.PropagationFlags]::None
   $matches=$matches -and $ok
   $rows+=@{sid=$r.IdentityReference.Value;mask=$mask;inheritance=[int]$r.InheritanceFlags;propagation=[int]$r.PropagationFlags;allow=$r.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow;inherited=$r.IsInherited}
  }
  return @{owner=$s.GetOwner([Security.Principal.SecurityIdentifier]).Value;protected=$s.AreAccessRulesProtected;aces=$rows;expected_masks_match=$matches}
 }
 $d=Measure-Acl $true;$f=Measure-Acl $false
 $clock.Stop()
 $ok=$PSVersionTable.PSVersion.Major -eq 5 -and $PSVersionTable.PSVersion.Minor -eq 1 -and $null -ne $dc -and $null -ne $fc -and $d.expected_masks_match -and $f.expected_masks_match -and $d.owner -eq $admin.Value -and $f.owner -eq $admin.Value -and $d.protected -and $f.protected -and $clock.ElapsedMilliseconds -le 5000
 $data=@{schema='books-clr-acl-measurement-v1';authoritative=$false;ps_version=$PSVersionTable.PSVersion.ToString();ps_edition=$PSVersionTable.PSEdition;clr_version=[Environment]::Version.ToString();image_runtime_version=[object].Assembly.ImageRuntimeVersion;is_64bit_process=[Environment]::Is64BitProcess;directory_security_overload_available=$null -ne $dc;filestream_security_ctor_available=$null -ne $fc;directory_acl=$d;file_acl=$f;elapsed_ms=$clock.ElapsedMilliseconds;expected_contract_match=$ok}
 $json=$data|ConvertTo-Json -Depth 6 -Compress
 if([Text.Encoding]::UTF8.GetByteCount($json) -gt 16384){throw 'Measurement stdout quota'}
 [Console]::Out.WriteLine($json)
 if(-not $ok){exit 2}
 exit 0
} catch {
 $message=$_.Exception.Message
 if($message.Length -gt 512){$message=$message.Substring(0,512)}
 [Console]::Error.WriteLine('CLR/ACL measurement refused: '+$message)
 exit 2
}
'@
~~~

## Finite controls / later gates

| Negative / future disposable fault | Required outcome |
|---|---|
| WrongPS/CLR, missing exact overload, extra/differentACE or Synchronize/owner/inheritance drift | Nonmatching measurement/exit2; no create/copy |
| Getter/malformed/oversize/duplicate measurement JSON or noactualexit0/over5s | No accepted measurement; no nativeclosure inference |
| Existing/raced target, absent adminquiescence, changed parent eligibility | Refuse; no adoption/repair |
| Swapped manifest/source, quota/member/dir/stream/link mismatch | Disabled preserved evidence; no execute/globalchange |
| Disposable birthACL/copy/write/flush/finalclose/reopen/hash/readback failure | Fail disabled; never mark nativeproof/canonicalQA |
| Firstprotected verifier missing/changed object/ACL/stream/hash/ID/ancestor | No enablement/QA; preserve partialroot/globalbaseline |
| Globalbaseline changed or rollbackcurrent differs from approvedcandidate | No manualoverwrite; re-review, no automaticCAS/delete |

Next SOURCE-only phase after independent ruling: prepare fixed disabledliteralrecipe+focused disposable fault tests under exact reviewedtarget/owner; measure constructor/ACL packet only after separate invocationapproval. Fresh parenteligibility, latest complete artifact/build proof, exact manifests and fresh opaque fallback-equivalent globalcandidate/rollbackbytes remain future gates. Audio owns native verifier design; Sources owns existing launcher/dispatch/watchdog graph. Human deployment request occurs only after concrete reviewed artifacts/measurement/fault evidence exist. Original NORESULT/UNKNOWNruns stay unchanged. Session scratch preserved.
