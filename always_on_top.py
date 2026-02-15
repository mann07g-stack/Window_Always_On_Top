import tkinter as tk
import ctypes
from ctypes import wintypes
import time
import keyboard
import threading
import psutil
from typing import Any

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
SetWindowPos = user32.SetWindowPos
SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
SetWindowPos.restype = wintypes.BOOL
SetWindowRgn = user32.SetWindowRgn
SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
SetWindowRgn.restype = ctypes.c_int
CreateRectRgn = gdi32.CreateRectRgn
CreateRectRgn.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
CreateRectRgn.restype = wintypes.HANDLE
DeleteObject = gdi32.DeleteObject
DeleteObject.argtypes = [wintypes.HANDLE]
DeleteObject.restype = wintypes.BOOL
WIN_STYLE= -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_BORDER = 0x00800000

def remove_window_decorations(hwnd):
    style = user32.GetWindowLongW(hwnd, WIN_STYLE)
    new_style = style & ~WS_CAPTION & ~WS_THICKFRAME & ~WS_BORDER
    user32.SetWindowLongW(hwnd, WIN_STYLE, new_style)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | 0x0020) 

def restore_window_decorations(hwnd, original_style):
    if original_style:
        user32.SetWindowLongW(hwnd, WIN_STYLE, original_style)
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | 0x0020) 

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_foreground_window():
    return user32.GetForegroundWindow()

def is_window_topmost(hwnd):
    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    return (ex_style & WS_EX_TOPMOST) != 0

def set_always_on_top(hwnd, enable=True):
    rect = wintypes.RECT()
    try:
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            if enable:
                flags = SWP_NOMOVE | SWP_NOSIZE
                SWP_SHOWWINDOW = 0x0040 
                success = SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags | SWP_SHOWWINDOW)
                if not success:
                    success = SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags | SWP_SHOWWINDOW | 0x4000)
            else:
                SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    except Exception:
        pass

def apply_native_crop(hwnd, screen_region):
    if not hwnd: return
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)): return
    win_x = rect.left
    win_y = rect.top
    rel_x = screen_region['left'] - win_x
    rel_y = screen_region['top'] - win_y
    rel_w = screen_region['width']
    rel_h = screen_region['height']
    hRgn = CreateRectRgn(int(rel_x), int(rel_y), int(rel_x + rel_w), int(rel_y + rel_h))
    if hRgn:
        success = SetWindowRgn(hwnd, hRgn, ctypes.c_int(1))
        if success:
            set_always_on_top(hwnd, True)
        else:
            DeleteObject(hRgn) 

def reset_native_crop(hwnd):
    SetWindowRgn(hwnd, None, True)

