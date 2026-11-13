"""Actual NSIS controls on a private, noninteractive Windows desktop.

No SwitchDesktop/foreground activation, product registry, or live application.
"""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import struct
import subprocess
import time


class NativeProcess:
    def __init__(self,command,environment,desktop):
        class Startup(c.Structure):
            _fields_=[('cb',w.DWORD),('reserved',w.LPWSTR),('desktop',w.LPWSTR),('title',w.LPWSTR),
                ('x',w.DWORD),('y',w.DWORD),('width',w.DWORD),('height',w.DWORD),('charsx',w.DWORD),
                ('charsy',w.DWORD),('fill',w.DWORD),('flags',w.DWORD),('show',w.WORD),('reserved2',w.WORD),
                ('reservedptr',c.c_void_p),('stdin',w.HANDLE),('stdout',w.HANDLE),('stderr',w.HANDLE)]
        class Info(c.Structure):_fields_=[('process',w.HANDLE),('thread',w.HANDLE),('pid',w.DWORD),('tid',w.DWORD)]
        self.kernel=c.WinDLL('kernel32',use_last_error=True);info=Info();startup=Startup();startup.cb=c.sizeof(startup);startup.desktop=desktop
        self.kernel.CreateProcessW.argtypes=[w.LPCWSTR,w.LPWSTR,c.c_void_p,c.c_void_p,w.BOOL,w.DWORD,c.c_void_p,w.LPCWSTR,c.POINTER(Startup),c.POINTER(Info)]
        env=c.create_unicode_buffer('\0'.join(key+'='+value for key,value in sorted(environment.items(),key=lambda item:item[0].upper()))+'\0\0')
        if not self.kernel.CreateProcessW(None,c.create_unicode_buffer(command),None,None,False,0x400,env,None,c.byref(startup),c.byref(info)):
            raise c.WinError(c.get_last_error())
        self.handle=info.process;self.pid=info.pid
        self.kernel.CloseHandle.argtypes=[w.HANDLE];self.kernel.CloseHandle(info.thread)
        self.kernel.GetExitCodeProcess.argtypes=[w.HANDLE,c.POINTER(w.DWORD)]
        self.kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD]
        self.kernel.TerminateProcess.argtypes=[w.HANDLE,w.UINT]
    def poll(self):
        code=w.DWORD()
        if not self.kernel.GetExitCodeProcess(self.handle,c.byref(code)):raise c.WinError(c.get_last_error())
        self.returncode=None if code.value==259 else code.value
        return self.returncode
    def wait(self,timeout):
        if self.kernel.WaitForSingleObject(self.handle,int(timeout*1000))==258:raise subprocess.TimeoutExpired('private NSIS fixture',timeout)
        return self.poll()
    def terminate(self):self.kernel.TerminateProcess(self.handle,125)
    def close(self):self.kernel.CloseHandle(self.handle)


