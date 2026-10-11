"""Local neutral artwork rendered with Windows Unicode text; no published-cover claim."""
import ctypes,os,struct,zlib
from ctypes import wintypes as W

MAX_TEXT=8192

def neutral_cover(title, authors=()):
    if not isinstance(title,str) or not title.strip() or len(title)>MAX_TEXT or '\0' in title:
        raise ValueError('Neutral cover needs a bounded approved display title')
    if not isinstance(authors,(list,tuple)) or any(not isinstance(a,str) or not a.strip() or '\0' in a for a in authors):
        raise ValueError('Neutral cover authors must be verified full credit strings')
    credit=' · '.join(authors)
    if len(credit)>MAX_TEXT:raise ValueError('Neutral cover credits exceed the text bound')
    if os.name!='nt':raise ValueError('Local Unicode neutral-cover renderer requires Windows')
    g=ctypes.WinDLL('gdi32',use_last_error=True);u=ctypes.WinDLL('user32',use_last_error=True)
    class Header(ctypes.Structure):
        _fields_=[('size',W.DWORD),('width',W.LONG),('height',W.LONG),('planes',W.WORD),('bits',W.WORD),('compression',W.DWORD),('image_size',W.DWORD),('x',W.LONG),('y',W.LONG),('used',W.DWORD),('important',W.DWORD)]
    class Info(ctypes.Structure):_fields_=[('header',Header),('colors',W.DWORD*3)]
    def bind(lib,name,args,result):
        fn=getattr(lib,name);fn.argtypes=args;fn.restype=result;return fn
    dcnew=bind(g,'CreateCompatibleDC',[W.HDC],W.HDC)
    dibnew=bind(g,'CreateDIBSection',[W.HDC,ctypes.POINTER(Info),W.UINT,ctypes.POINTER(ctypes.c_void_p),W.HANDLE,W.DWORD],W.HBITMAP)
    select=bind(g,'SelectObject',[W.HDC,W.HGDIOBJ],W.HGDIOBJ)
    delete=bind(g,'DeleteObject',[W.HGDIOBJ],W.BOOL)
    deletedc=bind(g,'DeleteDC',[W.HDC],W.BOOL)
    fontnew=bind(g,'CreateFontW',[ctypes.c_int]*5+[W.DWORD]*8+[W.LPCWSTR],W.HFONT)
    color=bind(g,'SetTextColor',[W.HDC,W.DWORD],W.DWORD)
    mode=bind(g,'SetBkMode',[W.HDC,ctypes.c_int],ctypes.c_int)
    draw=bind(u,'DrawTextW',[W.HDC,W.LPCWSTR,ctypes.c_int,ctypes.POINTER(W.RECT),W.UINT],ctypes.c_int)
    glyph=bind(g,'GetGlyphIndicesW',[W.HDC,W.LPCWSTR,ctypes.c_int,ctypes.POINTER(W.WORD),W.DWORD],W.DWORD)
    dc=dcnew(None);bitmap=None;oldbitmap=None;fonts=[];oldfont=None
    if not dc:raise ValueError('Neutral-cover drawing context unavailable')
    try:
        info=Info();info.header=Header(40,1200,-1200,1,32,0,1200*1200*4,0,0,0,0)
        pixels=ctypes.c_void_p();bitmap=dibnew(dc,ctypes.byref(info),0,ctypes.byref(pixels),None,0)
        if not bitmap or not pixels.value:raise ValueError('Neutral-cover pixel allocation failed')
        oldbitmap=select(dc,bitmap)
        if not oldbitmap or oldbitmap==ctypes.c_void_p(-1).value:raise ValueError('Neutral-cover bitmap selection failed')
        # BGRA pixels, opaque blue-gray background; no external image decoder.
        background=bytes((0x2d,0x21,0x18,0xff))*(1200*1200)
        ctypes.memmove(pixels,background,len(background));mode(dc,1)
        def make(size,text):
            face=fontnew(-size,0,0,0,400,0,0,0,1,0,0,4,0,'Segoe UI')
            if not face:raise ValueError('Installed Unicode cover font is unavailable')
            fonts.append(face)
            nonlocal oldfont
            previous=select(dc,face)
            if not previous or previous==ctypes.c_void_p(-1).value:raise ValueError('Neutral-cover font selection failed')
            if oldfont is None:oldfont=previous
            glyph_text=''.join(character for character in text if not character.isspace())
            count=len(glyph_text.encode('utf-16-le'))//2
            if count:
                indices=(W.WORD*count)()
                if glyph(dc,glyph_text,count,indices,1)==0xffffffff or any(value==0xffff for value in indices):
                    raise ValueError('Installed cover font cannot represent all approved text')
            rectangle=W.RECT(96,0,1104,0)
            height=draw(dc,text,-1,ctypes.byref(rectangle),0x400|0x10|0x800|0x2000) if text else 0
            if text and height<=0:raise ValueError('Neutral cover text cannot be measured')
            return face,height,rectangle.right<=1104
        chosen=None
        for size in range(80,39,-2):
            titlefont,titleheight,titlefits=make(size,title);authorfont,authorheight,authorfits=make(max(32,round(42*size/80)),credit)
            height=titleheight+(48+authorheight if credit else 0)
            if height<=1008 and titlefits and authorfits:chosen=(titlefont,titleheight,authorfont,authorheight,height);break
        if chosen is None:raise ValueError('Approved cover text cannot fit without truncation')
        titlefont,titleheight,authorfont,authorheight,height=chosen;y=96+(1008-height)//2
        for text,face,h,rgb in ((title,titlefont,titleheight,0xf7f5f3),(credit,authorfont,authorheight,0xdacfc5)):
            if not text:continue
            select(dc,face);color(dc,rgb)
            rectangle=W.RECT(96,y,1104,y+h)
            actual=draw(dc,text,-1,ctypes.byref(rectangle),0x10|0x800|0x2000)
            if actual<=0 or actual>h:raise ValueError('Neutral-cover text exceeded its measured fit')
            y+=h+48
        raw=ctypes.string_at(pixels,1200*1200*4)
        rows=[]
        for y in range(1200):
            row=raw[y*4800:(y+1)*4800]
            rgb=bytearray(3600);rgb[0::3]=row[2::4];rgb[1::3]=row[1::4];rgb[2::3]=row[0::4]
            rows.append(b'\0'+rgb)
        def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
        data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1200,1200,8,2,0,0,0))+chunk(b'sRGB',b'\0')+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')
        if len(data)>8*1024*1024:raise ValueError('Neutral cover exceeds the artwork byte limit')
        return {'bytes':data,'kind':'neutral','basis':'Generated locally from approved title and full author credits; not published artwork',
                'title':title,'authors':list(authors),'width':1200,'height':1200}
    finally:
        if oldfont:select(dc,oldfont)
        if oldbitmap:select(dc,oldbitmap)
        for face in fonts:delete(face)
        if bitmap:delete(bitmap)
        deletedc(dc)
