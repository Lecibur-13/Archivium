import os, json, subprocess, datetime, re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkfont
from styles import apply_styles
# Add image support (Pillow) if available
try:
    from PIL import Image, ImageDraw, ImageTk
except Exception:
    Image = None
    ImageDraw = None
    ImageTk = None
try:
    import customtkinter as ctk
    USE_CTK = True
except Exception:
    ctk = None
    USE_CTK = False

icons = {}

APP_NAME = "Archivium"
APP_ID = "Archivium"
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_ID)
CONFIG_PATH = os.path.join(APPDATA_DIR, "config.json")
DEFAULT_CONFIG = {"default_dest": "", "theme": "system", "organize_mode": "current"}
# App logo paths
LOGO_PATH = os.path.join(os.path.dirname(__file__), "img", "logo.PNG")
LOGO_ICO_PATH = os.path.join(os.path.dirname(__file__), "img", "logo.ico")
HEADER_IMAGE_SIZE = 48

JPEG_PATTERNS = ["*.jpg","*.jpeg","*.jpe","*.jfif","*.png","*.gif","*.bmp","*.tiff","*.tif","*.webp","*.ico","*.svg","*.heic","*.heif"]
RAW_PATTERNS  = ["*.cr2","*.cr3","*.nef","*.raf","*.arw","*.rw2","*.dng","*.orf","*.sr2","*.pef","*.nrw"]
VIDEO_PATTERNS= ["*.mp4","*.mov","*.avi","*.mts","*.mxf","*.mpg","*.mpeg","*.mkv","*.wmv","*.3gp"]

log_text = None
format_btn = None
organize_btn = None
root_app = None
logs_frame = None
logs_toggle_btn = None
logs_visible = False
CURRENT_SETTINGS_WINDOW = None
USER_INTENDS_SETTINGS = False
# Cancellation and transfer status
cancel_event = None
is_transferring = False
transfer_thread = None
# Font configuration
UI_FONT_FAMILY = "Arial"
BASE_FONT = None
TITLE_FONT = None
SMALL_FONT = None
LABEL_FONT_BOLD = None
EMOJI_FONT = None
ENTRY_FONT = None

def ensure_appdata(): os.makedirs(APPDATA_DIR, exist_ok=True)

def load_config():
    ensure_appdata()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH,"r",encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    ensure_appdata()
    with open(CONFIG_PATH,"w",encoding="utf-8") as f: json.dump(cfg,f,ensure_ascii=False,indent=2)

def log(text):
    import threading
    def _append():
        log_text.configure(state="normal")
        log_text.insert("end", text+"\n")
        log_text.see("end")
        log_text.configure(state="disabled")
    if threading.current_thread() is threading.main_thread():
        _append()
    else:
        root_app.after(0, _append)

def pick_dest():
    path = filedialog.askdirectory(title="Select destination folder")
    if path:
        dest_var.set(path)
        cfg = load_config(); cfg["default_dest"] = path; save_config(cfg)
        log(f"Destination saved: {path}")

def pick_src():
    path = filedialog.askdirectory(title="Select source folder (SD/Folder)")
    if path:
        src_var.set(path)
        log(f"Source: {path}")

def today_str(): return datetime.date.today().strftime("%Y-%m-%d")

def next_sequence_folder(base):
    date_str = today_str(); prefix = date_str+"_"; seq = 1
    try:
        existing = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base,d)) and d.startswith(prefix)]
        if existing:
            nums = []; pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
            for d in existing:
                m = pattern.match(d)
                if m: nums.append(int(m.group(1)))
            if nums: seq = max(nums) + 1
    except Exception: pass
    return os.path.join(base, f"{prefix}{seq:02d}")

def ensure_dirs(*dirs):
    for d in dirs: os.makedirs(d, exist_ok=True)

def detect_drive_letter(path):
    if os.name == 'nt' and len(path) >= 2 and path[1] == ':': return path[0].upper()
    return None

def ensure_logo_icon():
    if not os.path.exists(LOGO_ICO_PATH) and Image:
        try:
            if os.path.exists(LOGO_PATH):
                img = Image.open(LOGO_PATH).convert("RGBA")
                img.save(LOGO_ICO_PATH, format="ICO", sizes=[(32,32)])
        except Exception: pass

def set_window_icon(root):
    ensure_logo_icon()
    try:
        if os.path.exists(LOGO_ICO_PATH): root.iconbitmap(LOGO_ICO_PATH)
    except Exception: pass

def clear_window_icon(root):
    try: root.iconbitmap("")
    except Exception: pass

def robocopy_available():
    try: subprocess.run(["robocopy", "/?"], capture_output=True, check=False); return True
    except Exception: return False

