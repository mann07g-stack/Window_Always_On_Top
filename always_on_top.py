import tkinter as tk
import ctypes
from ctypes import wintypes
import time
import keyboard

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001

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

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_foreground_window():
    return user32.GetForegroundWindow()

def set_always_on_top(hwnd, enable=True):
    rect = wintypes.RECT()
    try:
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            x = rect.left
            y = rect.top
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            
            if enable:
                flags = SWP_NOMOVE | SWP_NOSIZE
                SWP_SHOWWINDOW = 0x0040 
                
                success = SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags | SWP_SHOWWINDOW)
                
                if not success:
                    err = ctypes.GetLastError()
                    print(f"Initial Pin failed (Error {err}). Retrying with ASYNC...")
                    success = SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags | SWP_SHOWWINDOW | 0x4000)
                    if not success:
                        print(f"Retry failed (Error {ctypes.GetLastError()}). Run as Admin if target is privileged.")
                        return

                print(f"Pinned window {hwnd}")
            else:
                success = SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                if not success:
                    print(f"Unpin failed (Error {ctypes.GetLastError()})")
                else:
                    print(f"Unpinned window {hwnd}")
        else:
            print(f"Invalid window handle {hwnd}")
    except Exception as e:
        print(f"Error setting window position: {e}")

def apply_native_crop(hwnd, screen_region):
    if not hwnd:
        return

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        print("Failed to get window bounds.")
        return

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
            print(f"Native crop applied to {hwnd} (Region: {rel_x},{rel_y} {rel_w}x{rel_h})")
            set_always_on_top(hwnd, True)
        else:
            print("SetWindowRgn failed via user32.")
            DeleteObject(hRgn) 
    else:
        print("Failed to create region.")

def reset_native_crop(hwnd):
    success = SetWindowRgn(hwnd, None, True)
    if success:
        print(f"Crop reset for {hwnd}")
    else:
        print("Failed to reset crop.")


class CropOverlay:
    def __init__(self, on_complete):
        self.on_complete = on_complete
        
        try:
            self.scaling_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
        except:
            self.scaling_factor = 1.0

        self.root = tk.Tk()
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
        
        self.canvas.create_text(
            self.root.winfo_screenwidth() // 2, 
            self.root.winfo_screenheight() // 2,
            text="Draw box. ENTER to Crop. ESC to Cancel.",
            fill="white", font=("Segoe UI", 20, "bold")
        )
        
        self.root.mainloop()

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
        x2, y2 = self.cur_x, self.cur_y
        
        self.x_left = float(min(x1, x2))
        self.y_top = float(min(y1, y2))
        self.x_right = float(max(x1, x2))
        self.y_bottom = float(max(y1, y2))
        
        w = self.x_right - self.x_left
        h = self.y_bottom - self.y_top
        
        if w <= 0 or h <= 0:
            return

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

    def on_release(self, event):
        pass

    def confirm(self, event=None):
        if self.selection_made:
            region = {
                'left': int(self.x_left), 
                'top': int(self.y_top), 
                'width': int(self.x_right - self.x_left), 
                'height': int(self.y_bottom - self.y_top)
            }
            self.root.destroy()
            self.on_complete(region)
        else:
            self.cancel()

    def cancel(self, event=None):
        self.root.destroy()
        self.on_complete(None)

def main():
    print("=== Native Always On Top & Crop Tool ===")
    
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    if not is_admin():
        print("Note: Run as Administrator if global hotkeys fail for some apps.")
        
    print("Hotkeys:")
    print("  CTRL+ALT+P   : Toggle Pin")
    print("  CTRL+ALT+C   : Crop Selection")
    print("  CTRL+ALT+Q   : Reset / Unpin")
    
    pinned_windows = set()
    state = {'target_hwnd': None}

    def handle_pin():
        hwnd = get_foreground_window()
        if hwnd in pinned_windows:
            set_always_on_top(hwnd, False)
            reset_native_crop(hwnd)
            pinned_windows.remove(hwnd)
        else:
            set_always_on_top(hwnd, True)
            pinned_windows.add(hwnd)
    
    def handle_unpin():
        hwnd = get_foreground_window()
        set_always_on_top(hwnd, False)
        reset_native_crop(hwnd)
        if hwnd in pinned_windows:
            pinned_windows.remove(hwnd)

    def on_crop_selection(region):
        target = state['target_hwnd']
        if region and target:
            print(f"Applying crop to window {target}...")
            set_always_on_top(target, True)
            
            apply_native_crop(target, region)
            
            set_always_on_top(target, True)
            
            pinned_windows.add(target)
        else:
            print("Crop cancelled or no target.")

    def start_crop():
        state['target_hwnd'] = get_foreground_window()
        CropOverlay(on_crop_selection)

    try:
        keyboard.add_hotkey('ctrl+alt+p', handle_pin)
        keyboard.add_hotkey('ctrl+alt+q', handle_unpin)
    except ImportError:
        print("Keyboard module error. Is it installed?")
        return
    
    print("Ready.")
    while True:
        try:
            if keyboard.is_pressed('ctrl+alt+c'):
                time.sleep(0.2) 
                start_crop()
            time.sleep(0.05)
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
