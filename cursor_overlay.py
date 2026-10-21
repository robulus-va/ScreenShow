import ctypes
from ctypes import wintypes
from pathlib import Path

from PIL import Image


CURSOR_RESOURCES = {
    "arrow": 32512,
    "ibeam": 32513,
    "wait": 32514,
    "cross": 32515,
    "uparrow": 32516,
    "sizenwse": 32642,
    "sizenesw": 32643,
    "sizewe": 32644,
    "sizens": 32645,
    "sizeall": 32646,
    "no": 32648,
    "hand": 32649,
    "appstarting": 32650,
    "help": 32651,
    "pin": 32671,
    "person": 32672,
}

DI_NORMAL = 0x0003
DIB_RGB_COLORS = 0
BI_RGB = 0
CURSOR_SHOWING = 0x0001

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HANDLE),
        ("ptScreenPos", wintypes.POINT),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HANDLE),
        ("hbmColor", wintypes.HANDLE),
    ]


class BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType", wintypes.LONG),
        ("bmWidth", wintypes.LONG),
        ("bmHeight", wintypes.LONG),
        ("bmWidthBytes", wintypes.LONG),
        ("bmPlanes", wintypes.WORD),
        ("bmBitsPixel", wintypes.WORD),
        ("bmBits", ctypes.c_void_p),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class RGBQUAD(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", wintypes.BYTE),
        ("rgbGreen", wintypes.BYTE),
        ("rgbRed", wintypes.BYTE),
        ("rgbReserved", wintypes.BYTE),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 1)]


user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.LoadCursorW.restype = wintypes.HANDLE
user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
user32.GetCursorInfo.restype = wintypes.BOOL
user32.GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ICONINFO)]
user32.GetIconInfo.restype = wintypes.BOOL
user32.DrawIconEx.argtypes = [
    wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.HANDLE,
    ctypes.c_int, ctypes.c_int, wintypes.UINT, wintypes.HBRUSH, wintypes.UINT,
]
user32.DrawIconEx.restype = wintypes.BOOL
gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
gdi32.GetObjectW.restype = ctypes.c_int
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC, ctypes.POINTER(BITMAPINFO), wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD,
]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL


class CursorOverlay:
    def __init__(self, asset_directory=None):
        self.asset_directory = Path(asset_directory or Path(__file__).with_name("cursor_assets"))
        self.asset_directory.mkdir(parents=True, exist_ok=True)
        self.cursors = {}
        self.assets = {}

        for name, resource_id in CURSOR_RESOURCES.items():
            handle = user32.LoadCursorW(None, ctypes.c_void_p(resource_id))
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            self._register_cursor(name, handle)

    def _register_cursor(self, name, handle):
        path = self.asset_directory / f"{name}.png"
        cursor, hotspot = self._render_cursor(handle)
        cursor.save(path, format="PNG")
        self.cursors[int(handle)] = (path, hotspot)
        self.assets[int(handle)] = cursor

    @staticmethod
    def _render_cursor(handle):
        icon_info = ICONINFO()
        if not user32.GetIconInfo(handle, ctypes.byref(icon_info)):
            raise ctypes.WinError(ctypes.get_last_error())

        bitmap_handle = icon_info.hbmColor or icon_info.hbmMask
        bitmap = BITMAP()
        try:
            if not gdi32.GetObjectW(bitmap_handle, ctypes.sizeof(bitmap), ctypes.byref(bitmap)):
                raise ctypes.WinError(ctypes.get_last_error())

            width = bitmap.bmWidth
            height = bitmap.bmHeight if icon_info.hbmColor else bitmap.bmHeight // 2
            if width <= 0 or height <= 0:
                raise RuntimeError("Windows returned an invalid cursor bitmap size.")

            info = BITMAPINFO()
            info.bmiHeader = BITMAPINFOHEADER(
                ctypes.sizeof(BITMAPINFOHEADER), width, -height, 1, 32,
                BI_RGB, width * height * 4, 0, 0, 0, 0,
            )
            dc = gdi32.CreateCompatibleDC(None)
            if not dc:
                raise ctypes.WinError(ctypes.get_last_error())
            dib_bits = ctypes.c_void_p()
            dib = gdi32.CreateDIBSection(
                dc, ctypes.byref(info), DIB_RGB_COLORS, ctypes.byref(dib_bits), None, 0,
            )
            if not dib:
                gdi32.DeleteDC(dc)
                raise ctypes.WinError(ctypes.get_last_error())

            previous = gdi32.SelectObject(dc, dib)
            try:
                black_pixels = CursorOverlay._draw_on_background(
                    dc, dib_bits, handle, width, height, 0,
                )
                white_pixels = CursorOverlay._draw_on_background(
                    dc, dib_bits, handle, width, height, 255,
                )
            finally:
                gdi32.SelectObject(dc, previous)
                gdi32.DeleteObject(dib)
                gdi32.DeleteDC(dc)

            rgba = bytearray(width * height * 4)
            for i in range(0, len(rgba), 4):
                blue, green, red = black_pixels[i:i + 3]
                white_blue, white_green, white_red = white_pixels[i:i + 3]
                alpha = max(0, min(255, round(255 - (
                    (white_blue - blue) + (white_green - green) + (white_red - red)
                ) / 3)))
                rgba[i:i + 4] = bytes((
                    min(255, round(red * 255 / alpha)) if alpha else 0,
                    min(255, round(green * 255 / alpha)) if alpha else 0,
                    min(255, round(blue * 255 / alpha)) if alpha else 0,
                    alpha,
                ))

            return Image.frombytes("RGBA", (width, height), bytes(rgba)), (
                icon_info.xHotspot, icon_info.yHotspot,
            )
        finally:
            if icon_info.hbmColor:
                gdi32.DeleteObject(icon_info.hbmColor)
            if icon_info.hbmMask:
                gdi32.DeleteObject(icon_info.hbmMask)

    @staticmethod
    def _draw_on_background(dc, dib_bits, handle, width, height, color):
        ctypes.memset(dib_bits, color, width * height * 4)
        if not user32.DrawIconEx(dc, 0, 0, handle, width, height, 0, None, DI_NORMAL):
            raise ctypes.WinError(ctypes.get_last_error())
        return ctypes.string_at(dib_bits, width * height * 4)

    def overlay(self, image):
        cursor_info = CURSORINFO()
        cursor_info.cbSize = ctypes.sizeof(cursor_info)
        if not user32.GetCursorInfo(ctypes.byref(cursor_info)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not cursor_info.flags & CURSOR_SHOWING:
            return

        handle = int(cursor_info.hCursor)
        if handle not in self.cursors:
            self._register_cursor(f"cursor_{handle:x}", cursor_info.hCursor)

        path, hotspot = self.cursors[handle]
        cursor_image = self.assets.get(handle)
        if cursor_image is None:
            cursor_image = Image.open(path).convert("RGBA")
            self.assets[handle] = cursor_image

        left = cursor_info.ptScreenPos.x - hotspot[0]
        top = cursor_info.ptScreenPos.y - hotspot[1]
        image.paste(cursor_image, (left, top), cursor_image)