def transfer_with_robocopy(src, dest, patterns, move=False):
    cmd = ["robocopy", src, dest] + patterns
    if move: cmd.append("/MOVE")
    cmd.extend(["/E", "/R:3", "/W:1", "/NP", "/NDL", "/NFL"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode < 8
    except Exception: return False

def unique_dest_path(dest, filename):
    base, ext = os.path.splitext(filename); counter = 1
    while os.path.exists(os.path.join(dest, filename)):
        filename = f"{base}_{counter}{ext}"; counter += 1
    return os.path.join(dest, filename)

# Determina el tipo de archivo a partir de su extensión
def get_file_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    jpeg_exts = {".jpg",".jpeg",".jpe",".jfif",".png",".gif",".bmp",".tiff",".tif",".webp",".ico",".svg",".heic",".heif"}
    raw_exts = {".cr2",".cr3",".nef",".raf",".arw",".rw2",".dng",".orf",".sr2",".pef",".nrw"}
    video_exts = {".mp4",".mov",".avi",".mts",".mxf",".mpg",".mpeg",".mkv",".wmv",".3gp"}
    if ext in jpeg_exts: return "JPEG"
    if ext in raw_exts: return "RAW"
    if ext in video_exts: return "VIDEO"
    return None

# Obtiene la fecha de captura (EXIF si disponible; si no, fecha de modificación)
def get_capture_date(file_path):
    # Devuelve formato DD-MM-YYYY
    try:
        if Image:
            try:
                img = Image.open(file_path)
                exif = {}
                try:
                    exif = img.getexif() or {}
                except Exception:
                    pass
                # Intentar claves string y numéricas más comunes
                dt = None
                if isinstance(exif, dict):
                    dt = exif.get("DateTimeOriginal") or exif.get("DateTime") or exif.get("DateTimeDigitized")
                    dt = dt or exif.get(36867) or exif.get(306) or exif.get(36868)
                if dt:
                    # Formato típico: YYYY:MM:DD HH:MM:SS
                    import datetime as _dt
                    s = str(dt)
                    parts = s.split(" ")[0].replace(":","-").split("-")
                    if len(parts) >= 3:
                        yyyy, mm, dd = parts[0], parts[1], parts[2]
                        return f"{dd}-{mm}-{yyyy}"
                try:
                    img.close()
                except Exception:
                    pass
            except Exception:
                pass
        ts = os.path.getmtime(file_path)
        d = datetime.datetime.fromtimestamp(ts).date()
        return d.strftime("%d-%m-%Y")
    except Exception:
        return datetime.date.today().strftime("%d-%m-%Y")

# Transfiere agrupando por fecha→tipo o tipo→fecha
def transfer_grouped(src, dest, move=False, progress_cb=None, mode="date_then_type"):
    import shutil, threading
    global cancel_event
    files_info = []
    for root, dirs, filenames in os.walk(src):
        if cancel_event and cancel_event.is_set(): return False
        for filename in filenames:
            fp = os.path.join(root, filename)
            typ = get_file_type(fp)
            if not typ: continue
            date_str = get_capture_date(fp)
            files_info.append((fp, typ, date_str))
    total = len(files_info); transferred = 0
    for fp, typ, date_str in files_info:
        if cancel_event and cancel_event.is_set(): return False
        try:
            if mode == "date_then_type":
                dest_dir = os.path.join(dest, date_str, typ)
            else:
                dest_dir = os.path.join(dest, typ, date_str)
            os.makedirs(dest_dir, exist_ok=True)
            out_name = os.path.basename(fp)
            dest_path = os.path.join(dest_dir, out_name)
            if os.path.exists(dest_path): dest_path = unique_dest_path(dest_dir, out_name)
            if move: shutil.move(fp, dest_path)
            else: shutil.copy2(fp, dest_path)
            transferred += 1
            if progress_cb and threading.current_thread() is threading.main_thread():
                progress_cb(transferred, total, typ)
            elif progress_cb:
                root_app.after(0, lambda t=transferred, tot=total, k=typ: progress_cb(t, tot, k))
        except Exception as e:
            log(f"Error transferring {fp}: {e}")
    return True

def transfer_with_python(src, dest, patterns, move=False, progress_cb=None, kind=None):
    import shutil, fnmatch, threading
    global cancel_event
    if cancel_event and cancel_event.is_set(): return False
    files = []
    for root, dirs, filenames in os.walk(src):
        if cancel_event and cancel_event.is_set(): return False
        for filename in filenames:
            for pattern in patterns:
                if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                    files.append(os.path.join(root, filename)); break
    if not files: return True
    total = len(files); transferred = 0
    for file_path in files:
        if cancel_event and cancel_event.is_set(): return False
        try:
            rel_path = os.path.relpath(file_path, src)
            dest_path = os.path.join(dest, rel_path)
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            if os.path.exists(dest_path): dest_path = unique_dest_path(dest_dir, os.path.basename(dest_path))
            if move: shutil.move(file_path, dest_path)
            else: shutil.copy2(file_path, dest_path)
            transferred += 1
            if progress_cb and threading.current_thread() is threading.main_thread():
                progress_cb(transferred, total, kind)
            elif progress_cb:
                root_app.after(0, lambda t=transferred, tot=total, k=kind: progress_cb(t, tot, k))
        except Exception as e:
            log(f"Error transferring {file_path}: {e}")
    return True

def do_transfer(src, session_dir, move=False):
    global cancel_event, is_transferring, transfer_thread
    import threading
    cancel_event = threading.Event(); is_transferring = True
    show_progress()
    def progress_callback(transferred, total, kind):
        if total > 0:
            pct = (transferred / total) * 100
            progress_bar.set(pct / 100)
            status_var.set(f"Transferring {kind}: {transferred}/{total} ({pct:.1f}%)")
    def transfer_task():
        try:
            log(f"Starting transfer from {src} to {session_dir}")
            log(f"Mode: {'Move' if move else 'Copy'}")
            cfg = load_config(); mode = cfg.get("organize_mode", "current")
            if mode == "current":
                jpeg_dir = os.path.join(session_dir, "JPEG")
                raw_dir = os.path.join(session_dir, "RAW")
                video_dir = os.path.join(session_dir, "VIDEO")
                ensure_dirs(jpeg_dir, raw_dir, video_dir)
                # Transfer by categories
                categories = [("JPEG", JPEG_PATTERNS, jpeg_dir), ("RAW", RAW_PATTERNS, raw_dir), ("VIDEO", VIDEO_PATTERNS, video_dir)]
                for kind, patterns, dest_dir in categories:
                    if cancel_event.is_set(): break
                    log(f"Transferring {kind} files...")
                    status_var.set(f"Transferring {kind} files...")
                    if robocopy_available() and os.name == 'nt':
                        success = transfer_with_robocopy(src, dest_dir, patterns, move)
                    else:
                        success = transfer_with_python(src, dest_dir, patterns, move, progress_callback, kind)
                    if not success and not cancel_event.is_set():
                        log(f"Failed to transfer {kind} files")
            else:
                log(f"Transfiriendo en modo '{mode}'...")
                status_var.set("Transferring grouped files...")
                # Para modos avanzados se usa transferencia Python agrupada
                m = "date_then_type" if mode == "date_then_type" else "type_then_date"
                success = transfer_grouped(src, session_dir, move, progress_callback, mode=m)
                if not success and not cancel_event.is_set():
                    log("Failed to transfer grouped files")
            if cancel_event.is_set():
                log("Transfer cancelled by user")
                status_var.set("Transfer cancelled")
            else:
                log("Transfer completed successfully")
                status_var.set("Transfer completed")
        except Exception as e:
            log(f"Transfer error: {e}")
            status_var.set(f"Transfer error: {e}")
        finally:
            is_transferring = False
            hide_progress()
    transfer_thread = threading.Thread(target=transfer_task, daemon=True)
    transfer_thread.start()

def organize():
    global cancel_event, transfer_thread, is_transferring
    # Robustez: si el hilo terminó pero la bandera quedó activa, resetea
    try:
        if is_transferring and transfer_thread and not transfer_thread.is_alive():
            is_transferring = False
            try: hide_progress()
            except Exception: pass
    except Exception:
        pass
    if is_transferring:
        if messagebox.askyesno("Cancel Transfer", "A transfer is in progress. Cancel it?"):
            if cancel_event: cancel_event.set()
            if transfer_thread: transfer_thread.join(timeout=2)
        return
    src = src_var.get().strip(); dest = dest_var.get().strip()
    if not src:
        messagebox.showerror("Error", "Please select a source folder"); return
    if not dest:
        messagebox.showerror("Error", "Please select a destination folder"); return
    if not os.path.exists(src):
        messagebox.showerror("Error", f"Source folder does not exist: {src}"); return
    if not os.path.exists(dest):
        messagebox.showerror("Error", f"Destination folder does not exist: {dest}"); return
    cfg = load_config(); mode = cfg.get("organize_mode", "current")
    if mode == "current":
        session_dir = next_sequence_folder(dest)
        try: os.makedirs(session_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create session folder: {e}"); return
        out_base = session_dir
    else:
        out_base = dest
    move_files = move_var.get()
    do_transfer(src, out_base, move_files)

def format_sd():
    src = src_var.get().strip()
    if not src:
        messagebox.showerror("Error", "Please select a source folder (SD card)"); return
    drive = detect_drive_letter(src)
    if not drive:
        messagebox.showerror("Error", "Cannot detect drive letter. Please select the root of an SD card."); return
    if not messagebox.askyesno("Confirm Format", f"This will FORMAT drive {drive}: and erase ALL data. Continue?"):
        return
    try:
        cmd = f'format {drive}: /FS:exFAT /Q /V:SD_CARD /Y'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            log(f"Drive {drive}: formatted successfully")
            messagebox.showinfo("Success", f"Drive {drive}: formatted successfully")
        else:
            log(f"Format failed: {result.stderr}")
            messagebox.showerror("Error", f"Format failed: {result.stderr}")
    except Exception as e:
        log(f"Format error: {e}")
        messagebox.showerror("Error", f"Format error: {e}")

def _make_folder_pil(size=24, color="#e5e7eb"):
    if not Image: return None
    img = Image.new("RGBA", (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    margin = size // 8; folder_height = size - 2*margin; folder_width = size - 2*margin
    tab_width = folder_width // 3; tab_height = folder_height // 4
    draw.rectangle([margin, margin + tab_height, margin + folder_width, margin + folder_height], fill=color)
    draw.rectangle([margin, margin, margin + tab_width, margin + tab_height], fill=color)
    return img

def make_ctk_folder_icon(size=20, color="#e5e7eb"):
    if not ctk or not ImageTk: return None
    pil_img = _make_folder_pil(size, color)
    return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(size, size)) if pil_img else None

def make_tk_folder_icon(root, size=16, color="#e5e7eb"):
    if not ImageTk: return None
    pil_img = _make_folder_pil(size, color)
    return ImageTk.PhotoImage(pil_img) if pil_img else None

def pick_font_family(root):
    global UI_FONT_FAMILY
    families = sorted(tkfont.families())
    selection = tk.simpledialog.askstring("Font Selection", f"Available fonts:\n{', '.join(families[:10])}...\n\nEnter font name:", initialvalue=UI_FONT_FAMILY)
    if selection and selection in families:
        UI_FONT_FAMILY = selection
        messagebox.showinfo("Font Changed", f"Font changed to: {UI_FONT_FAMILY}\nRestart the application to apply changes.")

def init_style(root):
    global BASE_FONT, TITLE_FONT, SMALL_FONT, LABEL_FONT_BOLD, EMOJI_FONT, ENTRY_FONT
    try:
        BASE_FONT = tkfont.Font(family=UI_FONT_FAMILY, size=10)
        TITLE_FONT = tkfont.Font(family=UI_FONT_FAMILY, size=16, weight="bold")
        SMALL_FONT = tkfont.Font(family=UI_FONT_FAMILY, size=9)
        LABEL_FONT_BOLD = tkfont.Font(family=UI_FONT_FAMILY, size=10, weight="bold")
        EMOJI_FONT = tkfont.Font(family="Segoe UI Emoji", size=12)
        ENTRY_FONT = tkfont.Font(family=UI_FONT_FAMILY, size=10)
    except Exception:
        BASE_FONT = tkfont.Font(family="Arial", size=10)
        TITLE_FONT = tkfont.Font(family="Arial", size=16, weight="bold")
        SMALL_FONT = tkfont.Font(family="Arial", size=9)
        LABEL_FONT_BOLD = tkfont.Font(family="Arial", size=10, weight="bold")
        EMOJI_FONT = tkfont.Font(family="Arial", size=12)
        ENTRY_FONT = tkfont.Font(family="Arial", size=10)

def toggle_logs():
    global logs_visible
    if logs_visible:
        logs_frame.grid_remove()
        logs_toggle_btn.configure(text="Show log")
        logs_visible = False
    else:
        logs_frame.grid()
        logs_toggle_btn.configure(text="Hide log")
        logs_visible = True

def show_progress():
    progress_bar.grid()
    progress_bar.set(0)

def hide_progress():
    progress_bar.grid_remove()
    progress_bar.set(0)

def detect_system_theme():
    """Detecta el tema del sistema Windows"""
    try:
        import winreg
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if value == 1 else "dark"
    except:
        return "light"  # Default fallback

def apply_theme(theme_name):
    """Aplica el tema y asegura que Settings no se cierre al primer cambio"""
    if USE_CTK:
        if theme_name == "system":
            system_theme = detect_system_theme()
            ctk.set_appearance_mode(system_theme)
        else:
            ctk.set_appearance_mode(theme_name)
    
    cfg = load_config(); cfg["theme"] = theme_name; save_config(cfg)
    log(f"Theme changed to: {theme_name}")
    
    # Immediate re-elevation if exists
    try:
        win = globals().get('CURRENT_SETTINGS_WINDOW')
        if win is not None:
            if hasattr(win, 'winfo_exists') and win.winfo_exists():
                try: win.deiconify()
                except Exception: pass
                win.lift(); win.focus_force()
                try: win.attributes('-topmost', True)
                except Exception: pass
                try: win.after(300, lambda: win.attributes('-topmost', False))
                except Exception: pass
    except Exception:
        pass
    
    # Safeguard: if destroyed by theme change, reopen with after
    try:
        def ensure_settings_visible():
            try:
                w = globals().get('CURRENT_SETTINGS_WINDOW')
                if w is not None and hasattr(w, 'winfo_exists') and w.winfo_exists():
                    try: w.deiconify()
                    except Exception: pass
                    w.lift(); w.focus_force()
                    try: w.attributes('-topmost', True)
                    except Exception: pass
                    try: w.after(300, lambda: w.attributes('-topmost', False))
                    except Exception: pass
                else:
                    # Reopen if destroyed by theme
                    try: open_settings()
                    except Exception: pass
            except Exception:
                pass
        if 'root_app' in globals() and globals().get('root_app'):
            if globals().get('USER_INTENDS_SETTINGS'):
                globals()['root_app'].after(120, ensure_settings_visible)
    except Exception:
        pass
    
    # Release any capture in main if stuck
    try:
        if 'root_app' in globals() and globals().get('root_app'):
            globals()['root_app'].grab_release()
            try: globals()['root_app'].attributes('-topmost', False)
            except Exception: pass
    except Exception:
        pass

# Guarda el modo de organización de carpetas seleccionado
def apply_organize_mode(mode_name):
    try:
        cfg = load_config(); cfg["organize_mode"] = mode_name; save_config(cfg)
        log(f"Modo de organización actualizado: {mode_name}")
    except Exception as e:
        log(f"No se pudo guardar el modo de organización: {e}")

def open_settings():
    """Opens the settings window as a child of main, with sidenav and icon"""
    global CURRENT_SETTINGS_WINDOW, USER_INTENDS_SETTINGS
    USER_INTENDS_SETTINGS = True
    if USE_CTK:
        settings_window = ctk.CTkToplevel(root_app)
        CURRENT_SETTINGS_WINDOW = settings_window
        settings_window.title("Settings")
        settings_window.resizable(False, False)
        settings_window.transient(root_app)
        settings_window.lift()
        settings_window.focus_force()
        # Keep on top while open
        try:
            settings_window.attributes('-topmost', True)
        except Exception:
            pass
        
        # Icon app
        try:
            set_window_icon(settings_window)
            if os.path.exists(LOGO_ICO_PATH):
                settings_window.iconbitmap(LOGO_ICO_PATH)
                settings_window.wm_iconbitmap(LOGO_ICO_PATH)
        except Exception:
            pass
        
        # Get fonts from styles object
        styles_obj = apply_styles(settings_window, use_ctk=True)
        
        # Center over main
        width, height = 600, 450
        try:
            root_app.update_idletasks()
            rx, ry = root_app.winfo_rootx(), root_app.winfo_rooty()
            rw, rh = root_app.winfo_width(), root_app.winfo_height()
            x = rx + (rw - width)//2
            y = ry + (rh - height)//2
            settings_window.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            settings_window.geometry(f"{width}x{height}")
        
        # Improved layout with sidenav
        settings_window.grid_columnconfigure(0, weight=1)
        settings_window.grid_rowconfigure(0, weight=1)
        container = ctk.CTkFrame(settings_window)
        container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        container.grid_columnconfigure(0, weight=0)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)
        
        # Sidenav with better typography
        sidenav = ctk.CTkFrame(container, width=160)
        sidenav.grid(row=0, column=0, sticky="ns", padx=(0,12))
        
        # Sidenav header
        nav_header = ctk.CTkFrame(sidenav, fg_color="transparent")
        nav_header.pack(fill="x", padx=12, pady=(12,16))
        ctk.CTkLabel(nav_header, text="Settings", font=styles_obj.TITLE_2_FONT).pack(anchor="w")
        ctk.CTkLabel(nav_header, text="Configure your preferences", font=styles_obj.CAPTION_1_FONT, text_color="#9ca3af").pack(anchor="w", pady=(2,0))
        
        current_section = tk.StringVar(value="Appearance")
        def update_section_view():
            try:
                if current_section.get() == "Appearance":
                    appearance_section.grid()
                    behavior_section.grid_remove()
                else:
                    behavior_section.grid()
                    appearance_section.grid_remove()
            except Exception:
                pass
        def select_section(name):
            current_section.set(name)
            update_section_view()
        ctk.CTkButton(sidenav, text="Appearance", command=lambda: select_section("Appearance"), fg_color="#334155", hover_color="#475569", text_color="#e2e8f0", font=styles_obj.CALLOUT_FONT).pack(fill="x", padx=8, pady=(0,6))
        ctk.CTkButton(sidenav, text="Behavior", command=lambda: select_section("Behavior"), fg_color="#334155", hover_color="#475569", text_color="#e2e8f0", font=styles_obj.CALLOUT_FONT).pack(fill="x", padx=8)
        
        # Content area with better design
        content = ctk.CTkFrame(container, corner_radius=8)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        
        # Appearance section (separate frame)
        appearance_section = ctk.CTkFrame(content, fg_color="transparent")
        appearance_section.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        appearance_section.grid_columnconfigure(0, weight=1)
        
        # Section header
        section_header = ctk.CTkFrame(appearance_section, fg_color="transparent")
        section_header.grid(row=0, column=0, sticky="ew", pady=(0,20))
        ctk.CTkLabel(section_header, text="Appearance", font=styles_obj.TITLE_2_FONT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(section_header, text="Customize the look and feel of the application", font=styles_obj.SUBHEADLINE_FONT, text_color="#9ca3af").grid(row=1, column=0, sticky="w", pady=(4,0))
        
        # Theme selection
        theme_section = ctk.CTkFrame(appearance_section, fg_color="transparent")
        theme_section.grid(row=1, column=0, sticky="ew", pady=(0,16))
        theme_section.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(theme_section, text="Theme", font=styles_obj.HEADLINE_FONT).grid(row=0, column=0, sticky="w", pady=(0,4))
        ctk.CTkLabel(theme_section, text="Choose between light, dark, or system theme", font=styles_obj.SUBHEADLINE_FONT, text_color="#9ca3af").grid(row=1, column=0, sticky="w", pady=(0,12))
        current_config = load_config(); current_theme = current_config.get("theme", "system")
        theme_var = tk.StringVar(value=current_theme)
        theme_options = ctk.CTkSegmentedButton(theme_section, values=["light","dark","system"], variable=theme_var, command=lambda m: apply_theme(m), font=styles_obj.CALLOUT_FONT)
        theme_options.grid(row=2, column=0, sticky="w")
        theme_options.set(current_theme)
        
        # Behavior section (separate frame)
        behavior_section = ctk.CTkFrame(content, fg_color="transparent")
        behavior_section.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        behavior_section.grid_columnconfigure(0, weight=1)
        behavior_header = ctk.CTkFrame(behavior_section, fg_color="transparent")
        behavior_header.grid(row=0, column=0, sticky="ew", pady=(0,20))
        ctk.CTkLabel(behavior_header, text="Behavior", font=styles_obj.TITLE_2_FONT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(behavior_header, text="Configure how destination folders are organized", font=styles_obj.SUBHEADLINE_FONT, text_color="#9ca3af").grid(row=1, column=0, sticky="w", pady=(4,0))
        current_cfg2 = load_config(); current_mode = current_cfg2.get("organize_mode", "current")
        mode_var = tk.StringVar(value=current_mode)
        
        # Group title
        ctk.CTkLabel(behavior_section, text="Folder Organization Mode", font=styles_obj.HEADLINE_FONT).grid(row=1, column=0, sticky="w", pady=(0,8))
        radio_frame = ctk.CTkFrame(behavior_section, fg_color="transparent")
        radio_frame.grid(row=2, column=0, sticky="w")
        ctk.CTkRadioButton(radio_frame, text="Classic Session", variable=mode_var, value="current", command=lambda: apply_organize_mode(mode_var.get()), font=styles_obj.CALLOUT_FONT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(radio_frame, text="Creates a session folder and organizes by categories (e.g., Session_01/Images).", font=styles_obj.FOOTNOTE_FONT, text_color="#9ca3af").grid(row=1, column=0, sticky="w", pady=(0,8))
        ctk.CTkRadioButton(radio_frame, text="Chronological (Date First)", variable=mode_var, value="date_then_type", command=lambda: apply_organize_mode(mode_var.get()), font=styles_obj.CALLOUT_FONT).grid(row=2, column=0, sticky="w")
        ctk.CTkLabel(radio_frame, text="Groups by capture date, then by file type (e.g., 2025/10/22/Images).", font=styles_obj.FOOTNOTE_FONT, text_color="#9ca3af").grid(row=3, column=0, sticky="w", pady=(0,8))
        ctk.CTkRadioButton(radio_frame, text="Collections (Type First)", variable=mode_var, value="type_then_date", command=lambda: apply_organize_mode(mode_var.get()), font=styles_obj.CALLOUT_FONT).grid(row=4, column=0, sticky="w")
        ctk.CTkLabel(radio_frame, text="Groups by file type, then by capture date (e.g., Images/2025/10/22).", font=styles_obj.FOOTNOTE_FONT, text_color="#9ca3af").grid(row=5, column=0, sticky="w")

        # Initially show Appearance
        behavior_section.grid_remove()
        update_section_view()
        
        def close_settings():
            try: settings_window.destroy()
            except Exception: pass
            globals()['CURRENT_SETTINGS_WINDOW'] = None
            globals()['USER_INTENDS_SETTINGS'] = False
        settings_window.protocol("WM_DELETE_WINDOW", close_settings)
        
        # Improved close button
        button_frame = ctk.CTkFrame(content, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0,16))
        button_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(button_frame, text="Close", command=close_settings, fg_color="#6b7280", hover_color="#4b5563", font=styles_obj.CALLOUT_FONT, height=36).grid(row=0, column=0, sticky="e")
    else:
        settings_window = tk.Toplevel(root_app)
        CURRENT_SETTINGS_WINDOW = settings_window
        settings_window.title("Settings")
        settings_window.resizable(False, False)
        settings_window.transient(root_app)
        settings_window.lift()
        settings_window.focus_force()
        try:
            settings_window.attributes('-topmost', True)
        except Exception:
            pass
        try:
            if os.path.exists(LOGO_ICO_PATH):
                settings_window.iconbitmap(LOGO_ICO_PATH)
                settings_window.wm_iconbitmap(LOGO_ICO_PATH)
        except Exception:
            pass
        width, height = 600, 420
        try:
            root_app.update_idletasks()
            rx, ry = root_app.winfo_rootx(), root_app.winfo_rooty()
            rw, rh = root_app.winfo_width(), root_app.winfo_height()
            x = rx + (rw - width)//2
            y = ry + (rh - height)//2
            settings_window.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            settings_window.geometry(f"{width}x{height}")
        
        container = ttk.Frame(settings_window, padding=16)
        container.pack(fill="both", expand=True)
        left = ttk.Frame(container, width=160)
        left.pack(side="left", fill="y", padx=(0,12))
        ttk.Label(left, text="Settings", font=TITLE_FONT).pack(anchor="w", padx=8, pady=(6,12))
        def update_section_view():
            appearance.pack_forget(); behavior.pack_forget()
            if current_section.get() == "Appearance":
                appearance.pack(fill="x")
            else:
                behavior.pack(fill="x")
            close_btn.pack(anchor="e", pady=(12,0))
        def select_section(name):
            current_section.set(name); update_section_view()
        ttk.Button(left, text="Appearance", command=lambda: select_section("Appearance")).pack(fill="x")
        ttk.Button(left, text="Behavior", command=lambda: select_section("Behavior")).pack(fill="x", pady=(4,0))
        
        right = ttk.Frame(container)
        right.pack(side="left", fill="both", expand=True)
        
        appearance = ttk.LabelFrame(right, text="Appearance", padding=12)
        ttk.Label(appearance, text="Theme:").pack(anchor="w", pady=(0,5))
        current_config = load_config(); current_theme = current_config.get("theme", "system")
        theme_var = tk.StringVar(value=current_theme)
        def on_theme_change(): apply_theme(theme_var.get())
        radios = ttk.Frame(appearance); radios.pack(anchor="w", pady=(0,10))
        ttk.Radiobutton(radios, text="Light", variable=theme_var, value="light", command=on_theme_change).pack(anchor="w")
        ttk.Radiobutton(radios, text="Dark", variable=theme_var, value="dark", command=on_theme_change).pack(anchor="w")
        ttk.Radiobutton(radios, text="System", variable=theme_var, value="system", command=on_theme_change).pack(anchor="w")
        
        behavior = ttk.LabelFrame(right, text="Behavior", padding=12)
        ttk.Label(behavior, text="Folder Organization Mode:").pack(anchor="w", pady=(0,5))
        current_mode = current_config.get("organize_mode", "current")
        mode_var = tk.StringVar(value=current_mode)
        def on_mode_change(): apply_organize_mode(mode_var.get())
        ttk.Radiobutton(behavior, text="Classic Session", variable=mode_var, value="current", command=on_mode_change).pack(anchor="w")
        ttk.Label(behavior, text="Creates a session folder and organizes by categories (e.g., Session_01/Images).", foreground="#6b7280").pack(anchor="w", padx=(24,0), pady=(0,8))
        ttk.Radiobutton(behavior, text="Chronological (Date First)", variable=mode_var, value="date_then_type", command=on_mode_change).pack(anchor="w")
        ttk.Label(behavior, text="Groups by capture date, then by file type (e.g., 2025/10/22/Images).", foreground="#6b7280").pack(anchor="w", padx=(24,0), pady=(0,8))
        ttk.Radiobutton(behavior, text="Collections (Type First)", variable=mode_var, value="type_then_date", command=on_mode_change).pack(anchor="w")
        ttk.Label(behavior, text="Groups by file type, then by capture date (e.g., Images/2025/10/22).", foreground="#6b7280").pack(anchor="w", padx=(24,0))

        def close_settings():
            try: settings_window.destroy()
            except Exception: pass
            globals()['CURRENT_SETTINGS_WINDOW'] = None
            globals()['USER_INTENDS_SETTINGS'] = False
        
        settings_window.protocol("WM_DELETE_WINDOW", close_settings)
        ttk.Button(right, text="Close", command=close_settings).pack(anchor="e", pady=(12,0))

def build_gui():
    global dest_var, src_var, move_var, status_var, root_app, organize_btn, format_btn, log_text, logs_frame, logs_toggle_btn, logs_visible, progress_bar
    if 'USE_CTK' in globals() and USE_CTK:
        root = ctk.CTk(); root.title("")
        set_window_icon(root)
        styles_obj = apply_styles(root, use_ctk=True)
        
        # New Apple-style typographic hierarchy
        LARGE_TITLE_FONT = styles_obj.LARGE_TITLE_FONT
        TITLE_1_FONT = styles_obj.TITLE_1_FONT
        TITLE_2_FONT = styles_obj.TITLE_2_FONT
        TITLE_3_FONT = styles_obj.TITLE_3_FONT
        HEADLINE_FONT = styles_obj.HEADLINE_FONT
        BODY_FONT = styles_obj.BODY_FONT
        CALLOUT_FONT = styles_obj.CALLOUT_FONT
        SUBHEADLINE_FONT = styles_obj.SUBHEADLINE_FONT
        FOOTNOTE_FONT = styles_obj.FOOTNOTE_FONT
        CAPTION_1_FONT = styles_obj.CAPTION_1_FONT
        MONOSPACE_FONT = styles_obj.MONOSPACE_FONT
        EMOJI_FONT = styles_obj.EMOJI_FONT
        
        # Compatibility with existing code
        TITLE_FONT = styles_obj.TITLE_FONT
        SMALL_FONT = styles_obj.SMALL_FONT
        LABEL_FONT_BOLD = styles_obj.LABEL_FONT_BOLD
        BASE_FONT = styles_obj.BASE_FONT
        ENTRY_FONT = styles_obj.ENTRY_FONT
        
        root_app = root
        dest_var = tk.StringVar(root)
        src_var = tk.StringVar(root)
        move_var = tk.BooleanVar(root, value=False)
        status_var = tk.StringVar(root, value="")
        root.grid_columnconfigure(0, weight=1); root.grid_rowconfigure(1, weight=1)
        
        # Header with improved design
        header = ctk.CTkFrame(root, corner_radius=0, height=50)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        # Title con fuente más prominente
        title_label = ctk.CTkLabel(header, text="Archivium", font=TITLE_1_FONT)
        title_label.grid(row=0, column=0, sticky="w", padx=20, pady=12)

        # Settings button
        settings_btn = ctk.CTkButton(
            header, 
            text="⚙️", 
            font=EMOJI_FONT, 
            command=open_settings,
            fg_color="#6b7280",
            hover_color="#4b5563",
            width=40,
            height=30
        )
        settings_btn.grid(row=0, column=1, sticky="e", padx=20, pady=12)
        
        # Main content area
        main_frame = ctk.CTkFrame(root, corner_radius=12)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(6,12))
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Config frame
        config_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        config_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        config_frame.grid_columnconfigure(1, weight=1)
        
        # Destination folder selection
        ctk.CTkLabel(config_frame, text="Destination", font=HEADLINE_FONT).grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(12,2))
        ctk.CTkLabel(config_frame, text="Choose your default output folder", font=SUBHEADLINE_FONT, text_color="#9ca3af").grid(row=1, column=0, columnspan=3, sticky="w", padx=12, pady=(0,8))
        
        dest_row = ctk.CTkFrame(config_frame)
        dest_row.grid(row=2, column=0, columnspan=3, sticky="ew", padx=12, pady=(0,16))
        dest_row.grid_columnconfigure(0, weight=1)
        dest_row.grid_columnconfigure(1, weight=0)
        dest_entry = ctk.CTkEntry(dest_row, textvariable=dest_var, font=BODY_FONT, height=36)
        dest_entry.grid(row=0, column=0, sticky="ew", padx=(0,8))
        btn_dest = ctk.CTkButton(dest_row, text="📁", font=EMOJI_FONT, corner_radius=6, command=pick_dest, fg_color="#1f2937", hover_color="#374151", text_color="#e2e8f0", width=48, height=36)
        btn_dest.grid(row=0, column=1, sticky="e")
        
        # Source folder selection
        ctk.CTkLabel(config_frame, text="Source", font=HEADLINE_FONT).grid(row=3, column=0, columnspan=3, sticky="w", padx=12, pady=(0,2))
        ctk.CTkLabel(config_frame, text="Select SD card or folder to organize", font=SUBHEADLINE_FONT, text_color="#9ca3af").grid(row=4, column=0, columnspan=3, sticky="w", padx=12, pady=(0,8))
        
        src_row = ctk.CTkFrame(config_frame)
        src_row.grid(row=5, column=0, columnspan=3, sticky="ew", padx=12, pady=(0,16))
        src_row.grid_columnconfigure(0, weight=1)
        src_row.grid_columnconfigure(1, weight=0)
        src_entry = ctk.CTkEntry(src_row, textvariable=src_var, font=BODY_FONT, height=36)
        src_entry.grid(row=0, column=0, sticky="ew", padx=(0,8))
        btn_src = ctk.CTkButton(src_row, text="📁", font=EMOJI_FONT, corner_radius=6, command=pick_src, fg_color="#1f2937", hover_color="#374151", text_color="#e2e8f0", width=48, height=36)
        btn_src.grid(row=0, column=1, sticky="e")
        
        # Switch mover con mejor tipografía
        move_switch = ctk.CTkSwitch(config_frame, text="Move instead of copy", variable=move_var, onvalue=True, offvalue=False, font=CALLOUT_FONT)
        move_switch.grid(row=6, column=0, columnspan=3, sticky="w", padx=12, pady=(0,4))
        ctk.CTkLabel(config_frame, text="Files will be deleted from source location", font=FOOTNOTE_FONT, text_color="#9ca3af").grid(row=7, column=0, columnspan=3, sticky="w", padx=12, pady=(0,16))
        
        # Buttons frame
        button_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        button_frame.grid(row=8, column=0, columnspan=3, sticky="ew", padx=12, pady=(0,12))
        button_frame.grid_columnconfigure(0, weight=0)
        button_frame.grid_columnconfigure(1, weight=0)
        button_frame.grid_columnconfigure(2, weight=1)
        
        logs_toggle_btn = ctk.CTkButton(button_frame, text="Show Log", command=toggle_logs, fg_color="#334155", hover_color="#475569", text_color="#e2e8f0", font=CALLOUT_FONT, height=36)
        logs_toggle_btn.grid(row=0, column=0, sticky="w", padx=(0,12))
        
        organize_btn = ctk.CTkButton(button_frame, text="Organize Files", command=organize, fg_color="#2563eb", hover_color="#1d4ed8", text_color="#ffffff", font=CALLOUT_FONT, height=36)
        organize_btn.grid(row=0, column=1, sticky="w")
        
        # Status and progress frame
        status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        status_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0,4))
        ctk.CTkLabel(status_frame, textvariable=status_var, font=SUBHEADLINE_FONT).grid(row=0, column=0, sticky="w")
        
        progress_bar = ctk.CTkProgressBar(main_frame, height=6)
        progress_bar.grid(row=2, column=0, columnspan=3, sticky="ew", padx=12, pady=(0,12))
        progress_bar.set(0)
        progress_bar.grid_remove()
        
        # Logs frame
        logs_frame = ctk.CTkFrame(main_frame, corner_radius=8)
        logs_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=12, pady=(6,0))
        
        log_header = ctk.CTkFrame(logs_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,4))
        ctk.CTkLabel(log_header, text="Activity Log", font=TITLE_3_FONT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(log_header, text="Real-time transfer progress and details", font=CAPTION_1_FONT, text_color="#9ca3af").grid(row=1, column=0, sticky="w", pady=(2,0))
        
        log_text = ctk.CTkTextbox(logs_frame, width=560, height=180, font=MONOSPACE_FONT)
        log_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,8))
        logs_frame.grid_columnconfigure(0, weight=1); logs_frame.grid_rowconfigure(1, weight=1)
        # Collapse by default
        logs_visible = False
        logs_frame.grid_remove()
        main_frame.grid_rowconfigure(3, weight=1)
        
        # Apply saved theme
        cfg = load_config()
        saved_theme = cfg.get("theme", "system")
        apply_theme(saved_theme)
        
        if cfg.get("default_dest"): dest_var.set(cfg["default_dest"]) 
        return root
    else:
        root = tk.Tk(); root.title("")
        clear_window_icon(root)
        styles_obj = apply_styles(root, use_ctk=False)
        root_app = root
        dest_var = tk.StringVar(root)
        src_var = tk.StringVar(root)
        move_var = tk.BooleanVar(root, value=False)
        status_var = tk.StringVar(root, value="")
        
        # Main container frame
        main_container = ttk.Frame(root)
        main_container.pack(fill="both", expand=True)
        
        # Header frame
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill="x", padx=10, pady=(10, 0))
        
        # Title label
        title_label = ttk.Label(header_frame, text="Archivium", font=("Arial", 16, "bold"))
        title_label.pack(side="left")
        
        # Settings button
        settings_btn = ttk.Button(header_frame, text="⚙️", command=open_settings, width=3)
        settings_btn.pack(side="right")
        
        frm = ttk.Frame(main_container, padding=10); frm.pack(fill="both", expand=True)
        frm.columnconfigure(0, weight=1)
        frm.columnconfigure(1, weight=0)
        ttk.Label(frm,text="Destination (default):", style='FieldLabel.TLabel').grid(row=0,column=0,columnspan=3,sticky="w")
        dest_row = ttk.Frame(frm)
        dest_row.grid(row=1,column=0,columnspan=3,sticky="ew")
        dest_row.columnconfigure(0, weight=1); dest_row.columnconfigure(1, weight=0)
        ttk.Entry(dest_row,textvariable=dest_var, style='Modern.TEntry').grid(row=0,column=0,sticky="ew", padx=(0,6))
        ttk.Button(dest_row,text="📁",width=3,command=pick_dest, style='IconGhost.TButton').grid(row=0,column=1,sticky="e", padx=(6,0))
        ttk.Label(frm,text="Source (SD/Folder):", style='FieldLabel.TLabel').grid(row=2,column=0,columnspan=3,sticky="w")
        src_row = ttk.Frame(frm)
        src_row.grid(row=3,column=0,columnspan=3,sticky="ew")
        src_row.columnconfigure(0, weight=1); src_row.columnconfigure(1, weight=0)
        ttk.Entry(src_row,textvariable=src_var, style='Modern.TEntry').grid(row=0,column=0,sticky="ew", padx=(0,6))
        ttk.Button(src_row,text="📁",width=3,command=pick_src, style='IconGhost.TButton').grid(row=0,column=1,sticky="e", padx=(6,0))
        # Switch mover
        ttk.Checkbutton(frm,text="Move instead of copy (deletes from source)",variable=move_var, style='Compact.TCheckbutton').grid(row=4,column=0,columnspan=2,sticky="w",pady=(4,8))
        # Log toggle button
        logs_toggle_btn = ttk.Button(frm,text="Show log",command=toggle_logs, style='Ghost.TButton')
        logs_toggle_btn.grid(row=5,column=0,sticky="w")
        organize_btn = ttk.Button(frm,text="Organize",command=organize, style='Primary.TButton'); organize_btn.grid(row=5,column=1,sticky="w")

        # Status label
        ttk.Label(frm,textvariable=status_var, style='FieldLabel.TLabel').grid(row=6,column=0,columnspan=3,sticky="w",pady=(4,4))
        progress_bar = ttk.Progressbar(frm, maximum=100, mode="determinate")
        progress_bar.grid(row=7,column=0,columnspan=3,sticky="ew",pady=(0,8))
        progress_bar.configure(value=0)
        logs_frame = ttk.Frame(frm)
        logs_frame.grid(row=8,column=0,columnspan=3,sticky="nsew",pady=(6,0))
        ttk.Label(logs_frame,text="Log:", style='FieldLabel.TLabel').grid(row=0,column=0,sticky="nw")
        log_text = tk.Text(logs_frame,height=10,width=80,state="disabled",bg="#0f172a",fg="#e5e7eb",relief="flat",highlightthickness=1,highlightbackground="#334155")
        log_text.grid(row=1,column=0,sticky="nsew")
        scroll = ttk.Scrollbar(logs_frame,orient="vertical",command=log_text.yview); log_text.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1,column=1,sticky="ns")
        logs_frame.columnconfigure(0, weight=1); logs_frame.rowconfigure(1, weight=1)
        logs_visible = False
        logs_frame.grid_remove()
        frm.columnconfigure(0, weight=1); frm.rowconfigure(8, weight=1)
        cfg = load_config();
        if cfg.get("default_dest"): dest_var.set(cfg["default_dest"]) 
        return root

if __name__ == "__main__":
    app = build_gui()
    app.mainloop()