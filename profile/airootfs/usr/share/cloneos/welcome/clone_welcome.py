#!/usr/bin/env python3
"""Clone Welcome: assistente de primeiro uso do Clone OS.

Conecta o Claude, define quais pastas ele pode acessar e aplica a aparência.
Toda ação no sistema passa por `clonectl` e `terminal-claude`, os mesmos comandos
que o próprio Claude usa.

Fora do Clone OS (ex.: Windows) roda em modo de demonstração: nenhum comando é
executado e as configurações vão para uma pasta temporária.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

ROOT = Path(__file__).resolve().parents[4]
SHARE = ROOT / "usr/share/cloneos"
WALLPAPER_DIR = ROOT / "usr/share/wallpapers"
DRY_RUN = sys.platform == "win32" or os.environ.get("CLONEOS_DRYRUN") == "1"
HOME = Path(tempfile.gettempdir()) / "cloneos-demo-home" if DRY_RUN else Path.home()
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config") / "cloneos"
if DRY_RUN:
    CONFIG_DIR = HOME / ".config/cloneos"
CLAUDE_DIR = HOME / ".claude"
IS_LIVE = Path("/run/archiso").is_dir()

CLAY = "#D97757"
ACCENTS = [
    ("Azul Arch", "#1793D1"),
    ("Argila", CLAY),
    ("Violeta", "#8B5CF6"),
    ("Menta", "#10B981"),
    ("Rosa", "#EC4899"),
    ("Âmbar", "#F59E0B"),
    ("Grafite", "#64748B"),
]
WALLPAPERS = [("bloom", "Bloom"), ("brisa", "Brisa"), ("night", "Noite"), ("dawn", "Amanhecer"),
              ("aurora", "Aurora"), ("graphite", "Grafite")]
USER_DIRS = [
    ("DESKTOP", "Área de trabalho"),
    ("DOCUMENTS", "Documentos"),
    ("DOWNLOAD", "Downloads"),
    ("PICTURES", "Imagens"),
    ("MUSIC", "Música"),
    ("VIDEOS", "Vídeos"),
]
DEFAULT_ALLOWED = {"DOCUMENTS", "DOWNLOAD"}
PERMISSION_MODES = [
    ("default", "Perguntar antes de agir", "O Claude pede sua confirmação antes de editar arquivos ou rodar comandos. Recomendado."),
    ("acceptEdits", "Editar arquivos sem perguntar", "Edições em arquivos das pastas liberadas são feitas direto. Comandos ainda pedem confirmação."),
    ("plan", "Somente planejar", "O Claude analisa e propõe um plano, mas não altera nada."),
]
# Regras que o Clone Welcome sempre adiciona às configurações do Claude Code.
PROTECTED_RULES = [
    "Read(~/.ssh/**)", "Edit(~/.ssh/**)",
    "Read(~/.gnupg/**)", "Edit(~/.gnupg/**)",
    "Read(~/.config/BraveSoftware/**)", "Edit(~/.config/BraveSoftware/**)",
    "Read(~/.config/Claude/**)", "Edit(~/.config/Claude/**)",
    "Read(~/.local/share/kwalletd/**)", "Edit(~/.local/share/kwalletd/**)",
    "Read(~/.claude/.credentials.json)",
]
PROTECTED_TEXT = ("O Claude nunca lê nem altera suas chaves SSH e GPG, as senhas e cookies do Brave, "
                  "a carteira do KDE (KWallet), o login do app do Claude e as credenciais do Claude Code.")

PALETTES = {
    "dark": {
        "bg": "#11141B", "side": "#0B0E14", "card": "#181D28", "card2": "#202634",
        "border": "#283042", "text": "#E6E9EF", "muted": "#9AA3B2", "faint": "#636B7D",
    },
    "light": {
        "bg": "#F4F6F9", "side": "#E8ECF2", "card": "#FFFFFF", "card2": "#F1F4F8",
        "border": "#D8DEE7", "text": "#1B1F2A", "muted": "#5B6576", "faint": "#98A1B0",
    },
}

# Ícones de linha próprios (viewBox 24x24). "C" é trocado pela cor desejada.
ICONS = {
    "sparkle": '<path d="M12 2.5c.7 4.6 3 6.9 7.5 7.5-4.5.6-6.8 2.9-7.5 7.5-.7-4.6-3-6.9-7.5-7.5 4.5-.6 6.8-2.9 7.5-7.5z" fill="C"/><path d="M18.5 15.5c.3 1.9 1.1 2.7 3 3-1.9.3-2.7 1.1-3 3-.3-1.9-1.1-2.7-3-3 1.9-.3 2.7-1.1 3-3z" fill="C"/>',
    "lock": '<rect x="5" y="10.5" width="14" height="10" rx="2.5" fill="none" stroke="C" stroke-width="1.8"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c1.2 0 1.6-.8 1.6-1.6 0-1.2-1-1.6-1-2.7 0-.9.7-1.7 1.7-1.7H16a5 5 0 0 0 5-5C21 6.3 17 3 12 3z" fill="none" stroke="C" stroke-width="1.8" stroke-linejoin="round"/><circle cx="7.5" cy="11.5" r="1.3" fill="C"/><circle cx="10" cy="7.2" r="1.3" fill="C"/><circle cx="14.8" cy="7.2" r="1.3" fill="C"/>',
    "terminal": '<rect x="3" y="4.5" width="18" height="15" rx="2.5" fill="none" stroke="C" stroke-width="1.8"/><path d="M7 9.5l3 2.5-3 2.5M12.5 15h4.5" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    "plug": '<path d="M9 3v4M15 3v4M6.5 7h11v3.5a5.5 5.5 0 0 1-11 0zM12 16v5" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    "globe": '<circle cx="12" cy="12" r="9" fill="none" stroke="C" stroke-width="1.8"/><path d="M3 12h18M12 3c2.4 2.6 3.7 5.6 3.7 9s-1.3 6.4-3.7 9c-2.4-2.6-3.7-5.6-3.7-9S9.6 5.6 12 3z" fill="none" stroke="C" stroke-width="1.8"/>',
    "shield": '<path d="M12 3l7 2.8v5.4c0 4.4-2.9 8-7 9.8-4.1-1.8-7-5.4-7-9.8V5.8z" fill="none" stroke="C" stroke-width="1.8" stroke-linejoin="round"/><path d="M8.8 12.2l2.2 2.2 4.3-4.4" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    "folder": '<path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H9l2 2.2h7.5A2.5 2.5 0 0 1 21 9.7v7.8a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z" fill="none" stroke="C" stroke-width="1.8" stroke-linejoin="round"/>',
    "download": '<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="C" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>',
    "keyboard": '<rect x="2.5" y="6" width="19" height="12" rx="2.5" fill="none" stroke="C" stroke-width="1.8"/><path d="M6 10h.01M9.5 10h.01M13 10h.01M16.5 10h.01M7.5 14h9" fill="none" stroke="C" stroke-width="2" stroke-linecap="round"/>',
    "chat": '<path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v7a2.5 2.5 0 0 1-2.5 2.5H10l-4.5 4v-4h0A1.5 1.5 0 0 1 4 14.5z" fill="none" stroke="C" stroke-width="1.8" stroke-linejoin="round"/>',
}


# --------------------------------------------------------------------------
# Sistema
# --------------------------------------------------------------------------

def run(cmd: list[str], detach: bool = True) -> None:
    if DRY_RUN:
        print("[demo] " + " ".join(cmd), flush=True)
        return
    try:
        if detach:
            subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(f"comando não encontrado: {cmd[0]}", file=sys.stderr)


def in_terminal(title: str, cmd: list[str]) -> None:
    run(["konsole", "-p", f"tabtitle={title}", "-e", *cmd])


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def claude_installed() -> bool:
    if DRY_RUN:
        return True
    return bool(shutil.which("claude")) or (HOME / ".local/bin/claude").exists()


def claude_app_installed() -> bool:
    return DRY_RUN or bool(shutil.which("claude-desktop"))


def claude_connected() -> bool:
    return (CLAUDE_DIR / ".credentials.json").exists()


def user_dirs() -> dict[str, Path]:
    """Lê ~/.config/user-dirs.dirs (nomes das pastas no idioma do sistema)."""
    found: dict[str, Path] = {}
    try:
        for line in (HOME / ".config/user-dirs.dirs").read_text(encoding="utf-8").splitlines():
            if line.startswith("XDG_") and "=" in line:
                key, value = line.split("=", 1)
                value = value.strip().strip('"').replace("$HOME", str(HOME))
                found[key[4:-4]] = Path(value)
    except OSError:
        pass
    return {key: found.get(key, HOME / label) for key, label in USER_DIRS}


def wallpaper_image(key: str) -> Path | None:
    images = sorted((WALLPAPER_DIR / f"CloneOS-{key.capitalize()}" / "contents/images").glob("*.png"))
    return images[-1] if images else None


def look_state() -> dict:
    state = {"theme": "dark", "accent": "auto", "wallpaper": "bloom"}
    state.update(read_json(CONFIG_DIR / "look.json"))
    return state


# --------------------------------------------------------------------------
# Estilo
# --------------------------------------------------------------------------

def svg_pixmap(svg: str, size: int, dpr: float = 2.0) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    renderer.render(p)
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def icon_pixmap(name: str, color: str, size: int) -> QPixmap:
    body = ICONS[name].replace('"C"', f'"{color}"')
    return svg_pixmap(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{body}</svg>', size)


def mix(c1: str, c2: str, t: float) -> str:
    a, b = QColor(c1), QColor(c2)
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
    ).name()


def stylesheet(p: dict, accent: str, check_icon: Path) -> str:
    hover = mix(accent, "#FFFFFF", 0.14)
    clay_hover = mix(CLAY, "#FFFFFF", 0.14)
    check = check_icon.as_posix()
    return f"""
    QWidget {{ color: {p['text']}; font-family: "Inter", "Noto Sans", "Segoe UI", sans-serif; font-size: 14px; }}
    #Root {{ background: {p['bg']}; }}
    #Sidebar {{ background: {p['side']}; border-right: 1px solid {p['border']}; }}
    #Footer {{ border-top: 1px solid {p['border']}; }}
    QLabel {{ background: transparent; }}
    QLabel#Brand {{ font-size: 19px; font-weight: 700; }}
    QLabel#H1 {{ font-size: 30px; font-weight: 700; }}
    QLabel#H2 {{ font-size: 15px; font-weight: 650; }}
    QLabel#Lead {{ color: {p['muted']}; font-size: 15px; }}
    QLabel#Muted {{ color: {p['muted']}; }}
    QLabel#Small {{ color: {p['muted']}; font-size: 12px; }}
    QLabel#Eyebrow {{ color: {accent}; font-size: 12px; font-weight: 700; }}
    QLabel#Section {{ color: {p['muted']}; font-size: 12px; font-weight: 700; }}
    QLabel#Pill {{ background: {mix(p['side'], accent, 0.22)}; color: {mix(accent, p['text'], 0.35)};
                   border-radius: 10px; padding: 3px 10px; font-size: 12px; font-weight: 600; }}
    QLabel#BadgeOk {{ background: {mix(p['card'], '#3CCB8A', 0.18)}; color: #2FB67A; border-radius: 10px;
                      padding: 3px 10px; font-size: 12px; font-weight: 700; }}
    QLabel#BadgeOff {{ background: {p['card2']}; color: {p['muted']}; border-radius: 10px;
                       padding: 3px 10px; font-size: 12px; font-weight: 700; }}
    QLabel#Key {{ background: {p['card2']}; border: 1px solid {p['border']}; border-bottom-width: 3px;
                  border-radius: 7px; padding: 4px 10px; font-weight: 700; font-size: 13px; }}
    QFrame#Card {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 14px; }}
    QFrame#Banner {{ background: {mix(p['card'], accent, 0.12)}; border: 1px solid {mix(p['border'], accent, 0.45)}; border-radius: 14px; }}
    QPushButton {{ background: {p['card2']}; border: 1px solid {p['border']}; border-radius: 10px;
                   padding: 9px 16px; font-weight: 600; }}
    QPushButton:hover {{ border-color: {accent}; }}
    QPushButton:disabled {{ color: {p['faint']}; border-color: {p['border']}; }}
    QPushButton#Primary {{ background: {accent}; border: 1px solid {accent}; color: #FFFFFF; }}
    QPushButton#Primary:hover {{ background: {hover}; border-color: {hover}; }}
    QPushButton#Claude {{ background: {CLAY}; border: 1px solid {CLAY}; color: #FFFFFF; }}
    QPushButton#Claude:hover {{ background: {clay_hover}; border-color: {clay_hover}; }}
    QPushButton#Ghost {{ background: transparent; border: 1px solid transparent; color: {p['muted']}; }}
    QPushButton#Ghost:hover {{ color: {p['text']}; }}
    QCheckBox, QRadioButton {{ spacing: 10px; background: transparent; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 2px solid {p['faint']}; background: transparent; }}
    QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; image: url("{check}"); }}
    QRadioButton::indicator {{ width: 18px; height: 18px; border-radius: 11px; border: 2px solid {p['faint']}; background: transparent; }}
    QRadioButton::indicator:checked {{ border-color: {accent}; background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #FFFFFF, stop:0.42 #FFFFFF, stop:0.5 {accent}, stop:1 {accent}); }}
    QListWidget {{ background: {p['card2']}; border: 1px solid {p['border']}; border-radius: 10px; padding: 4px; }}
    QListWidget::item {{ padding: 6px 8px; border-radius: 6px; }}
    QListWidget::item:selected {{ background: {mix(p['card2'], accent, 0.3)}; color: {p['text']}; }}
    QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px; }}
    QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 3px; min-height: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    """


# --------------------------------------------------------------------------
# Widgets
# --------------------------------------------------------------------------

def label(text: str, name: str | None = None, wrap: bool = False) -> QLabel:
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    if wrap:
        w.setWordWrap(True)
    w.setTextInteractionFlags(Qt.NoTextInteraction)
    return w


def button(text: str, name: str | None = None, slot=None) -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    if name:
        b.setObjectName(name)
    if slot:
        b.clicked.connect(slot)
    return b


def card(name: str = "Card") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName(name)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(10)
    return frame, layout


class IconTile(QLabel):
    """Ícone de linha dentro de um quadrado arredondado tingido."""

    def __init__(self, icon: str, color_fn, size: int = 40):
        super().__init__()
        self.icon, self.color_fn, self.box = icon, color_fn, size
        self.setFixedSize(size, size)

    def paintEvent(self, _event) -> None:
        color = self.color_fn()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = QColor(color)
        bg.setAlpha(38)
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(0, 0, self.box, self.box), 11, 11)
        s = int(self.box * 0.55)
        p.drawPixmap(int((self.box - s) / 2), int((self.box - s) / 2), icon_pixmap(self.icon, color, s))
        p.end()


class StepList(QWidget):
    clicked = Signal(int)

    def __init__(self, steps: list[str], win: "Welcome"):
        super().__init__()
        self.steps, self.win, self.current = steps, win, 0
        self.setFixedHeight(len(steps) * 48)
        self.setCursor(Qt.PointingHandCursor)

    def set_current(self, index: int) -> None:
        self.current = index
        self.update()

    def mousePressEvent(self, event) -> None:
        index = int(event.position().y() // 48)
        if 0 <= index < len(self.steps):
            self.clicked.emit(index)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pal, accent = self.win.palette_colors, self.win.accent
        for i, name in enumerate(self.steps):
            y = i * 48
            if i == self.current:
                bg = QColor(accent)
                bg.setAlpha(34)
                p.setPen(Qt.NoPen)
                p.setBrush(bg)
                p.drawRoundedRect(QRectF(0, y + 4, self.width(), 40), 10, 10)
            circle = QRectF(12, y + 12, 24, 24)
            done = i < self.current
            if done or i == self.current:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(accent))
            else:
                p.setPen(QPen(QColor(pal["faint"]), 1.6))
                p.setBrush(Qt.NoBrush)
            p.drawEllipse(circle)
            if done:
                p.drawPixmap(int(circle.x() + 5), int(circle.y() + 5), icon_pixmap("check", "#FFFFFF", 14))
            else:
                p.setPen(QColor("#FFFFFF" if i == self.current else pal["muted"]))
                f = QFont(self.font())
                f.setPixelSize(12)
                f.setBold(True)
                p.setFont(f)
                p.drawText(circle, Qt.AlignCenter, str(i + 1))
            f = QFont(self.font())
            f.setPixelSize(14)
            f.setBold(i == self.current)
            p.setFont(f)
            p.setPen(QColor(pal["text"] if i <= self.current else pal["muted"]))
            p.drawText(QRectF(48, y, self.width() - 52, 48), Qt.AlignVCenter | Qt.AlignLeft, name)
        p.end()


class ThemeCard(QAbstractButton):
    """Miniatura de área de trabalho para escolher tema claro/escuro."""

    def __init__(self, theme: str, title: str, win: "Welcome"):
        super().__init__()
        self.theme, self.title, self.win = theme, title, win
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(212, 136)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        ui, accent = self.win.palette_colors, self.win.accent
        mini = PALETTES[self.theme]
        outer = QRectF(1.5, 1.5, self.width() - 3, self.height() - 3)
        p.setPen(QPen(QColor(accent if self.isChecked() else ui["border"]), 2.5 if self.isChecked() else 1))
        p.setBrush(QColor(ui["card"]))
        p.drawRoundedRect(outer, 14, 14)
        screen = QRectF(12, 12, self.width() - 24, 82)
        path = QPainterPath()
        path.addRoundedRect(screen, 9, 9)
        p.setClipPath(path)
        p.fillRect(screen, QColor("#0E1830" if self.theme == "dark" else "#F3DCCB"))
        p.fillRect(QRectF(screen.x(), screen.bottom() - 14, screen.width(), 14), QColor(mini["side"]))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(accent))
        p.drawEllipse(QRectF(screen.x() + 6, screen.bottom() - 11, 8, 8))
        win = QRectF(screen.x() + 26, screen.y() + 10, 120, 52)
        p.setBrush(QColor(mini["card"]))
        p.drawRoundedRect(win, 6, 6)
        p.setBrush(QColor(mini["border"]))
        p.drawRoundedRect(QRectF(win.x() + 10, win.y() + 12, 70, 6), 3, 3)
        p.drawRoundedRect(QRectF(win.x() + 10, win.y() + 23, 90, 6), 3, 3)
        p.setBrush(QColor(accent))
        p.drawRoundedRect(QRectF(win.x() + 10, win.y() + 35, 36, 10), 4, 4)
        p.setClipping(False)
        f = QFont(self.font())
        f.setPixelSize(14)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(ui["text"]))
        p.drawText(QRectF(14, 98, self.width() - 28, 30), Qt.AlignVCenter | Qt.AlignLeft, self.title)
        if self.isChecked():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(accent))
            dot = QRectF(self.width() - 36, 102, 22, 22)
            p.drawEllipse(dot)
            p.drawPixmap(int(dot.x() + 4), int(dot.y() + 4), icon_pixmap("check", "#FFFFFF", 14))
        p.end()


class Swatch(QAbstractButton):
    def __init__(self, name: str, color: str, win: "Welcome"):
        super().__init__()
        self.color, self.win = color, win
        self.setCheckable(True)
        self.setToolTip(name)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(40, 40)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.isChecked():
            p.setPen(QPen(QColor(self.color), 2.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(2, 2, 36, 36))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self.color))
        p.drawEllipse(QRectF(7, 7, 26, 26))
        p.end()


class WallpaperTile(QAbstractButton):
    def __init__(self, key: str, title: str, image: Path | None, win: "Welcome"):
        super().__init__()
        self.key, self.title, self.win = key, title, win
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(168, 124)
        self.thumb = QPixmap()
        if image:
            self.thumb = QPixmap(str(image)).scaled(QSize(320, 180), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        ui, accent = self.win.palette_colors, self.win.accent
        img = QRectF(3, 3, self.width() - 6, 90)
        path = QPainterPath()
        path.addRoundedRect(img, 10, 10)
        p.setClipPath(path)
        if not self.thumb.isNull():
            p.drawPixmap(img.toRect(), self.thumb)
        else:
            p.fillRect(img, QColor(ui["card2"]))
        p.setClipping(False)
        p.setPen(QPen(QColor(accent if self.isChecked() else ui["border"]), 3 if self.isChecked() else 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(img, 10, 10)
        f = QFont(self.font())
        f.setPixelSize(13)
        f.setBold(self.isChecked())
        p.setFont(f)
        p.setPen(QColor(ui["text"] if self.isChecked() else ui["muted"]))
        p.drawText(QRectF(4, 96, self.width() - 8, 26), Qt.AlignVCenter | Qt.AlignLeft, self.title)
        p.end()


# --------------------------------------------------------------------------
# Páginas
# --------------------------------------------------------------------------

class Page(QWidget):
    eyebrow = ""
    title = ""
    lead = ""

    def __init__(self, win: "Welcome"):
        super().__init__()
        self.win = win
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        self.layout_ = QVBoxLayout(body)
        self.layout_.setContentsMargins(48, 40, 48, 28)
        self.layout_.setSpacing(8)
        self.layout_.addWidget(label(self.eyebrow, "Eyebrow"))
        self.layout_.addWidget(label(self.title, "H1", wrap=True))
        if self.lead:
            self.layout_.addWidget(label(self.lead, "Lead", wrap=True))
        self.layout_.addSpacing(18)
        self.build(self.layout_)
        self.layout_.addStretch(1)

    def build(self, layout: QVBoxLayout) -> None:
        raise NotImplementedError

    def on_enter(self) -> None:
        pass

    def on_leave(self) -> None:
        pass

    def commit(self) -> None:
        """Chamado só pelo botão Continuar: "Pular" e "Voltar" não salvam nada."""

    def accent(self) -> str:
        return self.win.accent


class WelcomePage(Page):
    eyebrow = "BEM-VINDO"
    title = "Olá! Este é o Clone OS"
    lead = ("Um Arch Linux com KDE Plasma e o Claude integrado ao sistema, ajustado para este notebook. "
            "Vamos deixar tudo pronto em poucos passos.")

    def build(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(14)
        features = [
            ("sparkle", lambda: CLAY, "Claude no sistema", "Peça em português: organizar arquivos, montar planilhas, ajustar o sistema."),
            ("shield", self.accent, "Você decide o acesso", "O Claude só enxerga as pastas que você liberar, e pede antes de agir."),
            ("palette", self.accent, "Do seu jeito", "Tema, cor de destaque e papel de parede, tudo a um clique."),
        ]
        for icon, color_fn, title, text in features:
            frame, box = card()
            box.addWidget(IconTile(icon, color_fn))
            box.addSpacing(4)
            box.addWidget(label(title, "H2"))
            box.addWidget(label(text, "Muted", wrap=True))
            box.addStretch(1)
            frame.setMinimumHeight(190)
            row.addWidget(frame, 1)
        layout.addLayout(row)

        if IS_LIVE or self.win.force_live:
            layout.addSpacing(14)
            frame, box = card("Banner")
            line = QHBoxLayout()
            line.setSpacing(16)
            line.addWidget(IconTile("download", self.accent, 44))
            text = QVBoxLayout()
            text.setSpacing(2)
            text.addWidget(label("Você está no modo live", "H2"))
            text.addWidget(label("Nada é salvo no disco até você instalar. Pode explorar à vontade.", "Muted", wrap=True))
            line.addLayout(text, 1)
            line.addWidget(button("Instalar Clone OS", "Primary", self.install))
            box.addLayout(line)
            layout.addWidget(frame)

    def install(self) -> None:
        in_terminal("Instalar Clone OS", ["sudo", "/usr/local/bin/clone-install"])


class ClaudePage(Page):
    eyebrow = "PASSO 2 DE 5 · CLAUDE"
    title = "Conecte o Claude ao seu computador"
    lead = ("O Claude Code e o app do Claude já vêm instalados. Falta só entrar com a sua conta Claude; "
            "o login abre no Brave.")

    def build(self, layout: QVBoxLayout) -> None:
        self.badges: dict[str, QLabel] = {}
        rows = [
            ("plug", lambda: CLAY, "Terminal Claude", "login",
             "O Claude Code, agente que trabalha com seus arquivos e com o sistema. "
             "Na primeira vez ele pede o login e abre o Brave.",
             [button("Entrar com Claude", "Claude", self.login)]),
            ("chat", self.accent, "App do Claude", "app",
             "Conversas, projetos e o Claude Code numa janela. Entre com a mesma conta.",
             [button("Abrir o app", None, lambda: run(["claude-desktop"]))]),
            ("globe", self.accent, "Claude no navegador", None,
             "Opcional: o claude.ai no Brave e a extensão Claude in Chrome (funciona no Brave).",
             [button("Abrir claude.ai", None, lambda: run(["brave", "https://claude.ai/login"])),
              button("Extensão", None, lambda: run(["brave", "https://claude.com/claude-in-chrome"]))]),
        ]
        for icon, color_fn, title, badge_key, text, actions in rows:
            frame, box = card()
            line = QHBoxLayout()
            line.setSpacing(16)
            line.addWidget(IconTile(icon, color_fn, 44), 0, Qt.AlignTop)
            info = QVBoxLayout()
            info.setSpacing(3)
            head = QHBoxLayout()
            head.setSpacing(10)
            head.addWidget(label(title, "H2"))
            if badge_key:
                badge = label("", "BadgeOff")
                self.badges[badge_key] = badge
                head.addWidget(badge)
            head.addStretch(1)
            info.addLayout(head)
            info.addWidget(label(text, "Muted", wrap=True))
            line.addLayout(info, 1)
            for action in actions:
                line.addWidget(action, 0, Qt.AlignVCenter)
            box.addLayout(line)
            layout.addWidget(frame)
            layout.addSpacing(6)

        layout.addSpacing(4)
        layout.addWidget(label(
            "O Claude Code requer um plano Claude Pro, Max, Team ou Enterprise, ou uma chave da API da Anthropic. "
            "Você pode fazer isso depois pelo menu: Clone Welcome.", "Small", wrap=True))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        if claude_installed():
            self.set_badge("login", claude_connected(), "Conectado", "Não conectado")
        else:
            self.set_badge("login", False, "", "Não instalado")
        self.set_badge("app", claude_app_installed(), "Instalado", "Não instalado")

    def set_badge(self, key: str, ok: bool, yes: str, no: str) -> None:
        badge = self.badges[key]
        badge.setText(("✓ " + yes) if ok else no)
        badge.setObjectName("BadgeOk" if ok else "BadgeOff")
        badge.style().unpolish(badge)
        badge.style().polish(badge)

    def login(self) -> None:
        run(["/usr/local/bin/terminal-claude"])

    def on_enter(self) -> None:
        self.refresh()
        self.timer.start(2000)

    def on_leave(self) -> None:
        self.timer.stop()


class PermissionsPage(Page):
    eyebrow = "PASSO 3 DE 5 · PRIVACIDADE"
    title = "O que o Claude pode acessar"
    lead = "O Claude só enxerga as pastas marcadas aqui, além da pasta de trabalho ~/Clone. Dá para mudar quando quiser."

    def build(self, layout: QVBoxLayout) -> None:
        settings = read_json(CLAUDE_DIR / "settings.json").get("permissions", {})
        saved = [Path(d) for d in settings.get("additionalDirectories", [])]
        self.dirs = user_dirs()
        first_time = not (CLAUDE_DIR / "settings.json").exists()

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        folders, box = card()
        box.addWidget(label("PASTAS LIBERADAS", "Section"))
        self.checks: dict[str, QCheckBox] = {}
        for key, name in USER_DIRS:
            path = self.dirs[key]
            cb = QCheckBox(f"{path.name or name}")
            cb.setToolTip(str(path))
            cb.setChecked(key in DEFAULT_ALLOWED if first_time else path in saved)
            cb.setCursor(Qt.PointingHandCursor)
            self.checks[key] = cb
            box.addWidget(cb)
        box.addSpacing(6)
        box.addWidget(label("Outras pastas", "Small"))
        self.extra = QListWidget()
        self.extra.setFixedHeight(84)
        known = set(self.dirs.values())
        for d in saved:
            if d not in known:
                self.extra.addItem(str(d))
        box.addWidget(self.extra)
        actions = QHBoxLayout()
        actions.addWidget(button("Adicionar pasta…", None, self.add_folder))
        actions.addWidget(button("Remover", "Ghost", self.remove_folder))
        actions.addStretch(1)
        box.addLayout(actions)
        box.addStretch(1)
        grid.addWidget(folders, 0, 0, 2, 1)

        modes, box = card()
        box.addWidget(label("COMO O CLAUDE AGE", "Section"))
        self.mode_group = QButtonGroup(self)
        current = settings.get("defaultMode", "default")
        for key, title, text in PERMISSION_MODES:
            rb = QRadioButton(title)
            rb.setProperty("mode", key)
            rb.setChecked(key == current)
            rb.setCursor(Qt.PointingHandCursor)
            self.mode_group.addButton(rb)
            box.addWidget(rb)
            hint = label(text, "Small", wrap=True)
            hint.setContentsMargins(30, 0, 0, 2)
            box.addWidget(hint)
        grid.addWidget(modes, 0, 1)

        protected, box = card()
        head = QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(IconTile("lock", self.accent, 30))
        head.addWidget(label("Sempre protegido", "H2"))
        head.addStretch(1)
        box.addLayout(head)
        box.addWidget(label(PROTECTED_TEXT,
                            "Small", wrap=True))
        grid.addWidget(protected, 1, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

    def add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Liberar pasta para o Claude", str(HOME))
        if folder and not self.extra.findItems(folder, Qt.MatchExactly):
            self.extra.addItem(folder)

    def remove_folder(self) -> None:
        for item in self.extra.selectedItems():
            self.extra.takeItem(self.extra.row(item))

    def commit(self) -> None:
        folders =[str(self.dirs[k]) for k, cb in self.checks.items() if cb.isChecked()]
        folders += [self.extra.item(i).text() for i in range(self.extra.count())]
        checked = self.mode_group.checkedButton()
        mode = checked.property("mode") if checked else "default"

        path = CLAUDE_DIR / "settings.json"
        data = read_json(path)
        perms = data.setdefault("permissions", {})
        perms["additionalDirectories"] = folders
        perms["defaultMode"] = mode
        deny = perms.setdefault("deny", [])
        deny.extend(rule for rule in PROTECTED_RULES if rule not in deny)
        write_json(path, data)
        for folder in folders:
            try:
                Path(folder).mkdir(parents=True, exist_ok=True)
            except OSError:
                pass


class LookPage(Page):
    eyebrow = "PASSO 4 DE 5 · APARÊNCIA"
    title = "Deixe o Clone OS com a sua cara"
    lead = "As mudanças são aplicadas na hora. Você também pode pedir ao Claude: “deixa o tema claro com destaque verde”."

    def build(self, layout: QVBoxLayout) -> None:
        state = self.win.look

        layout.addWidget(label("TEMA", "Section"))
        row = QHBoxLayout()
        row.setSpacing(14)
        self.theme_group = QButtonGroup(self)
        for key, title in (("dark", "Escuro"), ("light", "Claro")):
            tc = ThemeCard(key, title, self.win)
            tc.setChecked(state["theme"] == key)
            tc.clicked.connect(lambda _=False, k=key: self.set_theme(k))
            self.theme_group.addButton(tc)
            row.addWidget(tc)
        row.addStretch(1)
        layout.addLayout(row)

        layout.addSpacing(14)
        layout.addWidget(label("COR DE DESTAQUE", "Section"))
        row = QHBoxLayout()
        row.setSpacing(6)
        self.accent_group = QButtonGroup(self)
        current = state["accent"] if state["accent"] != "auto" else ACCENTS[0][1]
        for name, color in ACCENTS:
            sw = Swatch(name, color, self.win)
            sw.setChecked(color.lower() == current.lower())
            sw.clicked.connect(lambda _=False, c=color: self.set_accent(c))
            self.accent_group.addButton(sw)
            row.addWidget(sw)
        row.addSpacing(8)
        row.addWidget(button("Outra cor…", "Ghost", self.pick_accent))
        row.addStretch(1)
        layout.addLayout(row)

        layout.addSpacing(14)
        head = QHBoxLayout()
        head.addWidget(label("PAPEL DE PAREDE", "Section"))
        head.addStretch(1)
        head.addWidget(button("Escolher imagem…", "Ghost", self.pick_wallpaper))
        head.addWidget(button("Mais opções", "Ghost", lambda: run(["systemsettings", "kcm_colors"])))
        layout.addLayout(head)
        grid = QGridLayout()
        grid.setSpacing(12)
        self.wall_group = QButtonGroup(self)
        for i, (key, title) in enumerate(WALLPAPERS):
            tile = WallpaperTile(key, title, wallpaper_image(key), self.win)
            tile.setChecked(state["wallpaper"] == key)
            tile.clicked.connect(lambda _=False, k=key: self.set_wallpaper(k))
            self.wall_group.addButton(tile)
            grid.addWidget(tile, i // 3, i % 3)
        grid.setColumnStretch(3, 1)
        layout.addLayout(grid)

    def set_theme(self, theme: str) -> None:
        run(["clonectl", "theme", theme])
        changes = {"theme": theme}
        if self.win.look.get("wallpaper") in ("bloom", "brisa"):
            changes["wallpaper"] = "brisa" if theme == "light" else "bloom"
            for b in self.wall_group.buttons():
                b.setChecked(b.key == changes["wallpaper"])
        self.win.update_look(**changes)

    def set_accent(self, color: str) -> None:
        run(["clonectl", "accent", color])
        self.win.update_look(accent=color)

    def pick_accent(self) -> None:
        color = QColorDialog.getColor(QColor(self.win.accent), self, "Cor de destaque")
        if color.isValid():
            self.accent_group.setExclusive(False)
            for b in self.accent_group.buttons():
                b.setChecked(False)
            self.accent_group.setExclusive(True)
            self.set_accent(color.name())

    def set_wallpaper(self, key: str) -> None:
        run(["clonectl", "wallpaper", key])
        self.win.update_look(wallpaper=key)

    def pick_wallpaper(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Escolher papel de parede", str(HOME),
                                              "Imagens (*.png *.jpg *.jpeg *.webp *.svg)")
        if path:
            self.wall_group.setExclusive(False)
            for b in self.wall_group.buttons():
                b.setChecked(False)
            self.wall_group.setExclusive(True)
            self.set_wallpaper(path)


class DonePage(Page):
    eyebrow = "TUDO PRONTO"
    title = "Pronto para usar"
    lead = "O Claude fica a um atalho de distância, em qualquer lugar do sistema, como o Copilot no Windows."

    def build(self, layout: QVBoxLayout) -> None:
        frame, box = card()
        line = QHBoxLayout()
        line.setSpacing(14)
        line.addWidget(IconTile("keyboard", self.accent, 44))
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(label("Abrir o Terminal Claude", "H2"))
        text.addWidget(label("Tecla Windows (Meta) + C, ou o ícone “Terminal Claude” na área de trabalho.", "Muted"))
        line.addLayout(text, 1)
        for key in ("Meta", "+", "C"):
            line.addWidget(label(key, None if key == "+" else "Key"))
        box.addLayout(line)
        layout.addWidget(frame)
        layout.addSpacing(10)

        frame, box = card()
        line = QHBoxLayout()
        line.setSpacing(14)
        line.addWidget(IconTile("palette", self.accent, 44))
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(label("Configurações", "H2"))
        text.addWidget(label("Tecla Windows + I: sistema, rede, aparência, barra de tarefas e atualizações.", "Muted"))
        line.addLayout(text, 1)
        for key in ("Meta", "+", "I"):
            line.addWidget(label(key, None if key == "+" else "Key"))
        box.addLayout(line)
        layout.addWidget(frame)
        layout.addSpacing(10)

        layout.addWidget(label("EXPERIMENTE PEDIR AO CLAUDE", "Section"))
        grid = QGridLayout()
        grid.setSpacing(12)
        examples = [
            "Organize minha pasta Downloads por tipo de arquivo.",
            "Crie uma planilha com os gastos do mês a partir destes PDFs.",
            "Deixe o tema claro e a barra de tarefas à esquerda.",
            "Resuma os documentos da pasta Documentos/Faculdade.",
        ]
        for i, example in enumerate(examples):
            frame, box = card()
            line = QHBoxLayout()
            line.setSpacing(12)
            line.addWidget(IconTile("chat", lambda: CLAY, 32), 0, Qt.AlignTop)
            line.addWidget(label(f"“{example}”", None, wrap=True), 1)
            box.addLayout(line)
            grid.addWidget(frame, i // 2, i % 2)
        layout.addLayout(grid)

        layout.addSpacing(14)
        row = QHBoxLayout()
        self.show_again = QCheckBox("Mostrar esta tela ao iniciar a sessão")
        self.show_again.setCursor(Qt.PointingHandCursor)
        row.addWidget(self.show_again)
        row.addStretch(1)
        row.addWidget(button("Abrir o Terminal Claude", "Claude", lambda: run(["/usr/local/bin/terminal-claude"])))
        layout.addLayout(row)


# --------------------------------------------------------------------------
# Janela
# --------------------------------------------------------------------------

class Welcome(QWidget):
    STEPS = ["Bem-vindo", "Conectar o Claude", "Permissões", "Aparência", "Pronto"]

    def __init__(self, force_live: bool = False):
        super().__init__()
        self.force_live = force_live
        self.look = look_state()
        runtime = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
        self.check_icon = Path(runtime) / "cloneos-check.svg"
        self.check_icon.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            + ICONS["check"].replace('"C"', '"#FFFFFF"') + "</svg>", encoding="utf-8")

        self.setObjectName("Root")
        self.setWindowTitle("Clone Welcome")
        self.setWindowIcon(QIcon(str(SHARE / "logo.svg")))
        self.resize(1080, 720)
        self.setMinimumSize(940, 640)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.build_sidebar())

        main = QVBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        self.stack = QStackedWidget()
        self.pages: list[Page] = []
        self.apply_style()
        for cls in (WelcomePage, ClaudePage, PermissionsPage, LookPage, DonePage):
            page = cls(self)
            self.pages.append(page)
            self.stack.addWidget(page)
        main.addWidget(self.stack, 1)
        main.addWidget(self.build_footer())
        root.addLayout(main, 1)
        self.go(0)

    # Aparência ------------------------------------------------------------

    @property
    def palette_colors(self) -> dict:
        return PALETTES["light" if self.look["theme"] == "light" else "dark"]

    @property
    def accent(self) -> str:
        return ACCENTS[0][1] if self.look["accent"] == "auto" else self.look["accent"]

    def apply_style(self) -> None:
        QApplication.instance().setStyleSheet(stylesheet(self.palette_colors, self.accent, self.check_icon))
        self.update()
        for w in self.findChildren(QWidget):
            w.update()

    def update_look(self, **changes) -> None:
        self.look.update(changes)
        if DRY_RUN:
            write_json(CONFIG_DIR / "look.json", self.look)
        self.apply_style()

    # Estrutura ------------------------------------------------------------

    def build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(260)
        box = QVBoxLayout(side)
        box.setContentsMargins(22, 28, 22, 22)
        box.setSpacing(0)

        brand = QHBoxLayout()
        brand.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(svg_pixmap((SHARE / "logo.svg").read_text(encoding="utf-8"), 40))
        brand.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label("Clone OS", "Brand"))
        names.addWidget(label(os_version(), "Small"))
        brand.addLayout(names, 1)
        box.addLayout(brand)
        box.addSpacing(34)

        self.steps = StepList(self.STEPS, self)
        self.steps.clicked.connect(self.go)
        box.addWidget(self.steps)
        box.addStretch(1)

        if IS_LIVE or self.force_live:
            pill = label("MODO LIVE", "Pill")
            pill.setAlignment(Qt.AlignCenter)
            box.addWidget(pill, 0, Qt.AlignLeft)
            box.addSpacing(10)
        box.addWidget(label("Arch Linux · KDE Plasma · Claude", "Small"))
        return side

    def build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("Footer")
        row = QHBoxLayout(footer)
        row.setContentsMargins(48, 14, 48, 18)
        self.back_btn = button("Voltar", "Ghost", lambda: self.go(self.index - 1))
        self.skip_btn = button("Pular", "Ghost", lambda: self.go(self.index + 1))
        self.next_btn = button("Continuar", "Primary", self.next)
        self.next_btn.setMinimumWidth(130)
        row.addWidget(self.back_btn)
        row.addStretch(1)
        row.addWidget(self.skip_btn)
        row.addWidget(self.next_btn)
        return footer

    # Navegação ------------------------------------------------------------

    index = 0

    def go(self, index: int) -> None:
        index = max(0, min(index, len(self.pages) - 1))
        if index != self.index:
            self.pages[self.index].on_leave()
        self.index = index
        self.stack.setCurrentIndex(index)
        self.pages[index].on_enter()
        self.steps.set_current(index)
        last = index == len(self.pages) - 1
        self.back_btn.setVisible(index > 0)
        self.skip_btn.setVisible(0 < index < len(self.pages) - 1)
        self.next_btn.setText("Concluir" if last else "Começar" if index == 0 else "Continuar")

    def next(self) -> None:
        self.pages[self.index].commit()
        if self.index < len(self.pages) - 1:
            self.go(self.index + 1)
        else:
            self.finish()

    def finish(self) -> None:
        self.pages[self.index].on_leave()
        show = self.pages[-1].show_again.isChecked()
        write_json(CONFIG_DIR / "welcome.json", {"completed": True, "show_on_startup": show})
        self.close()


def os_version() -> str:
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if line.startswith("VERSION="):
                return line.split("=", 1)[1].strip('"')
    except OSError:
        pass
    return "0.4 (notebook)"


def should_autostart() -> bool:
    state = read_json(CONFIG_DIR / "welcome.json")
    return not state.get("completed") or state.get("show_on_startup", False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Assistente de boas-vindas do Clone OS")
    parser.add_argument("--autostart", action="store_true", help="abre só se o assistente ainda não foi concluído")
    parser.add_argument("--page", type=int, default=1, help="página inicial (1 a 5)")
    parser.add_argument("--live", action="store_true", help="simula o modo live")
    parser.add_argument("--screenshots", metavar="PASTA", help="salva uma imagem de cada página e sai")
    args = parser.parse_args()

    if args.autostart and not should_autostart():
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("Clone Welcome")
    app.setDesktopFileName("clone-welcome")
    win = Welcome(force_live=args.live)
    win.go(args.page - 1)

    if args.screenshots:
        out = Path(args.screenshots)
        out.mkdir(parents=True, exist_ok=True)
        win.show()
        for i in range(len(win.pages)):
            win.go(i)
            app.processEvents()
            win.grab().save(str(out / f"{i + 1}-{win.STEPS[i].lower().replace(' ', '-')}.png"))
        win.go(3)
        look = win.pages[3]
        look.theme_group.buttons()[1].click()
        look.accent_group.buttons()[3].click()
        look.wall_group.buttons()[1].click()
        app.processEvents()
        win.grab().save(str(out / "4-aparencia-claro.png"))
        return 0

    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
