"""Gera a arte e os temas do Clone OS dentro de profile/.

Rode sempre que mudar cores, logo ou papéis de parede:
    uv run --with pyside6 python tools/build_assets.py
"""

from __future__ import annotations

import json
import math
import random
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtSvg import QSvgRenderer

REPO = Path(__file__).resolve().parents[1]
PROFILE = REPO / "profile"
AIROOTFS = PROFILE / "airootfs"
LOGO = AIROOTFS / "usr/share/cloneos/logo.svg"

BLUE = "#1793D1"
CLAY = "#D97757"

# --------------------------------------------------------------------------
# Esquemas de cor do KDE
# --------------------------------------------------------------------------

SCHEMES = {
    "CloneOSDark": {
        "name": "Clone OS Escuro",
        "fg": {
            "Normal": "#E6E9EF", "Inactive": "#9AA3B2", "Active": "#43B6EE",
            "Link": "#43B6EE", "Visited": "#B48CF2", "Negative": "#F0616D",
            "Neutral": "#F2A65A", "Positive": "#3CCB8A",
        },
        "bg": {
            "Window": ("#1B1F2A", "#222734"),
            "View": ("#141720", "#1A1E29"),
            "Button": ("#262C3A", "#2D3444"),
            "Header": ("#151923", "#1B1F2A"),
            "Tooltip": ("#1B1F2A", "#222734"),
            "Complementary": ("#10131A", "#151923"),
            "Selection": (BLUE, "#126E9C"),
        },
        "header_inactive": ("#1B1F2A", "#222734"),
        "wm": {"active": "#151923", "inactive": "#1B1F2A"},
    },
    "CloneOSLight": {
        "name": "Clone OS Claro",
        "fg": {
            "Normal": "#1B1F2A", "Inactive": "#5B6576", "Active": BLUE,
            "Link": "#0F7BB5", "Visited": "#7C4DCC", "Negative": "#D6334A",
            "Neutral": "#C26A12", "Positive": "#1E9E63",
        },
        "bg": {
            "Window": ("#EEF1F5", "#E6EAF0"),
            "View": ("#FFFFFF", "#F5F7FA"),
            "Button": ("#F7F8FA", "#E3E8EF"),
            "Header": ("#E3E8EF", "#EEF1F5"),
            "Tooltip": ("#F7F8FA", "#E3E8EF"),
            "Complementary": ("#1B1F2A", "#222734"),
            "Selection": (BLUE, "#126E9C"),
        },
        "header_inactive": ("#EEF1F5", "#E3E8EF"),
        "wm": {"active": "#E3E8EF", "inactive": "#EEF1F5"},
    },
}

COLOR_EFFECTS = """[ColorEffects:Disabled]
Color=56,56,56
ColorAmount=0
ColorEffect=0
ContrastAmount=0.65
ContrastEffect=1
IntensityAmount=0.1
IntensityEffect=2

[ColorEffects:Inactive]
ChangeSelectionColor=true
Color=112,111,110
ColorAmount=0.025
ColorEffect=2
ContrastAmount=0.1
ContrastEffect=2
Enable=false
IntensityAmount=0
IntensityEffect=0
"""


def rgb(hex_color: str) -> str:
    c = QColor(hex_color)
    return f"{c.red()},{c.green()},{c.blue()}"


def color_group(title: str, bg: tuple[str, str], fg: dict[str, str], selection: bool = False) -> str:
    fg_normal = "#FFFFFF" if selection else fg["Normal"]
    fg_inactive = "#D6ECF8" if selection else fg["Inactive"]
    lines = [
        f"[{title}]",
        f"BackgroundAlternate={rgb(bg[1])}",
        f"BackgroundNormal={rgb(bg[0])}",
        f"DecorationFocus={rgb(BLUE)}",
        f"DecorationHover={rgb('#43B6EE')}",
        f"ForegroundActive={rgb(fg['Active'])}",
        f"ForegroundInactive={rgb(fg_inactive)}",
        f"ForegroundLink={rgb(fg['Link'])}",
        f"ForegroundNegative={rgb(fg['Negative'])}",
        f"ForegroundNeutral={rgb(fg['Neutral'])}",
        f"ForegroundNormal={rgb(fg_normal)}",
        f"ForegroundPositive={rgb(fg['Positive'])}",
        f"ForegroundVisited={rgb(fg['Visited'])}",
    ]
    return "\n".join(lines) + "\n"