def inspect_pages(executable, application_dir, environment, output):
    u=c.WinDLL('user32',use_last_error=True);k=c.WinDLL('kernel32',use_last_error=True)
    u.CreateDesktopW.argtypes=[w.LPCWSTR,w.LPCWSTR,c.c_void_p,w.DWORD,w.DWORD,c.c_void_p];u.CreateDesktopW.restype=w.HANDLE
    u.CloseDesktop.argtypes=[w.HANDLE];u.EnumDesktopWindows.argtypes=[w.HANDLE,c.c_void_p,w.LPARAM]
    u.SendMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];u.SendMessageW.restype=w.LPARAM
    u.SendMessageTimeoutW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM,w.UINT,w.UINT,c.POINTER(c.c_size_t)]
    u.SendMessageTimeoutW.restype=w.LPARAM
    def send(hwnd,message,first=0,second=0):
        result=c.c_size_t()
        if not u.SendMessageTimeoutW(hwnd,message,first,second,2,5000,c.byref(result)):
            raise AssertionError(('Private native control timed out',message,c.get_last_error()))
        return result.value
    u.SendMessageW=send
    u.IsWindowEnabled.argtypes=[w.HWND];u.IsWindowVisible.argtypes=[w.HWND]
    u.GetDlgItem.argtypes=[w.HWND,c.c_int];u.GetDlgItem.restype=w.HWND
    callback=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
    u.EnumChildWindows.argtypes=[w.HWND,c.c_void_p,w.LPARAM]
    u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
    u.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
    u.GetClassNameW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
    u.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
    k.CloseHandle.argtypes=[w.HANDLE]
    name='BooksLifecyclePrivate'+str(time.time_ns());desktop=u.CreateDesktopW(name,None,None,0,0x1ff,None)
    if not desktop:raise c.WinError(c.get_last_error())
    process=None
    try:
        command='"'+str(executable)+'" _?='+str(application_dir)
        process=NativeProcess(command,environment,'winsta0\\'+name)
        Path(output).with_suffix('.process.json').write_text(json.dumps(dict(desktop=name,pid=process.pid)))
        def windows():
            found=[]
            @callback
            def visit(hwnd,param):
                pid=w.DWORD();u.GetWindowThreadProcessId(hwnd,c.byref(pid))
                if pid.value==process.pid and u.IsWindowVisible(hwnd):found.append(hwnd)
                return True
            u.EnumDesktopWindows(desktop,visit,0);return found
        def children(parent):
            found=[]
            @callback
            def visit(hwnd,param):found.append(hwnd);return True
            u.EnumChildWindows(parent,visit,0);return found
        def title(hwnd):
            text=c.create_unicode_buffer(4096);u.GetWindowTextW(hwnd,text,4096)
            if not text.value and _class(u,hwnd).lower()=='edit':
                u.SendMessageW(hwnd,0x0d,4096,c.addressof(text))
            return text.value
        def wait(predicate):
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                value=predicate()
                if value:return value
                if process.poll() is not None:raise AssertionError(('NSIS exited early',process.returncode))
                time.sleep(.05)
            Path(output).with_suffix('.failure.json').write_text(json.dumps([
                dict(window=title(h),children=[title(x) for x in children(h)]) for h in windows()],indent=2))
            Path(output).with_suffix('.helper.json').write_text(json.dumps({str(p):p.read_bytes().decode('utf16' if p.read_bytes().startswith(b'\xff\xfe') else 'utf8',errors='replace') for p in Path(environment['TEMP']).rglob('books-*.ini')},indent=2))
            raise AssertionError('Private native page did not reach expected state')
        parent=wait(lambda:next((h for h in windows() if any(title(x)=='Keep my data' for x in children(h))),None))
        controls=children(parent);keep=next(h for h in controls if title(h)=='Keep my data')
        assert u.SendMessageW(keep,0xf0,0,0)==1,'Keep is not default'
        remove=next(h for h in controls if title(h)=='Remove Books Arranger data from selected locations')
        u.SendMessageW(remove,0xf5,0,0)
        table=next(h for h in controls if _class(u,h)=='SysListView32')
        header=u.SendMessageW(table,0x101f,0,0)
        assert u.SendMessageW(header,0x1200,0,0)==4,'Expected four review columns'
        # Send the checkbox state through memory owned by this private process.
        k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
        k.VirtualAllocEx.argtypes=[w.HANDLE,c.c_void_p,c.c_size_t,w.DWORD,w.DWORD];k.VirtualAllocEx.restype=c.c_void_p
        k.WriteProcessMemory.argtypes=[w.HANDLE,c.c_void_p,c.c_void_p,c.c_size_t,c.c_void_p]
        k.VirtualFreeEx.argtypes=[w.HANDLE,c.c_void_p,c.c_size_t,w.DWORD]
        handle=k.OpenProcess(0x38,False,process.pid);remote=k.VirtualAllocEx(handle,None,64,0x3000,4)
        try:
            value=c.create_string_buffer(struct.pack('<5I',8,0,0,0x2000,0xf000))
            assert k.WriteProcessMemory(handle,remote,value,len(value),None)
            u.SendMessageW(table,0x102b,0,remote)
            checked=u.SendMessageW(table,0x102c,0,0xf000)
            Path(output).with_suffix('.review.json').write_text(json.dumps(dict(checkbox_state=checked,visible_text=[title(x) for x in children(parent)]),indent=2))
            assert checked==0x2000,('Private review checkbox refused eligible row',checked)
            # Row 1 contains an unknown personal PDF and is visibly protected.
            u.SendMessageW(table,0x102b,1,remote)
            assert u.SendMessageW(table,0x102c,1,0xf000)==0x1000,'Protected row accepted a check'
            focus=c.create_string_buffer(struct.pack('<5I',8,1,0,3,3))
            assert k.WriteProcessMemory(handle,remote,focus,len(focus),None)
            u.SendMessageW(table,0x102b,1,remote)
            u.SendMessageW(table,0x100,0x20,0)
            assert u.SendMessageW(table,0x102c,1,0xf000)==0x1000,'Keyboard checked a protected row'
        finally:k.VirtualFreeEx(handle,remote,0,0x8000);k.CloseHandle(handle)
        u.PostMessageW(u.GetDlgItem(parent,1),0xf5,0,0)
        confirm=wait(lambda:next((h for h in children(parent) if title(h)=='I want to permanently delete the selected data.'),None))
        nextbutton=u.GetDlgItem(parent,1)
        assert not u.IsWindowEnabled(nextbutton),'Uninstall enabled without confirmation'
        assert any('Uninstall Books Arranger and permanently delete' in title(h) for h in children(parent))
        assert any('Resolved:' in title(h) for h in children(parent)),'Exact alias list is missing'
        assert title(nextbutton)=='Uninstall','Stock caption changed'
        u.SendMessageW(confirm,0xf5,0,0);assert u.IsWindowEnabled(nextbutton)
        u.SendMessageW(confirm,0xf5,0,0);assert not u.IsWindowEnabled(nextbutton)
        u.SendMessageW(confirm,0xf5,0,0);u.SendMessageW(nextbutton,0xf5,0,0)
        # Fixture-only cleanup finishes, then the actual result page is visible.
        wait(lambda:any(title(h)=='Uninstallation Complete' for h in children(parent)))
        u.PostMessageW(u.GetDlgItem(parent,1),0xf5,0,0)
        wait(lambda:any('Removed:' in title(h) for h in children(parent)))
        evidence=dict(private_desktop=name,desktop_switched=False,product_registration_written=False,
                      actual_native_pages=True,keep_default=True,columns=4,confirmation_disabled_until_checked=True,
                      exact_alias_list=True,stock_uninstall_caption=True,result_page_visible=True,
                      protected_mouse_and_keyboard_selection_refused=True,
                      visible_text=[title(h) for h in children(parent) if title(h)])
        Path(output).write_text(json.dumps(evidence,indent=2),encoding='utf8')
        close=u.GetDlgItem(parent,1)
        assert u.IsWindowEnabled(close),'Final Close is disabled'
        u.PostMessageW(parent,0x111,1,close)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            Path(output).with_suffix('.close.json').write_text(json.dumps([
                dict(window=title(h),children=[dict(text=title(x),id=u.GetDlgCtrlID(x),enabled=bool(u.IsWindowEnabled(x))) for x in children(h)]) for h in windows()],indent=2))
            raise
        evidence['normal_close_verified']=True
        Path(output).write_text(json.dumps(evidence,indent=2),encoding='utf8')
        return evidence
    finally:
        if process and process.poll() is None:
            # Close only our isolated fixture; no product process interaction.
            for hwnd in windows():u.PostMessageW(hwnd,0x10,0,0)
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
        if process:process.close()
        u.CloseDesktop(desktop)


def _class(user,hwnd):
    text=c.create_unicode_buffer(256);user.GetClassNameW(hwnd,text,256);return text.value
