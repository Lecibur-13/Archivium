import os, json, subprocess, datetime, re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkfont
from styles import apply_styles
# Añadimos soporte de imágenes (Pillow) si está disponible
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
# Referencias de iconos para evitar garbage collection
icons = {}

APP_NAME = "Archivium"
APP_ID = "Archivium"
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_ID)
CONFIG_PATH = os.path.join(APPDATA_DIR, "config.json")
DEFAULT_CONFIG = {"default_dest": ""}

JPEG_PATTERNS = ["*.jpg","*.jpeg","*.jpe","*.jfif"]
RAW_PATTERNS  = ["*.cr2","*.cr3","*.nef","*.raf","*.arw","*.rw2","*.dng","*.orf","*.sr2","*.pef","*.nrw"]
VIDEO_PATTERNS= ["*.mp4","*.mov","*.avi","*.mts","*.mxf","*.mpg","*.mpeg","*.mkv","*.wmv","*.3gp"]

log_text = None
format_btn = None
organize_btn = None
root_app = None
logs_frame = None
logs_toggle_btn = None
logs_visible = False
# Fuente seleccionada y fuentes CTk (si corresponde)
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
    # Si estamos en hilo secundario, despachar al hilo principal
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
        for name in os.listdir(base):
            dpath = os.path.join(base,name)
            if os.path.isdir(dpath) and name.startswith(prefix):
                m = re.match(rf"^{re.escape(date_str)}_(\d+)$", name)
                if m:
                    n = int(m.group(1)); seq = max(seq, n+1)
    except FileNotFoundError: os.makedirs(base, exist_ok=True)
    return f"{date_str}_{seq:03d}"

def ensure_dirs(*dirs):
    for d in dirs: os.makedirs(d, exist_ok=True)

def detect_drive_letter(path):
    drive,_ = os.path.splitdrive(os.path.abspath(path))
    return drive[0].upper() if drive and len(drive)>=2 and drive[1]==":" else None

def robocopy_available():
    from shutil import which
    return which("robocopy") is not None

def transfer_with_robocopy(src, dest, patterns, move=False):
    # Excluir carpetas de sistema al usar la raíz de la SD
    exclude_dirs = ["$RECYCLE.BIN","System Volume Information"]
    cmd = ["robocopy", src, dest] + patterns + ["/S","/R:1","/W:2","/MT:16","/NP","/NFL","/NDL","/XD"] + exclude_dirs
    if move: cmd.append("/MOV")
    log("Ejecutando: "+" ".join(cmd))
    p = subprocess.run(cmd, capture_output=True, text=True)
    log(p.stdout.strip() or "(sin salida)")
    if p.stderr.strip(): log("STDERR: "+p.stderr.strip())
    if p.returncode > 7: raise RuntimeError(f"robocopy fallo con codigo {p.returncode}")

# Nuevo: generar nombres únicos en destino para evitar colisiones

def unique_dest_path(dest, filename):
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(dest, filename)
    idx = 2
    while os.path.exists(candidate):
        candidate = os.path.join(dest, f"{base}_{idx:02d}{ext}")
        idx += 1
    return candidate

# Plano: copiar/mover sin subcarpetas, solo archivos que coinciden

def transfer_with_python(src, dest, patterns, move=False, progress_cb=None, kind=None):
    import fnmatch, shutil
    count = 0
    exclude_dirs = {"$RECYCLE.BIN","System Volume Information"}
    for root,dirs,files in os.walk(src):
        # filtrar directorios excluidos
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for fn in files:
            f = fn.lower()
            if any(fnmatch.fnmatch(f, pat.lower()) for pat in patterns):
                src_path = os.path.join(root,fn)
                target = unique_dest_path(dest, fn)
                if move:
                    shutil.move(src_path, target)
                else:
                    shutil.copy2(src_path, target)
                count += 1
                if progress_cb:
                    try:
                        progress_cb(1, fn, kind or "Files")
                    except Exception:
                        pass
                if count % 100 == 0:
                    log(f"{count} files copied to {dest}")
    log(f"Copied {count} files to {dest} (flat)")