def scheme_body(key: str) -> str:
    s = SCHEMES[key]
    fg = s["fg"]
    parts = [COLOR_EFFECTS]
    for group, bg in s["bg"].items():
        if group == "Complementary":
            comp_fg = dict(fg, Normal="#E6E9EF", Inactive="#9AA3B2")
            parts.append(color_group("Colors:Complementary", bg, comp_fg))
        elif group == "Selection":
            parts.append(color_group("Colors:Selection", bg, fg, selection=True))
        else:
            parts.append(color_group(f"Colors:{group}", bg, fg))
            if group == "Header":
                parts.append(color_group("Colors:Header][Inactive", s["header_inactive"], fg))
    wm = s["wm"]
    parts.append(
        "[WM]\n"
        f"activeBackground={rgb(wm['active'])}\n"
        f"activeBlend={rgb(fg['Normal'])}\n"
        f"activeForeground={rgb(fg['Normal'])}\n"
        f"inactiveBackground={rgb(wm['inactive'])}\n"
        f"inactiveBlend={rgb(fg['Inactive'])}\n"
        f"inactiveForeground={rgb(fg['Inactive'])}\n"
    )
    return "\n".join(parts)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build_color_schemes() -> None:
    for key, s in SCHEMES.items():
        text = scheme_body(key) + f"\n[General]\nColorScheme={key}\nName={s['name']}\nshadeSortColumn=true\n\n[KDE]\ncontrast=4\n"
        write(AIROOTFS / f"usr/share/color-schemes/{key}.colors", text)

    # Padrões do sistema para todo usuário novo (antes mesmo do primeiro login terminar).
    # Fonte Inter: a mais próxima da Segoe UI Variable do Windows 11 entre as livres.
    def font(size: int, weight: int = 400, family: str = "Inter") -> str:
        return f"{family},{size},-1,5,{weight},0,0,0,0,0,0,0,0,0,0,1"

    kdeglobals = (
        scheme_body("CloneOSDark")
        + "\n[General]\nColorScheme=CloneOSDark\nBrowserApplication=brave-browser.desktop\n"
        + f"font={font(10)}\nmenuFont={font(10)}\ntoolBarFont={font(10)}\n"
        + f"smallestReadableFont={font(8)}\nfixed={font(10, family='JetBrains Mono')}\n"
        + f"\n[WM]\nactiveFont={font(10, 600)}\n"
        + "\n[Icons]\nTheme=CloneOS-Dark\n"
        + "\n[KDE]\nLookAndFeelPackage=org.cloneos.desktop\ncontrast=4\nAnimationDurationFactor=0.75\n"
    )
    write(AIROOTFS / "etc/xdg/kdeglobals", kdeglobals)


# --------------------------------------------------------------------------
# Ícones
# --------------------------------------------------------------------------

# Terminal Claude: grafite quente com o brilho argila e um prompt creme,
# as mesmas cores da janela do terminal (usr/share/cloneos/terminal-claude).
ICON_TERMINAL_CLAUDE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#3A3834"/>
      <stop offset="1" stop-color="#201F1D"/>
    </linearGradient>
    <linearGradient id="clay" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#EE9A78"/>
      <stop offset="1" stop-color="#C65F3D"/>
    </linearGradient>
  </defs>
  <rect x="8" y="8" width="112" height="112" rx="28" fill="url(#bg)"/>
  <rect x="8.5" y="8.5" width="111" height="111" rx="27.5" fill="none" stroke="#FFFFFF" stroke-opacity="0.10"/>
  <path d="M84 20 C86 37 92 43 109 45 C92 47 86 53 84 70 C82 53 76 47 59 45 C76 43 82 37 84 20 Z" fill="url(#clay)"/>
  <path d="M28 66 L46 80 L28 94" fill="none" stroke="#ECEAE3" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="54" y="89" width="30" height="9" rx="4.5" fill="#ECEAE3"/>
