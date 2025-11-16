import tkinter as tk
import threading
import queue
from pynput import keyboard
import ctypes
import pystray
from PIL import Image

# --- Configuration ---
DOT_COLORS = {"BASE": "green", "LOWER": "red", "RAISE": "blue", "HIDDEN": "black"}
DOT_SIZE = 8
WINDOW_SIZE = 10

KEY_MAPPING = {
    keyboard.Key.f13: "LOWER",  # NOTI_LOWER
    keyboard.Key.f14: "RAISE",  # NOTI_RAISE
    keyboard.Key.f15: "BASE",  # NOTI_BASE
}

# --- Thread-safe queue for GUI updates ---
color_queue = queue.Queue()

# --- Global references for shutdown ---
app = None
listener = None
icon = None


# --- GUI Application (The Dot) ---
class DotApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.dot_color = DOT_COLORS["BASE"]
        self.wm_attributes("-topmost", 1)
        self.overrideredirect(True)
        self.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}+0+0")
        self.wm_attributes("-transparentcolor", "black")
        self.config(bg="black")

        self.canvas = tk.Canvas(
            self,
            width=WINDOW_SIZE,
            height=WINDOW_SIZE,
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack()

        x0 = (WINDOW_SIZE - DOT_SIZE) / 2
        y0 = (WINDOW_SIZE - DOT_SIZE) / 2
        x1 = x0 + DOT_SIZE
        y1 = y0 + DOT_SIZE
        self.dot = self.canvas.create_oval(
            x0, y0, x1, y1, fill=self.dot_color, outline=self.dot_color
        )

        self.set_click_through()
        self.after(100, self.check_queue)

        # If the window is somehow closed, trigger the exit function
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def on_exit(self):
        # This function is new, in case of a manual close
        exit_app()

    def set_click_through(self):
        try:
            hwnd = self.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new_style = style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
            ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, 255, 0x2)
        except Exception as e:
            print(f"Failed to set click-through: {e}")

    def check_queue(self):
        try:
            new_layer = color_queue.get_nowait()
            self.update_dot(new_layer)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_queue)

    def update_dot(self, layer_name):
        new_color = DOT_COLORS.get(layer_name, "black")
        self.canvas.itemconfig(self.dot, fill=new_color, outline=new_color)


# --- Keyboard Listener ---
def on_press(key):
    try:
        if key in KEY_MAPPING:
            layer_name = KEY_MAPPING[key]
            color_queue.put(layer_name)
    except Exception:
        pass


def start_listener():
    global listener
    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()


# --- NEW: System Tray Icon ---
def setup_tray_icon():
    # Create a simple white image for the icon
    width = 64
    height = 64
    image = Image.new("RGB", (width, height), color="white")

    # Define the menu
    menu = (pystray.MenuItem("Exit", exit_app),)

    # Create the icon
    tray_icon = pystray.Icon("ZMK Notifier", image, "ZMK Layer Notifier", menu)
    return tray_icon


# --- NEW: Exit Function ---
def exit_app():
    # This function cleanly stops all parts
    global listener, app, icon
    print("Exiting application...")
    if listener:
        listener.stop()
    if icon:
        icon.stop()
    if app:
        app.destroy()


# --- Main ---
if __name__ == "__main__":

    # 1. Start the keyboard listener in a background thread
    start_listener()

    # 2. Setup the tray icon
    icon = setup_tray_icon()

    # 3. Start the tray icon in its own thread
    icon.run_detached()

    # 4. Start the tkinter GUI (the dot)
    # This MUST run in the main thread
    app = DotApp()
    app.mainloop()