def do_transfer(src, session_dir, move=False):
    jpeg_dir = os.path.join(session_dir,"JPEG")
    raw_dir  = os.path.join(session_dir,"RAW")
    video_dir= os.path.join(session_dir,"Video")

    # Helpers: contar y actualizar progreso
    def count_matching_files(src_dir, patterns):
        import fnmatch
        total = 0
        exclude_dirs = {"$RECYCLE.BIN","System Volume Information"}
        for r, d, files in os.walk(src_dir):
            d[:] = [x for x in d if x not in exclude_dirs]
            for fn in files:
                f = fn.lower()
                if any(fnmatch.fnmatch(f, pat.lower()) for pat in patterns):
                    total += 1
        return total

    def update_progress(pct, kind, filename):
        import threading
        text = f"Copying {kind}: {int(pct*100)}% — {filename}"
        def _ui():
            try:
                status_var.set(text)
            except Exception:
                pass
            try:
                if progress_bar is not None:
                    if 'USE_CTK' in globals() and USE_CTK:
                        progress_bar.set(pct)
                    else:
                        progress_bar['value'] = int(pct*100)
            except Exception:
                pass
        if threading.current_thread() is threading.main_thread():
            _ui()
        else:
            root_app.after(0, _ui)

    total_jpeg = count_matching_files(src, JPEG_PATTERNS)
    total_raw  = count_matching_files(src, RAW_PATTERNS)
    total_video= count_matching_files(src, VIDEO_PATTERNS)
    total_all = total_jpeg + total_raw + total_video
    done = {"count": 0}

    update_progress(0.0, "Scanning", "")

    ensure_dirs(jpeg_dir, raw_dir, video_dir)
    # Modo plano: no mantener subcarpetas del origen
    log("Separating: JPEG, RAW, Video (flat mode)")

    def progress_cb(increment, filename, kind):
        done["count"] += increment
        pct = 0.0 if total_all == 0 else done["count"] / total_all
        update_progress(pct, kind, filename)

    transfer_with_python(src, jpeg_dir, JPEG_PATTERNS, move=move, progress_cb=progress_cb, kind="JPEG")
    transfer_with_python(src, raw_dir,  RAW_PATTERNS,  move=move, progress_cb=progress_cb, kind="RAW")
    transfer_with_python(src, video_dir,VIDEO_PATTERNS, move=move, progress_cb=progress_cb, kind="Video")

def organize():
    src = src_var.get().strip(); dest = dest_var.get().strip(); move = move_var.get()
    if not dest:
        messagebox.showerror(APP_NAME, "Select destination folder."); return
    if not src:
        messagebox.showerror(APP_NAME, "Select source folder."); return
    session_name = next_sequence_folder(dest); session_dir = os.path.join(dest,session_name)
    ensure_dirs(session_dir); log(f"Session: {session_dir}")

    # Deshabilitar UI mientras corre
    def set_busy(state: bool):
        organize_btn.configure(state="disabled" if state else "normal")
        format_btn.configure(state="disabled")
    set_busy(True)

    # Reset progreso
    try:
        status_var.set("Starting...")
        if progress_bar is not None:
            if 'USE_CTK' in globals() and USE_CTK:
                progress_bar.set(0.0)
            else:
                progress_bar.configure(value=0)
    except Exception:
        pass

    import threading
    def _worker():
        try:
            do_transfer(src, session_dir, move=move)
            log("Transfer complete.")
            root_app.after(0, format_btn.configure, {"state":"normal"})
            root_app.after(0, status_var.set, f"Done: {session_dir}")
            # Completar barra
            try:
                if 'USE_CTK' in globals() and USE_CTK:
                    root_app.after(0, progress_bar.set, 1.0)
                else:
                    root_app.after(0, progress_bar.configure, {"value":100})
            except Exception:
                pass
            root_app.after(0, messagebox.showinfo, APP_NAME, "Transfer finished. You may format the SD if you want.")
        except Exception as e:
            log("Error: "+str(e))
            root_app.after(0, messagebox.showerror, APP_NAME, f"Error during transfer:\n{e}")
        finally:
            root_app.after(0, set_busy, False)
            root_app.after(0, hide_progress)
    threading.Thread(target=_worker, daemon=True).start()

def format_sd():
    src = src_var.get().strip()
    if not src: messagebox.showerror(APP_NAME, "Select source to detect the SD."); return
    drive = detect_drive_letter(src)
    if not drive: messagebox.showerror(APP_NAME, "SD drive not detected."); return
    ok = messagebox.askyesno(APP_NAME, f"WARNING: {drive}: will be formatted. Confirm?")
    if not ok: return
    ps_cmd = ["powershell","-NoProfile","-Command",f"Format-Volume -DriveLetter {drive} -FileSystem exFAT -Force -Confirm:$false -NewFileSystemLabel 'CAMERA'"]
    log("Formatting SD: "+" ".join(ps_cmd))
    p = subprocess.run(ps_cmd, capture_output=True, text=True)
    if p.returncode != 0:
        log("STDERR: "+(p.stderr.strip() or ""))
        messagebox.showerror(APP_NAME, f"Could not format SD.\nExit code: {p.returncode}\n{p.stderr}")
    else:
        log(p.stdout.strip() or "Format complete.")
        messagebox.showinfo(APP_NAME, f"SD {drive}: formatted successfully.")