</svg>
"""

ICON_INSTALL = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#3FB0EA"/>
      <stop offset="1" stop-color="#0F6E9F"/>
    </linearGradient>
  </defs>
  <rect x="8" y="8" width="112" height="112" rx="28" fill="url(#g)"/>
  <path d="M64 30 V80 M44 61 L64 81 L84 61" fill="none" stroke="#FFFFFF" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M34 84 V96 H94 V84" fill="none" stroke="#FFFFFF" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

ICON_SEARCH = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#5CC4F2"/>
      <stop offset="1" stop-color="#1273A8"/>
    </linearGradient>
  </defs>
  <circle cx="54" cy="54" r="24" fill="#43B6EE" fill-opacity="0.22"/>
  <circle cx="54" cy="54" r="31" fill="none" stroke="url(#g)" stroke-width="12"/>
  <path d="M77 77 L105 105" stroke="url(#g)" stroke-width="15" stroke-linecap="round"/>
</svg>
"""

ICON_TASK_VIEW = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <defs>
    <linearGradient id="b" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#43B6EE"/>
      <stop offset="1" stop-color="#1273A8"/>
    </linearGradient>
    <linearGradient id="c" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#F29D7B"/>
      <stop offset="1" stop-color="#C65B39"/>
    </linearGradient>
  </defs>
  <rect x="12" y="26" width="66" height="52" rx="11" fill="url(#b)"/>
  <rect x="48" y="50" width="68" height="54" rx="11" fill="url(#c)" stroke="#FFFFFF" stroke-opacity="0.9" stroke-width="5"/>
</svg>
"""


def gear_path(cx: float, cy: float, r_out: float, r_in: float, teeth: int) -> str:
    """Engrenagem como caminho SVG: dentes com topo reto, alternando os dois raios."""
    points = []
    step = 2 * math.pi / teeth
    for i in range(teeth):
        a = i * step
        for da, r in ((-0.30, r_in), (-0.17, r_out), (0.17, r_out), (0.30, r_in)):
            ang = a + da * step * 1.6
            points.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in points) + " Z"


ICON_SETTINGS = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#8A9BB4"/>
      <stop offset="1" stop-color="#3E4C63"/>
    </linearGradient>
  </defs>
  <path fill-rule="evenodd" fill="url(#g)" d="{gear_path(64, 64, 54, 42, 8)}
     M64 44 A20 20 0 1 0 64.01 44 Z"/>
  <circle cx="64" cy="64" r="11" fill="#1793D1"/>
</svg>
"""

START_HERE_NAMES = [
    "start-here", "start-here-symbolic", "start-here-kde", "start-here-kde-symbolic",
    "start-here-kde-plasma", "start-here-kde-plasma-symbolic", "distributor-logo",
    "distributor-logo-symbolic",
]


def build_icons() -> None:
    logo = LOGO.read_text(encoding="utf-8")
    hicolor = AIROOTFS / "usr/share/icons/hicolor/scalable/apps"
    write(hicolor / "cloneos.svg", logo)
    write(hicolor / "terminal-claude.svg", ICON_TERMINAL_CLAUDE)
    write(hicolor / "cloneos-install.svg", ICON_INSTALL)
    write(hicolor / "cloneos-pesquisar.svg", ICON_SEARCH)
    write(hicolor / "cloneos-visao-de-tarefas.svg", ICON_TASK_VIEW)
    write(hicolor / "cloneos-configuracoes.svg", ICON_SETTINGS)

    for variant, parent, label in (("Dark", "breeze-dark", "escuro"), ("Light", "breeze", "claro")):
        theme = AIROOTFS / f"usr/share/icons/CloneOS-{variant}"
        if theme.exists():
            shutil.rmtree(theme)
        write(
            theme / "index.theme",
            f"[Icon Theme]\nName=Clone OS ({label})\nComment=Breeze com a marca do Clone OS\n"
            f"Inherits={parent},hicolor\nDirectories=scalable/places\n\n"
            "[scalable/places]\nSize=64\nMinSize=8\nMaxSize=512\nType=Scalable\nContext=Places\n",
        )
        for name in START_HERE_NAMES:
            write(theme / f"scalable/places/{name}.svg", logo)


# --------------------------------------------------------------------------
# Papéis de parede e tela de boot
# --------------------------------------------------------------------------

def chevron(cx: float, top: float, h: float) -> QPainterPath:
    """A mesma forma do logo: um pico com recorte, altura h."""
    w = h * 40 / 96
    notch_w = h * 16.8 / 96
    notch_y = top + h * 56 / 96
    path = QPainterPath(QPointF(cx, top))
    for x, y in ((cx + w, top + h), (cx + notch_w, top + h), (cx, notch_y), (cx - notch_w, top + h), (cx - w, top + h)):
        path.lineTo(x, y)
    path.closeSubpath()
    return path