class CropOverlay:
    def __init__(self, master, on_complete, target_hwnd=None):
        self.on_complete = on_complete
        self.master = master
        self.target_hwnd = target_hwnd
        try:
            self.scaling_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
        except:
            self.scaling_factor = 1.0
        self.root = tk.Toplevel(master)
        self.offset_x = 0
        self.offset_y = 0
        if self.target_hwnd:
             rect = wintypes.RECT()
             if user32.GetWindowRect(self.target_hwnd, ctypes.byref(rect)):
                 w = rect.right - rect.left
                 h = rect.bottom - rect.top
                 self.offset_x = rect.left
                 self.offset_y = rect.top
                 self.root.geometry(f"{w}x{h}+{rect.left}+{rect.top}")
                 self.root.overrideredirect(True) 
             else:
                 self.root.attributes('-fullscreen', True)
        else:
            self.root.attributes('-fullscreen', True)
        self.root.attributes('-alpha', 0.3)
        self.root.configure(bg='black')
        self.root.attributes('-topmost', True)
        self.root.lift()
        self.root.focus_force()
        self.start_x = 0
        self.start_y = 0
        self.cur_x = 0
        self.cur_y = 0
        self.x_left = 0
        self.x_right = 0
        self.y_top = 0
        self.y_bottom = 0
        self.selection_made = False
        self.canvas = tk.Canvas(self.root, cursor="cross", bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("<Escape>", self.cancel)
        self.root.bind("<Return>", self.confirm)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        cw = self.root.winfo_screenwidth()
        ch = self.root.winfo_screenheight()
        if self.target_hwnd:
             rect = wintypes.RECT()
             if user32.GetWindowRect(self.target_hwnd, ctypes.byref(rect)):
                cw = rect.right - rect.left
                ch = rect.bottom - rect.top
        self.canvas.create_text(
            cw // 2, ch // 2,
            text="Draw to Crop. ENTER Confirm. ESC Cancel.",
            fill="white", font=("Segoe UI", 20, "bold")
        )
        
    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def on_drag(self, event):
        self.cur_x, self.cur_y = event.x, event.y
        self.draw_selection()
        self.selection_made = True

    def draw_selection(self):
        self.canvas.delete("selection")
        x1, y1 = self.start_x, self.start_y
        w_canv = self.canvas.winfo_width()
        h_canv = self.canvas.winfo_height()
        x2 = max(0, min(self.cur_x, w_canv))
        y2 = max(0, min(self.cur_y, h_canv))
        self.x_left = float(min(x1, x2))
        self.y_top = float(min(y1, y2))
        self.x_right = float(max(x1, x2))
        self.y_bottom = float(max(y1, y2))
        w = self.x_right - self.x_left
        h = self.y_bottom - self.y_top
        if w <= 0 or h <= 0: return
        color = "red"
        thick = 4
        handle_s = 10.0
        mid_x = self.x_left + w / 2
        mid_y = self.y_top + h / 2
        self.canvas.create_rectangle(self.x_left, self.y_top, self.x_right, self.y_bottom, outline=color, width=thick, tags=("selection",))
        self.canvas.create_rectangle(mid_x-handle_s, self.y_top-handle_s, mid_x+handle_s, self.y_top+handle_s, fill=color, outline="white", tags=("selection",))
        self.canvas.create_rectangle(mid_x-handle_s, self.y_bottom-handle_s, mid_x+handle_s, self.y_bottom+handle_s, fill=color, outline="white", tags=("selection",))
        self.canvas.create_rectangle(self.x_left-handle_s, mid_y-handle_s, self.x_left+handle_s, mid_y+handle_s, fill=color, outline="white", tags=("selection",))
        self.canvas.create_rectangle(self.x_right-handle_s, mid_y-handle_s, self.x_right+handle_s, mid_y+handle_s, fill=color, outline="white", tags=("selection",))

    def on_release(self, event): pass

    def confirm(self, event=None):
        if self.selection_made:
            abs_left = self.x_left + self.offset_x
            abs_top = self.y_top + self.offset_y
            region = {
                'left': int(abs_left), 
                'top': int(abs_top), 
                'width': int(self.x_right - self.x_left), 
                'height': int(self.y_bottom - self.y_top)
            }
            self.root.destroy()
            self.on_complete(region)
        else: self.cancel()

    def cancel(self, event=None):
        self.root.destroy()
        self.on_complete(None)
    
    def on_close(self):
        self.root.destroy()
        self.on_complete(None)

class TitleBar:
    def __init__(self, master, target_hwnd, region, on_reset_callback):
        self.master = master
        self.target_hwnd = target_hwnd
        self.on_reset = on_reset_callback
        self.width = region['width']
        self.start_x = region['left']
        self.current_bar_x = self.start_x
        target_y = region['top'] - 30
        if target_y < 0: target_y = 0
        self.current_bar_y = target_y
        self.top = tk.Toplevel(master)
        self.top.overrideredirect(True)
        self.top.geometry(f"{self.width}x30+{self.current_bar_x}+{self.current_bar_y}")
        self.top.attributes('-topmost', True)
        self.top.configure(bg='#0078D7') 
        self.top.attributes('-alpha', 0.9)
        drag_frame = tk.Frame(self.top, bg='#0078D7', cursor="fleur")
        drag_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lbl = tk.Label(drag_frame, text="::: Drag :::", bg='#0078D7', fg='white', font=("Segoe UI", 9, "bold"))
        lbl.pack(fill=tk.BOTH, expand=True)
        btn = tk.Button(self.top, text="X", bg='#E81123', fg='white', command=self.close_crop, bd=0, padx=15, font=("Segoe UI", 9, "bold"))
        btn.pack(side=tk.RIGHT, fill=tk.Y)
        drag_frame.bind("<ButtonPress-1>", self.on_press)
        drag_frame.bind("<B1-Motion>", self.on_drag)
        lbl.bind("<ButtonPress-1>", self.on_press)
        lbl.bind("<B1-Motion>", self.on_drag)
        self.last_x = 0
        self.last_y = 0

    def on_press(self, event):
        self.last_x = event.x_root
        self.last_y = event.y_root

    def on_drag(self, event):
        dx = event.x_root - self.last_x
        dy = event.y_root - self.last_y
        self.current_bar_x += dx
        self.current_bar_y += dy
        self.top.geometry(f"+{self.current_bar_x}+{self.current_bar_y}")
        rect = wintypes.RECT()
        if user32.GetWindowRect(self.target_hwnd, ctypes.byref(rect)):
             new_x = rect.left + dx
             new_y = rect.top + dy
             flags = 0x0001 | 0x0004 | 0x0010
             user32.SetWindowPos(self.target_hwnd, 0, new_x, new_y, 0, 0, flags)
        self.last_x = event.x_root
        self.last_y = event.y_root

    def close_crop(self):
        if self.on_reset: self.on_reset()

    def destroy(self):
        try: self.top.destroy()
        except: pass

def main(root_window):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try: ctypes.windll.user32.SetProcessDPIAware()
        except: pass

    pinned_windows = set()
    state: dict[str, Any] = {'target_hwnd': None, 'active_titlebar': None, 'original_style': None} 

    def reset_ui_state():
        if state['active_titlebar']:
            state['active_titlebar'].destroy()
            state['active_titlebar'] = None

    def handle_pin():
        try:
            hwnd = get_foreground_window()
            if not hwnd: return
            current_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            is_visually_pinned = (current_style & WS_EX_TOPMOST) != 0
            if (hwnd in pinned_windows) or is_visually_pinned:
                set_always_on_top(hwnd, False)
                reset_native_crop(hwnd)
                if state.get('original_style') and state['target_hwnd'] == hwnd:
                     restore_window_decorations(hwnd, state['original_style'])
                     state['original_style'] = None
                reset_ui_state() 
                if hwnd in pinned_windows: pinned_windows.remove(hwnd)
                try: ctypes.windll.user32.MessageBeep(0xFFFFFFFF) 
                except: pass
            else:
                set_always_on_top(hwnd, True)
                pinned_windows.add(hwnd)
                try: ctypes.windll.user32.MessageBeep(0) 
                except: pass
        except: pass

    def handle_unpin():
        try:
             hwnd = get_foreground_window()
             target = state.get('target_hwnd')
             if hwnd:
                set_always_on_top(hwnd, False)
                reset_native_crop(hwnd)
                if hwnd in pinned_windows: pinned_windows.remove(hwnd)
             if target:
                 set_always_on_top(target, False)
                 reset_native_crop(target)
                 if state.get('original_style'):
                     restore_window_decorations(target, state['original_style'])
                     state['original_style'] = None
                 if target in pinned_windows: pinned_windows.remove(target)
                 reset_ui_state()
             try: ctypes.windll.user32.MessageBeep(0xFFFFFFFF)
             except: pass
        except: pass

    def on_titlebar_close():
        if state['target_hwnd']:
            set_always_on_top(state['target_hwnd'], False)
            reset_native_crop(state['target_hwnd'])
            if state.get('original_style'):
                 restore_window_decorations(state['target_hwnd'], state['original_style'])
                 state['original_style'] = None
            if state['target_hwnd'] in pinned_windows: pinned_windows.remove(state['target_hwnd'])
            reset_ui_state()
            try: ctypes.windll.user32.MessageBeep(0xFFFFFFFF)
            except: pass

    def on_crop_selection(region):
        state['is_cropping'] = False 
        target = state['target_hwnd']
        reset_ui_state()
        if region and target:
            current_s = user32.GetWindowLongW(target, WIN_STYLE)
            state['original_style'] = current_s
            remove_window_decorations(target)
            set_always_on_top(target, True)
            apply_native_crop(target, region)
            set_always_on_top(target, True)
            pinned_windows.add(target)
            bar = TitleBar(root_window, target, region, on_titlebar_close)
            state['active_titlebar'] = bar

    def start_crop():
        if state.get('is_cropping'): return
        state['is_cropping'] = True
        time.sleep(0.1)
        state['target_hwnd'] = get_foreground_window()
        CropOverlay(root_window, on_crop_selection, target_hwnd=state['target_hwnd'])

    def request_crop():
        if not state.get('is_cropping'):
            state['crop_request'] = True

    if not state.get('hotkeys_registered'):
        try:
            keyboard.add_hotkey('ctrl+alt+p', handle_pin)
            keyboard.add_hotkey('ctrl+alt+q', handle_unpin)
            keyboard.add_hotkey('ctrl+alt+c', request_crop, suppress=True) 
            state['hotkeys_registered'] = True
        except ImportError: return
    
    while True:
        try:
            try:
                root_window.update_idletasks()
                root_window.update()
            except tk.TclError: break 
            if state.get('crop_request'):
                state['crop_request'] = False
                start_crop()
            time.sleep(0.01)
        except KeyboardInterrupt: break

if __name__ == "__main__":
    try:
        p = psutil.Process()
        p.nice(psutil.HIGH_PRIORITY_CLASS)
    except: pass
    root = tk.Tk()
    root.withdraw()
    main(root)