# --- Icono de carpeta dibujado ---
def _make_folder_pil(size=24, color="#e5e7eb"):
    if Image is None or ImageDraw is None:
        return None
    img = Image.new("RGBA", (size, size), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # pestaña
    d.rounded_rectangle([size*0.12, size*0.18, size*0.46, size*0.38], radius=int(size*0.08), fill=color)
    # cuerpo
    d.rounded_rectangle([size*0.10, size*0.30, size*0.88, size*0.86], radius=int(size*0.12), fill=color)
    return img

def make_ctk_folder_icon(size=20, color="#e5e7eb"):
    if not ('USE_CTK' in globals() and USE_CTK) or Image is None:
        return None
    try:
        return ctk.CTkImage(light_image=_make_folder_pil(size, color), dark_image=_make_folder_pil(size, color), size=(size, size))
    except Exception:
        return None

def make_tk_folder_icon(root, size=16, color="#e5e7eb"):
    if Image is None or ImageTk is None:
        return None
    try:
        pil = _make_folder_pil(size, color)
        return ImageTk.PhotoImage(pil)
    except Exception:
        return None

def pick_font_family(root):
    try:
        fams = set(tkfont.families(root))
    except Exception:
        fams = set()
    for name in ['Roboto', 'Poppins', 'Segoe UI', 'Arial']:
        if name in fams:
            return name
    return 'Arial'

def init_style(root):
    global UI_FONT_FAMILY, BASE_FONT, TITLE_FONT, SMALL_FONT, LABEL_FONT_BOLD, EMOJI_FONT, ENTRY_FONT
    UI_FONT_FAMILY = pick_font_family(root)
    if 'USE_CTK' in globals() and USE_CTK:
        try:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            BASE_FONT = ctk.CTkFont(family=UI_FONT_FAMILY, size=12)
            TITLE_FONT = ctk.CTkFont(family=UI_FONT_FAMILY, size=16, weight="bold")
            SMALL_FONT = ctk.CTkFont(family=UI_FONT_FAMILY, size=11)
            LABEL_FONT_BOLD = ctk.CTkFont(family=UI_FONT_FAMILY, size=12, weight="bold")
            # Fuente para emoji visible en Windows
            EMOJI_FONT = ctk.CTkFont(family="Segoe UI Emoji", size=16)
            ENTRY_FONT = ctk.CTkFont(family=UI_FONT_FAMILY, size=13)
        except Exception:
            pass
        return
    # Fallback ttk (sobrio y compacto)
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except Exception:
        pass
    root.configure(bg='#0f1115')
    base_bg = '#0f1115'
    text_fg = '#e5e7eb'
    style.configure('TFrame', background=base_bg)
    style.configure('FieldLabel.TLabel', background=base_bg, foreground=text_fg, font=(UI_FONT_FAMILY, 10, 'bold'))
    style.configure('Muted.TLabel', background=base_bg, foreground='#9ca3af', font=(UI_FONT_FAMILY, 9))
    style.configure('Modern.TEntry', fieldbackground='#111827', foreground=text_fg, font=(UI_FONT_FAMILY, 11))
    style.map('Modern.TEntry', fieldbackground=[('focus', '#111827')])
    style.configure('Compact.TCheckbutton', background=base_bg, foreground=text_fg, font=(UI_FONT_FAMILY, 10))
    style.configure('Primary.TButton', font=(UI_FONT_FAMILY, 10), padding=6, foreground='#ffffff', background='#2563eb')
    style.map('Primary.TButton', background=[('active', '#1d4ed8'), ('disabled', '#1e40af')], foreground=[('disabled', '#cbd5e1')])
    style.configure('Ghost.TButton', font=(UI_FONT_FAMILY, 10), padding=6, foreground=text_fg, background='#334155')
    style.map('Ghost.TButton', background=[('active', '#475569')])
    style.configure('Danger.TButton', font=(UI_FONT_FAMILY, 10), padding=6, foreground='#ffffff', background='#ef4444')
    style.map('Danger.TButton', background=[('active', '#dc2626'), ('disabled', '#b91c1c')], foreground=[('disabled', '#fca5a5')])
    # Estilo específico para botones de icono con fuente emoji
    style.configure('IconGhost.TButton', font=('Segoe UI Emoji', 11), padding=6, foreground=text_fg, background='#334155')
    style.map('IconGhost.TButton', background=[('active', '#475569')])

def toggle_logs():
    global logs_visible
    if logs_visible:
        logs_frame.grid_remove()
        logs_toggle_btn.configure(text='Show log')
        logs_visible = False
    else:
        logs_frame.grid()
        logs_toggle_btn.configure(text='Hide log')
        logs_visible = True

# Mostrar/ocultar barra de progreso
def show_progress():
    global progress_visible
    try:
        if 'USE_CTK' in globals() and USE_CTK:
            if progress_bar is not None:
                progress_bar.set(0.0)
                progress_bar.grid()
        else:
            if progress_bar is not None:
                progress_bar.configure(value=0)
                progress_bar.grid()
        progress_visible = True
    except Exception:
        pass

def hide_progress():
    global progress_visible
    try:
        if progress_bar is not None:
            progress_bar.grid_remove()
        progress_visible = False
        # Limpiar estado textual opcionalmente
        try:
            status_var.set("")
        except Exception:
            pass
    except Exception:
        pass

def build_gui():
    global dest_var, src_var, move_var, status_var, root_app, organize_btn, format_btn, log_text, logs_frame, logs_toggle_btn, logs_visible, progress_bar
    if 'USE_CTK' in globals() and USE_CTK:
        root = ctk.CTk(); root.title(APP_NAME)
        styles_obj = apply_styles(root, use_ctk=True)
        # Fuentes locales tomadas del módulo de estilos
        TITLE_FONT = styles_obj.TITLE_FONT
        SMALL_FONT = styles_obj.SMALL_FONT
        LABEL_FONT_BOLD = styles_obj.LABEL_FONT_BOLD
        BASE_FONT = styles_obj.BASE_FONT
        EMOJI_FONT = styles_obj.EMOJI_FONT
        ENTRY_FONT = styles_obj.ENTRY_FONT
        root_app = root
        dest_var = tk.StringVar(root)
        src_var = tk.StringVar(root)
        move_var = tk.BooleanVar(root, value=False)
        status_var = tk.StringVar(root, value="")
        root.grid_columnconfigure(0, weight=1); root.grid_rowconfigure(1, weight=1)
        # Header
        header = ctk.CTkFrame(root, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12,6))
        title = ctk.CTkLabel(header, text=APP_NAME, font=TITLE_FONT)
        title.grid(row=0, column=0, sticky="w", padx=10, pady=8)
        def on_appearance(value):
            try:
                ctk.set_appearance_mode("light" if value == "Light" else "dark")
            except Exception:
                pass
        mode = ctk.CTkSegmentedButton(header, values=["Light","Dark"], command=on_appearance, font=SMALL_FONT)
        mode.set("Dark")
        mode.grid(row=0, column=1, sticky="e", padx=10, pady=8)
        header.grid_columnconfigure(0, weight=1)
        # Card de contenido
        frm = ctk.CTkFrame(root, corner_radius=12)
        frm.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0,12))
        # Col 0 expandible y col 1 fija (botón)
        frm.grid_columnconfigure(0, weight=1)
        frm.grid_columnconfigure(1, weight=0)
        # Fila destino
        ctk.CTkLabel(frm, text="Destination (default):", font=LABEL_FONT_BOLD).grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(12,4))
        dest_row = ctk.CTkFrame(frm)
        dest_row.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0,12))
        dest_row.grid_columnconfigure(0, weight=1)
        dest_row.grid_columnconfigure(1, weight=0)
        dest_entry = ctk.CTkEntry(dest_row, textvariable=dest_var, font=ENTRY_FONT, height=34)
        dest_entry.grid(row=0, column=0, sticky="ew", padx=(0,6))
        btn_dest = ctk.CTkButton(dest_row, text="📁", font=EMOJI_FONT, corner_radius=6, command=pick_dest, fg_color="#1f2937", hover_color="#374151", text_color="#e2e8f0", width=48, height=34)
        btn_dest.grid(row=0, column=1, sticky="e")
        # Fila origen
        ctk.CTkLabel(frm, text="Source (SD/Folder):", font=LABEL_FONT_BOLD).grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(0,4))
        src_row = ctk.CTkFrame(frm)
        src_row.grid(row=3, column=0, columnspan=3, sticky="ew", padx=12, pady=(0,12))
        src_row.grid_columnconfigure(0, weight=1)
        src_row.grid_columnconfigure(1, weight=0)
        src_entry = ctk.CTkEntry(src_row, textvariable=src_var, font=ENTRY_FONT, height=34)
        src_entry.grid(row=0, column=0, sticky="ew", padx=(0,6))
        btn_src = ctk.CTkButton(src_row, text="📁", font=EMOJI_FONT, corner_radius=6, command=pick_src, fg_color="#1f2937", hover_color="#374151", text_color="#e2e8f0", width=48, height=34)
        btn_src.grid(row=0, column=1, sticky="e")
        # Switch mover
        move_switch = ctk.CTkSwitch(frm, text="Move instead of copy (deletes from source)", variable=move_var, onvalue=True, offvalue=False, font=BASE_FONT)
        move_switch.grid(row=4, column=0, columnspan=3, sticky="w", padx=12, pady=(0,12))
        # Botones
        logs_toggle_btn = ctk.CTkButton(frm, text="Show log", command=toggle_logs, fg_color="#334155", hover_color="#475569", text_color="#e2e8f0", font=BASE_FONT)
        logs_toggle_btn.grid(row=5, column=0, sticky="w", padx=12, pady=(0,12))
        organize_btn = ctk.CTkButton(frm, text="Organize", command=organize, fg_color="#2563eb", hover_color="#1d4ed8", text_color="#ffffff", font=BASE_FONT)
        organize_btn.grid(row=5, column=1, sticky="w", padx=(0,12), pady=(0,12))
        format_btn = ctk.CTkButton(frm, text="Format SD", command=format_sd, fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff", font=BASE_FONT)
        format_btn.grid(row=5, column=2, sticky="w", padx=(0,12), pady=(0,12))
        format_btn.configure(state="disabled")
        # Estado y progreso
        ctk.CTkLabel(frm, textvariable=status_var, font=BASE_FONT).grid(row=6, column=0, columnspan=3, sticky="ew", padx=12, pady=(0,4))
        progress_bar = ctk.CTkProgressBar(frm)
        progress_bar.grid(row=7, column=0, columnspan=3, sticky="ew", padx=12, pady=(0,12))
        progress_bar.set(0)
        progress_bar.grid_remove()
        # Registro
        logs_frame = ctk.CTkFrame(frm, corner_radius=8)
        logs_frame.grid(row=8, column=0, columnspan=3, sticky="nsew", padx=12, pady=(6,0))
        ctk.CTkLabel(logs_frame, text="Log:", font=LABEL_FONT_BOLD).grid(row=0, column=0, sticky="nw", padx=8, pady=(8,4))
        log_text = ctk.CTkTextbox(logs_frame, width=560, height=180, font=BASE_FONT)
        log_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,8))
        logs_frame.grid_columnconfigure(0, weight=1); logs_frame.grid_rowconfigure(1, weight=1)
        # Colapsar por defecto
        logs_visible = False
        logs_frame.grid_remove()
        frm.grid_rowconfigure(8, weight=1)
        cfg = load_config();
        if cfg.get("default_dest"): dest_var.set(cfg["default_dest"]) 
        return root
    else:
        root = tk.Tk(); root.title(APP_NAME)
        _ = apply_styles(root, use_ctk=False)
        root_app = root
        dest_var = tk.StringVar(root)
        src_var = tk.StringVar(root)
        move_var = tk.BooleanVar(root, value=False)
        status_var = tk.StringVar(root, value="")
        frm = ttk.Frame(root, padding=10); frm.grid(row=0,column=0,sticky="nsew")
        root.columnconfigure(0, weight=1); root.rowconfigure(0, weight=1)
        # Col 0 expandible; col 1 ancho fijo (botón)
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
        # Botones
        logs_toggle_btn = ttk.Button(frm,text="Show log",command=toggle_logs, style='Ghost.TButton')
        logs_toggle_btn.grid(row=5,column=0,sticky="w")
        organize_btn = ttk.Button(frm,text="Organize",command=organize, style='Primary.TButton'); organize_btn.grid(row=5,column=1,sticky="w")
        format_btn = ttk.Button(frm,text="Format SD",command=format_sd, style='Danger.TButton'); format_btn.grid(row=5,column=2,sticky="w"); format_btn.configure(state="disabled")
        # Estado y progreso
        ttk.Label(frm,textvariable=status_var, style='FieldLabel.TLabel').grid(row=6,column=0,columnspan=3,sticky="w",pady=(4,4))
        progress_bar = ttk.Progressbar(frm, maximum=100, mode="determinate")
        progress_bar.grid(row=7,column=0,columnspan=3,sticky="ew",pady=(0,8))
        progress_bar.configure(value=0)
        # Frame de registro (colapsable)
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