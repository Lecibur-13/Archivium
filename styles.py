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
    # Jerarquía tipográfica al estilo Apple
    LARGE_TITLE_FONT: object | None = None      # 28pt, Bold - Para títulos principales
    TITLE_1_FONT: object | None = None          # 22pt, Bold - Títulos de sección
    TITLE_2_FONT: object | None = None          # 17pt, Bold - Subtítulos importantes
    TITLE_3_FONT: object | None = None          # 15pt, Semibold - Subtítulos menores
    HEADLINE_FONT: object | None = None         # 14pt, Semibold - Headlines
    BODY_FONT: object | None = None             # 13pt, Regular - Texto principal
    CALLOUT_FONT: object | None = None          # 12pt, Regular - Texto destacado
    SUBHEADLINE_FONT: object | None = None      # 11pt, Regular - Subtextos
    FOOTNOTE_FONT: object | None = None         # 10pt, Regular - Notas al pie
    CAPTION_1_FONT: object | None = None        # 9pt, Regular - Captions principales
    CAPTION_2_FONT: object | None = None        # 8pt, Regular - Captions secundarios
    
    # Fuentes especiales
    EMOJI_FONT: object | None = None
    MONOSPACE_FONT: object | None = None        # Para logs y código
    
    # Compatibilidad con código existente
    BASE_FONT: object | None = None
    TITLE_FONT: object | None = None
    SMALL_FONT: object | None = None
    LABEL_FONT_BOLD: object | None = None
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
            
            # Jerarquía tipográfica al estilo Apple
            s.LARGE_TITLE_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=28, weight="bold")
            s.TITLE_1_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=22, weight="bold")
            s.TITLE_2_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=17, weight="bold")
            s.TITLE_3_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=15, weight="bold")
            s.HEADLINE_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=14, weight="bold")
            s.BODY_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=13)
            s.CALLOUT_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=12)
            s.SUBHEADLINE_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=11)
            s.FOOTNOTE_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=10)
            s.CAPTION_1_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=9)
            s.CAPTION_2_FONT = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=8)
            
            # Fuentes especiales
            s.EMOJI_FONT = ctk.CTkFont(family="Segoe UI Emoji", size=16)
            s.MONOSPACE_FONT = ctk.CTkFont(family="Consolas", size=11)
            
            # Compatibilidad con código existente
            s.BASE_FONT = s.CALLOUT_FONT
            s.TITLE_FONT = s.TITLE_2_FONT
            s.SMALL_FONT = s.SUBHEADLINE_FONT
            s.LABEL_FONT_BOLD = ctk.CTkFont(family=s.UI_FONT_FAMILY, size=12, weight="bold")
            s.ENTRY_FONT = s.BODY_FONT
        except Exception:
            # en CTk cualquier fallo no debe romper la app; devolvemos estilos básicos
            pass
        return s

    # Fallback ttk (sobrio y compacto) con jerarquía tipográfica mejorada
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except Exception:
        pass
    root.configure(bg='#0f1115')
    base_bg = '#0f1115'
    text_fg = '#e5e7eb'
    
    # Configurar estilos ttk con jerarquía tipográfica
    style.configure('TFrame', background=base_bg)
    style.configure('LargeTitle.TLabel', background=base_bg, foreground=text_fg, font=(s.UI_FONT_FAMILY, 20, 'bold'))
    style.configure('Title1.TLabel', background=base_bg, foreground=text_fg, font=(s.UI_FONT_FAMILY, 16, 'bold'))
    style.configure('Title2.TLabel', background=base_bg, foreground=text_fg, font=(s.UI_FONT_FAMILY, 14, 'bold'))
    style.configure('Title3.TLabel', background=base_bg, foreground=text_fg, font=(s.UI_FONT_FAMILY, 12, 'bold'))
    style.configure('Headline.TLabel', background=base_bg, foreground=text_fg, font=(s.UI_FONT_FAMILY, 11, 'bold'))
    style.configure('Body.TLabel', background=base_bg, foreground=text_fg, font=(s.UI_FONT_FAMILY, 10))
    style.configure('Callout.TLabel', background=base_bg, foreground=text_fg, font=(s.UI_FONT_FAMILY, 10))
    style.configure('Subheadline.TLabel', background=base_bg, foreground=text_fg, font=(s.UI_FONT_FAMILY, 9))
    style.configure('Footnote.TLabel', background=base_bg, foreground='#9ca3af', font=(s.UI_FONT_FAMILY, 8))
    style.configure('Caption1.TLabel', background=base_bg, foreground='#9ca3af', font=(s.UI_FONT_FAMILY, 8))
    style.configure('Caption2.TLabel', background=base_bg, foreground='#9ca3af', font=(s.UI_FONT_FAMILY, 7))
    
    # Estilos existentes actualizados
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
