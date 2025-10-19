import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from dataclasses import dataclass

try:
    import customtkinter as ctk
except Exception:
    ctk = None

@dataclass
class Styles:
    UI_FONT_FAMILY: str = "Arial"
    BASE_FONT: object | None = None
    TITLE_FONT: object | None = None
    SMALL_FONT: object | None = None
    LABEL_FONT_BOLD: object | None = None
    EMOJI_FONT: object | None = None
    ENTRY_FONT: object | None = None


def pick_font_family(root: tk.Misc) -> str:
    try:
        fams = set(tkfont.families(root))
    except Exception:
        fams = set()
    for name in ['Roboto', 'Poppins', 'Segoe UI', 'Arial']:
        if name in fams:
            return name
    return 'Arial'


def apply_styles(root: tk.Misc, use_ctk: bool = True) -> Styles:
    """Configura estilos (CTk o ttk) y devuelve fuentes y tema.
    - CTk: establece modo y tema por defecto y crea fuentes de UI.
    - ttk: aplica una paleta compacta y moderna con estilos nombrados.
    """
    s = Styles()
    s.UI_FONT_FAMILY = pick_font_family(root)

    if use_ctk and ctk is not None:
        try:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            s.BASE_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=12)
            s.TITLE_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=16, weight="bold")
            s.SMALL_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=11)
            s.LABEL_FONT_BOLD = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=12, weight="bold")
            s.EMOJI_FONT = ctk.CTkFont(family="Segoe UI Emoji", size=16)
            s.ENTRY_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=13)
        except Exception:
            # en CTk cualquier fallo no debe romper la app; devolvemos estilos básicos
            pass
        return s

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
    style.configure('FieldLabel.TLabel', background=base_bg, foreground=text_fg, font=(s.UI_FONT_FAMILY, 10, 'bold'))
    style.configure('Muted.TLabel', background=base_bg, foreground='#9ca3af', font=(s.UI_FONT_FAMILY, 9))
    style.configure('Modern.TEntry', fieldbackground='#111827', foreground=text_fg, font=(s.UI_FONT_FAMILY, 11))
    style.map('Modern.TEntry', fieldbackground=[('focus', '#111827')])
    style.configure('Compact.TCheckbutton', background=base_bg, foreground=text_fg, font=(s.UI_FONT_FAMILY, 10))
    style.configure('Primary.TButton', font=(s.UI_FONT_FAMILY, 10), padding=6, foreground='#ffffff', background='#2563eb')
    style.map('Primary.TButton', background=[('active', '#1d4ed8'), ('disabled', '#1e40af')], foreground=[('disabled', '#cbd5e1')])
    style.configure('Ghost.TButton', font=(s.UI_FONT_FAMILY, 10), padding=6, foreground=text_fg, background='#334155')
    style.map('Ghost.TButton', background=[('active', '#475569')])
    style.configure('Danger.TButton', font=(s.UI_FONT_FAMILY, 10), padding=6, foreground='#ffffff', background='#ef4444')
    style.map('Danger.TButton', background=[('active', '#dc2626'), ('disabled', '#b91c1c')], foreground=[('disabled', '#fca5a5')])
    style.configure('IconGhost.TButton', font=('Segoe UI Emoji', 11), padding=6, foreground=text_fg, background='#334155')
    style.map('IconGhost.TButton', background=[('active', '#475569')])
    return s