"""界面主题与样式常量。

集中管理颜色、字体、间距与通用 ttk 样式，保证各窗口视觉一致。
主色沿用实验二高保真原型中的品牌蓝 #1668D1。
"""

# 品牌与中性色板。
PRIMARY = "#1668D1"
PRIMARY_DARK = "#0E4FA8"
PRIMARY_LIGHT = "#E8F2FE"
ACCENT = "#E8552D"
BG = "#F4F6FA"
SURFACE = "#FFFFFF"
SIDEBAR = "#17233B"
TEXT = "#1F2937"
TEXT_MUTED = "#6B7280"
BORDER = "#E2E7EF"
SUCCESS = "#1F9E62"
SUCCESS_BG = "#E4F6EC"
DANGER = "#D64545"
DANGER_BG = "#FCEAEA"
WARNING = "#C98A12"
WARNING_BG = "#FBF3DD"

# 字体族与字号。
FONT_FAMILY = "Microsoft YaHei UI"
FONT_TITLE = (FONT_FAMILY, 18, "bold")
FONT_HEADING = (FONT_FAMILY, 14, "bold")
FONT_BODY = (FONT_FAMILY, 11)
FONT_SMALL = (FONT_FAMILY, 10)
FONT_BUTTON = (FONT_FAMILY, 11, "bold")

# 间距与圆角（tkinter 控件本身不支持圆角，仅用于布局参考）。
PADDING = 12
PADDING_SMALL = 8
RADIUS = 8


def configure_style(style) -> None:
    """配置全局 ttk 样式。"""
    style.theme_use("clam")
    style.configure("TFrame", background=BG)
    style.configure("Surface.TFrame", background=SURFACE)
    style.configure("Sidebar.TFrame", background=SIDEBAR)
    style.configure("TLabel", background=BG, foreground=TEXT, font=FONT_BODY)
    style.configure("Surface.TLabel", background=SURFACE, foreground=TEXT)
    style.configure("Muted.TLabel", background=BG, foreground=TEXT_MUTED,
                    font=FONT_SMALL)
    style.configure("Title.TLabel", background=BG, foreground=PRIMARY,
                    font=FONT_TITLE)
    style.configure("Heading.TLabel", background=SURFACE, foreground=TEXT,
                    font=FONT_HEADING)
    style.configure("Sidebar.TLabel", background=SIDEBAR, foreground="#FFFFFF",
                    font=FONT_BODY)
    style.configure("Primary.TButton", background=PRIMARY, foreground="#FFFFFF",
                    font=FONT_BUTTON, padding=8, borderwidth=0)
    style.map("Primary.TButton",
              background=[("active", PRIMARY_DARK), ("disabled", "#9DB8DC")])
    style.configure("TButton", font=FONT_BODY, padding=6)
    style.configure("Treeview", font=FONT_SMALL, rowheight=28,
                    fieldbackground=SURFACE, background=SURFACE)
    style.configure("Treeview.Heading", font=FONT_BUTTON,
                    background=PRIMARY_LIGHT, foreground=PRIMARY_DARK)
    style.configure("TEntry", fieldbackground=SURFACE, padding=6)
    style.configure("TCombobox", padding=6)