def triangle(cx: float, top: float, h: float) -> QPainterPath:
    w = h * 40 / 96
    path = QPainterPath(QPointF(cx, top))
    path.lineTo(cx + w, top + h)
    path.lineTo(cx - w, top + h)
    path.closeSubpath()
    return path


def with_alpha(hex_color: str, alpha: int) -> QColor:
    c = QColor(hex_color)
    c.setAlpha(max(0, min(255, alpha)))
    return c


def noise_tile(strength: int) -> QImage:
    rnd = random.Random(7)
    tile = QImage(192, 192, QImage.Format_ARGB32)
    for y in range(192):
        for x in range(192):
            v = 255 if rnd.random() > 0.5 else 0
            tile.setPixelColor(x, y, QColor(v, v, v, rnd.randint(0, strength)))
    return tile


WALLPAPERS = {
    "Night": {
        "title": "Clone Noite",
        "bg": ("#070B16", "#12203B"),
        "glows": [((0.76, 0.34), 0.55, BLUE, 80), ((0.60, 0.86), 0.42, CLAY, 55)],
        "echo": (BLUE, CLAY), "echo_alpha": 70,
        "logo": (("#43B6EE", "#1273A8"), ("#F29D7B", "#C65B39")),
        "stars": True,
    },
    "Dawn": {
        "title": "Clone Amanhecer",
        "bg": ("#FBF3EC", "#EDB999"),
        "glows": [((0.30, 0.20), 0.60, "#FFFFFF", 150), ((0.78, 0.70), 0.45, CLAY, 70)],
        "echo": ("#B45A38", "#1B6F9E"), "echo_alpha": 60,
        "logo": (("#43B6EE", "#1273A8"), ("#F29D7B", "#C65B39")),
        "stars": False,
    },
    "Aurora": {
        "title": "Clone Aurora",
        "bg": ("#04161A", "#0B2F2C"),
        "glows": [((0.70, 0.25), 0.55, "#10B981", 75), ((0.35, 0.90), 0.45, BLUE, 60)],
        "echo": ("#34D399", "#43B6EE"), "echo_alpha": 65,
        "logo": (("#6EE7B7", "#0E8F6A"), ("#7DD3FC", "#1273A8")),
        "stars": True,
    },
    "Graphite": {
        "title": "Clone Grafite",
        "bg": ("#121317", "#24262D"),
        "glows": [((0.72, 0.40), 0.55, "#8B93A7", 45)],
        "echo": ("#9AA3B2", "#6B7385"), "echo_alpha": 55,
        "logo": (("#E6E9EF", "#9AA3B2"), ("#9AA3B2", "#5B6576")),
        "stars": False,
    },
}


def paint_background(p: QPainter, w: int, h: int, spec: dict, noise: QImage) -> None:
    grad = QLinearGradient(0, 0, w, h)
    grad.setColorAt(0, QColor(spec["bg"][0]))
    grad.setColorAt(1, QColor(spec["bg"][1]))
    p.fillRect(0, 0, w, h, grad)

    for (fx, fy), radius, color, alpha in spec["glows"]:
        rg = QRadialGradient(QPointF(fx * w, fy * h), radius * w)
        rg.setColorAt(0, with_alpha(color, alpha))
        rg.setColorAt(1, with_alpha(color, 0))
        p.fillRect(0, 0, w, h, rg)

    if spec["stars"]:
        rnd = random.Random(42)
        p.setPen(Qt.NoPen)
        for _ in range(int(w * h / 9000)):
            x, y = rnd.random() * w, rnd.random() * h * 0.75
            r = rnd.random() * 1.6 + 0.3
            p.setBrush(QColor(255, 255, 255, rnd.randint(20, 110)))
            p.drawEllipse(QPointF(x, y), r, r)

    p.drawTiledPixmap(0, 0, w, h, _pixmap(noise))


def _pixmap(img: QImage):
    from PySide6.QtGui import QPixmap
    return QPixmap.fromImage(img)


def paint_logo(p: QPainter, cx: float, top: float, h: float, colors, with_echoes: dict | None = None) -> None:
    back = (cx - 12 / 96 * h, top)
    front = (cx + 12 / 96 * h, top + 10 / 96 * h)

    if with_echoes:
        for i in range(1, 16):
            k = 1 + i * 0.16
            fade = int(with_echoes["alpha"] * (1 - i / 16) ** 1.3)
            for (x, y), color in ((back, with_echoes["colors"][0]), (front, with_echoes["colors"][1])):
                hh = h * k
                p.setPen(QPen(with_alpha(color, fade), max(1.5, h / 260), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.setBrush(Qt.NoBrush)
                p.drawPath(triangle(x, y + (h - hh) * 0.62, hh))

    p.setPen(Qt.NoPen)
    for (x, y), (c1, c2) in ((back, colors[0]), (front, colors[1])):
        g = QLinearGradient(0, y, 0, y + h)
        g.setColorAt(0, QColor(c1))
        g.setColorAt(1, QColor(c2))
        p.setBrush(g)
        p.drawPath(chevron(x, y, h))


def build_wallpapers() -> None:
    noise = noise_tile(9)
    w, h = 2560, 1440
    for key, spec in WALLPAPERS.items():
        base = AIROOTFS / f"usr/share/wallpapers/CloneOS-{key}"
        if base.exists():
            shutil.rmtree(base)
        img = QImage(w, h, QImage.Format_RGB32)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        paint_background(p, w, h, spec, noise)
        paint_logo(
            p, cx=w * 0.70, top=h * 0.30, h=h * 0.40, colors=spec["logo"],
            with_echoes={"colors": spec["echo"], "alpha": spec["echo_alpha"]},
        )
        p.end()
        out = base / "contents/images/2560x1440.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(out), "PNG")
        img.scaled(640, 360, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).save(str(base / "contents/screenshot.png"), "PNG")
        write(
            base / "metadata.json",
            json.dumps(
                {"KPlugin": {"Authors": [{"Name": "Clone OS"}], "Id": f"CloneOS-{key}",
                             "License": "CC-BY-SA-4.0", "Name": spec["title"]}},
                indent=4, ensure_ascii=False,
            ) + "\n",
        )
        print(f"  papel de parede: {out.relative_to(REPO)} ({out.stat().st_size // 1024} KB)")


# Bloom (escuro) e Brisa (claro): uma flor abstrata de pétalas translúcidas nas cores do
# Clone OS, no espírito do papel de parede do Windows 11 (mas um desenho próprio).
BLOOMS = {
    "Bloom": {"title": "Clone Bloom", "dark": True},
    "Brisa": {"title": "Clone Brisa", "dark": False},
}


def petal(length: float, width: float, twist: float) -> QPainterPath:
    """Pétala em forma de fita torcida, saindo da origem em direção a -y."""
    path = QPainterPath(QPointF(0, 0))
    path.cubicTo(QPointF(width * 1.15, -length * 0.22), QPointF(width * (1.0 + twist), -length * 0.72),
                 QPointF(width * twist * 0.7, -length))
    path.cubicTo(QPointF(-width * (0.55 - twist), -length * 0.82), QPointF(-width * 0.95, -length * 0.34),
                 QPointF(0, 0))
    return path


def paint_flower(p: QPainter, h: int, dark: bool) -> None:
    """A flor em si, centrada na origem. Cada pétala tem o degradê do comprimento e um
    sombreado de lado a lado, como uma fita dobrada."""
    layers = [
        # pétalas, comprimento, largura, torção, giro, base, ponta, opacidade
        (9, h * 0.52, h * 0.120, 0.34, 0, "#08304D" if dark else "#7CC8EE", "#3FB0EA", 215),
        (9, h * 0.45, h * 0.115, -0.26, 20, "#4A1C10" if dark else "#F4B79C", "#E8845F", 205),
        (9, h * 0.35, h * 0.095, 0.36, 10, "#0D4E78" if dark else "#BDE6FA", "#7DD3FC", 220),
        (9, h * 0.23, h * 0.070, -0.32, 30, "#7A3420" if dark else "#FFD9C7", "#F7B39A", 230),
        (9, h * 0.13, h * 0.045, 0.30, 4, "#1D6FA0" if dark else "#FFFFFF", "#E6F6FF", 235),
    ]
    for n, length, width, twist, rot, base, tip, alpha in layers:
        for i in range(n):
            p.save()
            p.rotate(rot + i * 360 / n)
            path = petal(length, width, twist)
            along = QLinearGradient(0, 0, 0, -length)
            along.setColorAt(0.0, with_alpha(base, alpha))
            along.setColorAt(0.75, with_alpha(tip, alpha))
            along.setColorAt(1.0, with_alpha(tip, int(alpha * 0.85)))
            p.setPen(Qt.NoPen)
            p.setBrush(along)
            p.drawPath(path)
            across = QLinearGradient(-width, 0, width * 1.2, 0)
            across.setColorAt(0.0, with_alpha("#FFFFFF", 70 if dark else 110))
            across.setColorAt(0.45, with_alpha("#FFFFFF", 0))
            across.setColorAt(0.75, with_alpha("#000000", 0))
            across.setColorAt(1.0, with_alpha("#000000", 70 if dark else 30))
            p.setBrush(across)
            p.drawPath(path)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(with_alpha("#FFFFFF", 60 if dark else 140), h / 1100))
            p.drawPath(path)
            p.restore()


def paint_bloom(p: QPainter, w: int, h: int, dark: bool, noise: QImage) -> None:
    bg = QLinearGradient(0, 0, w, h)
    bg.setColorAt(0, QColor("#050914" if dark else "#E8F2FB"))
    bg.setColorAt(1, QColor("#0F1A33" if dark else "#F9EFE8"))
    p.fillRect(0, 0, w, h, bg)

    cx, cy = w * 0.5, h * 0.57
    halo = QRadialGradient(QPointF(cx, cy), h * 0.85)
    halo.setColorAt(0.0, with_alpha("#1793D1" if dark else "#FFFFFF", 70 if dark else 200))
    halo.setColorAt(0.5, with_alpha(CLAY, 22 if dark else 36))
    halo.setColorAt(1.0, with_alpha(BLUE, 0))
    p.fillRect(0, 0, w, h, halo)

    # A flor é desenhada numa camada à parte; uma cópia desfocada (reduzida e ampliada)
    # vira o brilho que ela "emite" por trás.
    layer = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    layer.fill(Qt.transparent)
    fp = QPainter(layer)
    fp.setRenderHint(QPainter.Antialiasing)
    fp.translate(cx, cy)
    paint_flower(fp, h, dark)
    fp.end()
    glow = layer.scaled(w // 24, h // 24, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    glow = glow.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    p.setOpacity(0.85 if dark else 0.55)
    p.setCompositionMode(QPainter.CompositionMode_Screen if dark else QPainter.CompositionMode_SourceOver)
    p.drawImage(0, 0, glow)
    p.setOpacity(1.0)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    p.drawImage(0, 0, layer)

    core = QRadialGradient(QPointF(cx, cy), h * 0.05)
    core.setColorAt(0, with_alpha("#FFFFFF", 200 if dark else 230))
    core.setColorAt(1, with_alpha("#FFFFFF", 0))
    p.setPen(Qt.NoPen)
    p.setBrush(core)
    p.drawEllipse(QPointF(cx, cy), h * 0.05, h * 0.05)

    p.drawTiledPixmap(0, 0, w, h, _pixmap(noise))


def build_blooms() -> None:
    noise = noise_tile(7)
    w, h = 2560, 1440
    for key, spec in BLOOMS.items():
        base = AIROOTFS / f"usr/share/wallpapers/CloneOS-{key}"
        if base.exists():
            shutil.rmtree(base)
        img = QImage(w, h, QImage.Format_RGB32)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        paint_bloom(p, w, h, spec["dark"], noise)
        p.end()
        out = base / "contents/images/2560x1440.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(out), "PNG")
        img.scaled(640, 360, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).save(str(base / "contents/screenshot.png"), "PNG")
        write(
            base / "metadata.json",
            json.dumps(
                {"KPlugin": {"Authors": [{"Name": "Clone OS"}], "Id": f"CloneOS-{key}",
                             "License": "CC-BY-SA-4.0", "Name": spec["title"]}},
                indent=4, ensure_ascii=False,
            ) + "\n",
        )
        print(f"  papel de parede: {out.relative_to(REPO)} ({out.stat().st_size // 1024} KB)")


def build_lnf_previews() -> None:
    """Prévias do tema global: papel de parede Bloom com a barra de tarefas centralizada."""
    hicolor = AIROOTFS / "usr/share/icons/hicolor/scalable/apps"
    icons = [LOGO, hicolor / "cloneos-pesquisar.svg", hicolor / "cloneos-visao-de-tarefas.svg",
             hicolor / "terminal-claude.svg", hicolor / "cloneos-configuracoes.svg"]
    wallpaper = QImage(str(AIROOTFS / "usr/share/wallpapers/CloneOS-Bloom/contents/images/2560x1440.png"))
    previews = AIROOTFS / "usr/share/plasma/look-and-feel/org.cloneos.desktop/contents/previews"
    previews.mkdir(parents=True, exist_ok=True)
    for name, (w, h), fmt in (("fullscreenpreview.jpg", (1920, 1080), "JPG"), ("preview.png", (600, 337), "PNG")):
        img = wallpaper.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_RGB32)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        bar = h * 48 / 1080
        p.fillRect(QRectF(0, h - bar, w, bar), with_alpha("#10131A", 215))
        size = bar * 0.62
        gap = bar * 0.3
        total = len(icons) * size + (len(icons) - 1) * gap
        x = (w - total) / 2
        for icon in icons:
            QSvgRenderer(str(icon)).render(p, QRectF(x, h - bar + (bar - size) / 2, size, size))
            x += size + gap
        p.setPen(QColor("#E6E9EF"))
        font = QFont("Inter")
        font.setPixelSize(max(6, int(bar * 0.26)))
        p.setFont(font)
        p.drawText(QRectF(w - bar * 2.6, h - bar, bar * 2.2, bar), Qt.AlignCenter, "14:30\n07/10/2026")
        p.end()
        img.save(str(previews / name), fmt, 88)


def build_boot_watermark() -> None:
    """Marca do Clone OS na tela de boot (Plymouth), embaixo do logo do fabricante."""
    w, h = 300, 64
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(str(LOGO)).render(p, QRectF(18, 6, 52, 52))
    font = QFont("Inter")
    font.setPixelSize(30)
    font.setWeight(QFont.DemiBold)
    p.setFont(font)
    p.setPen(QColor("#E6E9EF"))
    p.drawText(QRectF(84, 0, w - 84, h), Qt.AlignVCenter | Qt.AlignLeft, "Clone OS")
    p.end()
    out = AIROOTFS / "usr/share/plymouth/themes/cloneos/watermark.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), "PNG")


def build_splash() -> None:
    """Fundo do menu de boot BIOS (syslinux exige 640x480)."""
    w, h = 640, 480
    spec = WALLPAPERS["Night"]
    img = QImage(w, h, QImage.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    paint_background(p, w, h, dict(spec, stars=False), noise_tile(0))
    paint_logo(p, cx=236, top=38, h=78, colors=spec["logo"])
    p.setPen(QColor("#E6E9EF"))
    font = QFont("Segoe UI", 30)
    font.setBold(True)
    p.setFont(font)
    p.drawText(QRectF(290, 44, 300, 50), Qt.AlignLeft | Qt.AlignVCenter, "Clone OS")
    font = QFont("Segoe UI", 12)
    p.setFont(font)
    p.setPen(QColor("#9AA3B2"))
    p.drawText(QRectF(292, 90, 300, 26), Qt.AlignLeft | Qt.AlignVCenter, "0.3 · baseado no Arch Linux")
    p.end()
    out = PROFILE / "syslinux/splash.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), "PNG")


def render_logo_png(size: int, out: Path) -> None:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    QSvgRenderer(str(LOGO)).render(p)
    p.end()
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), "PNG")


def main() -> None:
    app = QGuiApplication(sys.argv)  # noqa: F841 — necessário para fontes e SVG
    print("Gerando esquemas de cor...")
    build_color_schemes()
    print("Gerando ícones...")
    build_icons()
    render_logo_png(256, AIROOTFS / "usr/share/cloneos/logo-256.png")
    print("Gerando papéis de parede...")
    build_wallpapers()
    build_blooms()
    print("Gerando prévias do tema global...")
    build_lnf_previews()
    print("Gerando tela de boot...")
    build_splash()
    build_boot_watermark()
    print("Pronto.")


if __name__ == "__main__":
    main()
