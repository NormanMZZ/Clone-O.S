#!/usr/bin/env python3
"""Configurações do Clone OS, no estilo do app Configurações do Windows 11.

Barra lateral com as categorias e busca; as páginas próprias (Personalização,
Privacidade e segurança, Claude, Atualizações, Sobre) mexem no sistema pelos mesmos
comandos que o Claude usa (clonectl, clone-update, terminal-claude). O resto abre o
módulo correspondente do KDE (kcmshell6), como um painel por cima.

Fora do Clone OS (ex.: Windows) roda em modo de demonstração, como o Clone Welcome.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QProcess, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "welcome"))
import clone_welcome as cw  # noqa: E402

cw.ICONS.update({
    "monitor": '<rect x="3" y="4" width="18" height="12" rx="2.2" fill="none" stroke="C" stroke-width="1.8"/><path d="M9 20h6M12 16v4" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round"/>',
    "bluetooth": '<path d="M7 7.5l10 9-5 4.5V3l5 4.5-10 9" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    "wifi": '<path d="M2.5 9a14 14 0 0 1 19 0M5.8 12.5a9.2 9.2 0 0 1 12.4 0M9.2 16a4.4 4.4 0 0 1 5.6 0" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="19.3" r="1.3" fill="C"/>',
    "brush": '<path d="M14.5 4.5l5 5-8.5 8.5-5-5z" fill="none" stroke="C" stroke-width="1.8" stroke-linejoin="round"/><path d="M6 13c-2 0-3 1.6-3 3.4V20h3.6c1.8 0 3.4-1 3.4-3" fill="none" stroke="C" stroke-width="1.8" stroke-linejoin="round"/>',
    "apps": '<rect x="3.5" y="3.5" width="7" height="7" rx="1.8" fill="none" stroke="C" stroke-width="1.8"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.8" fill="none" stroke="C" stroke-width="1.8"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.8" fill="none" stroke="C" stroke-width="1.8"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.8" fill="none" stroke="C" stroke-width="1.8"/>',
    "user": '<circle cx="12" cy="8.5" r="4" fill="none" stroke="C" stroke-width="1.8"/><path d="M4.5 20.5c.8-4 3.8-6 7.5-6s6.7 2 7.5 6" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round"/>',
    "clock": '<circle cx="12" cy="12" r="9" fill="none" stroke="C" stroke-width="1.8"/><path d="M12 7v5.2l3.4 2" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    "access": '<circle cx="12" cy="4.8" r="1.8" fill="C"/><path d="M5 8.5l7 1.5 7-1.5M12 10v4.5M12 14.5l-3.5 6M12 14.5l3.5 6" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    "update": '<path d="M19.5 12a7.5 7.5 0 0 1-13.2 4.9M4.5 12A7.5 7.5 0 0 1 17.7 7.1" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round"/><path d="M18.5 3.5v4h-4M5.5 20.5v-4h4" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    "info": '<circle cx="12" cy="12" r="9" fill="none" stroke="C" stroke-width="1.8"/><path d="M12 11v5.5" stroke="C" stroke-width="1.9" stroke-linecap="round"/><circle cx="12" cy="7.8" r="1.2" fill="C"/>',
    "sound": '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z" fill="none" stroke="C" stroke-width="1.8" stroke-linejoin="round"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round"/>',
    "bell": '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15z" fill="none" stroke="C" stroke-width="1.8" stroke-linejoin="round"/><path d="M10 20.5a2.2 2.2 0 0 0 4 0" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round"/>',
    "battery": '<rect x="2.5" y="7" width="17" height="10" rx="2.2" fill="none" stroke="C" stroke-width="1.8"/><path d="M21.5 10.5v3" stroke="C" stroke-width="1.8" stroke-linecap="round"/><rect x="5" y="9.5" width="8" height="5" rx="1" fill="C"/>',
    "mouse": '<rect x="6.5" y="3" width="11" height="18" rx="5.5" fill="none" stroke="C" stroke-width="1.8"/><path d="M12 7v3" stroke="C" stroke-width="1.8" stroke-linecap="round"/>',
    "drive": '<rect x="3" y="13" width="18" height="7" rx="2" fill="none" stroke="C" stroke-width="1.8"/><path d="M5 13l2.5-8h9L19 13" fill="none" stroke="C" stroke-width="1.8" stroke-linejoin="round"/><circle cx="16.5" cy="16.5" r="1.1" fill="C"/>',
    "font": '<path d="M4 19l5.5-14h1L16 19M6.2 13.5h7.6" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 12.5c2.5-1.2 4.5 0 4.5 2.2V19M21.5 15.5c-3 0-4.8.6-4.8 2s1 1.7 2 1.7c1.5 0 2.8-1 2.8-2.5" fill="none" stroke="C" stroke-width="1.6" stroke-linecap="round"/>',
    "language": '<path d="M3.5 5.5h10M8.5 3.5v2M6 5.5c.8 3.4 3 6 6 7.5M11 5.5c-.8 3.6-3.4 6.6-7 8" fill="none" stroke="C" stroke-width="1.7" stroke-linecap="round"/><path d="M12.5 20.5l4-10 4 10M14 17h5" fill="none" stroke="C" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>',
    "chevron": '<path d="M9 5.5l6.5 6.5L9 18.5" fill="none" stroke="C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="C" stroke-width="1.8"/><path d="M15.5 15.5l5 5" stroke="C" stroke-width="1.9" stroke-linecap="round"/>',
    "power": '<path d="M12 3.5v8" stroke="C" stroke-width="1.9" stroke-linecap="round"/><path d="M7 6.5a7.5 7.5 0 1 0 10 0" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round"/>',
    "chip": '<rect x="6" y="6" width="12" height="12" rx="2" fill="none" stroke="C" stroke-width="1.8"/><rect x="9.5" y="9.5" width="5" height="5" rx="1" fill="C"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3" stroke="C" stroke-width="1.6" stroke-linecap="round"/>',
})

DRY_RUN = cw.DRY_RUN
HOME = cw.HOME
CONFIG_DIR = cw.CONFIG_DIR
CLAY = cw.CLAY

# Categorias da barra lateral, na ordem do Windows 11 (com a página do Claude antes das Atualizações).
CATEGORIES = [
    ("system", "Sistema", "monitor", "#1793D1"),
    ("devices", "Bluetooth e dispositivos", "bluetooth", "#3B82F6"),
    ("network", "Rede e internet", "wifi", "#0EA5E9"),
    ("personalization", "Personalização", "brush", "#EC4899"),
    ("apps", "Aplicativos", "apps", "#8B5CF6"),
    ("accounts", "Contas", "user", "#10B981"),
    ("time", "Hora e idioma", "clock", "#F59E0B"),
    ("accessibility", "Acessibilidade", "access", "#06B6D4"),
    ("privacy", "Privacidade e segurança", "shield", "#64748B"),
    ("claude", "Claude", "sparkle", CLAY),
    ("updates", "Atualizações", "update", "#1793D1"),
]

# Programas opcionais dos repositórios oficiais do Arch (o equivalente à loja).
OPTIONAL_APPS = [
    ("thunderbird", "Thunderbird", "E-mail e agenda"),
    ("gimp", "GIMP", "Edição de fotos e imagens"),
    ("vlc", "VLC", "Reprodutor de vídeo que abre qualquer formato"),
    ("obs-studio", "OBS Studio", "Gravar a tela e fazer lives"),
    ("telegram-desktop", "Telegram", "Mensagens"),
    ("discord", "Discord", "Chat de voz e texto"),
    ("kdenlive", "Kdenlive", "Edição de vídeo"),
    ("krita", "Krita", "Desenho e pintura digital"),
]


# --------------------------------------------------------------------------
# Sistema
# --------------------------------------------------------------------------

def run(cmd: list[str]) -> None:
    cw.run(cmd)


def kcm(module: str):
    return lambda: run(["kcmshell6", module])


def output(cmd: list[str], fallback: str = "", timeout: float = 4) -> str:
    if DRY_RUN:
        return fallback
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return fallback


def read(path: str, fallback: str = "") -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return fallback


def os_release(key: str, fallback: str) -> str:
    for line in read("/etc/os-release").splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip('"')
    return fallback


def full_name() -> str:
    if DRY_RUN:
        return "Gabriel"
    try:
        import pwd
        entry = pwd.getpwuid(os.getuid())
        return entry.pw_gecos.split(",")[0] or entry.pw_name
    except (ImportError, KeyError):
        return os.environ.get("USER", "Você")


def cpu_model() -> str:
    for line in read("/proc/cpuinfo").splitlines():
        if line.startswith("model name"):
            return " ".join(line.split(":", 1)[1].replace("(R)", "").replace("(TM)", "").split())
    return "Intel Core i5 de 8ª geração" if DRY_RUN else platform.processor() or "Desconhecido"


def mem_total() -> str:
    for line in read("/proc/meminfo").splitlines():
        if line.startswith("MemTotal:"):
            return f"{int(line.split()[1]) / 1024 / 1024:.1f} GB".replace(".", ",")
    return "8 GB"


def device_model() -> str:
    vendor = read("/sys/class/dmi/id/sys_vendor")
    product = read("/sys/class/dmi/id/product_name")
    text = " ".join(x for x in (vendor, product) if x and "O.E.M" not in x and "System Product" not in x)
    return text or ("Notebook" if DRY_RUN else "Computador")


def disk_summary() -> str:
    if DRY_RUN:
        return "HD de 1 TB · sistema usando 9,8 GB de 80 GB"
    try:
        st = os.statvfs("/")
        used = (st.f_blocks - st.f_bfree) * st.f_frsize / 1e9
        total = st.f_blocks * st.f_frsize / 1e9
    except OSError:
        return "Desconhecido"
    source = output(["findmnt", "-nvo", "SOURCE", "/"])
    kind = "HD" if output(["lsblk", "-nso", "ROTA", source]).split()[-1:] == ["1"] else "SSD"
    return f"{kind} · sistema usando {used:.1f} GB de {total:.0f} GB".replace(".", ",")


def gpu_name() -> str:
    for line in output(["lspci"], "VGA compatible controller: Intel Corporation UHD Graphics 620").splitlines():
        if "VGA compatible" in line or "3D controller" in line:
            name = line.split(": ", 1)[-1]
            return name.replace("Corporation ", "").split(" (rev")[0]
    return "Desconhecida"


def service_active(name: str, user: bool = False) -> bool:
    if DRY_RUN:
        return True
    cmd = ["systemctl", "--user"] if user else ["systemctl"]
    return output(cmd + ["is-active", name]) == "active"


def security_status() -> dict:
    """Estado das proteções, lido pelo cloneos-seguranca (não precisa de senha)."""
    if DRY_RUN:
        return {"uefi": True, "secure_boot": False, "setup_mode": False, "tpm2": True, "tpm_unlock": False,
                "encrypted": True, "apparmor": True, "lockdown": "integrity", "firewall": True,
                "antivirus_updated": time.time() - 5 * 3600}
    try:
        return json.loads(output(["/usr/local/bin/cloneos-seguranca", "status"], "{}"))
    except ValueError:
        return {}


def installed(package: str) -> bool:
    if DRY_RUN:
        return package in ("vlc",)
    return subprocess.run(["pacman", "-Q", package], capture_output=True).returncode == 0


def clear_widget(widget: QWidget) -> None:
    """Tira o widget da tela na hora (o deleteLater sozinho deixa ele visível até o próximo ciclo)."""
    widget.hide()
    widget.setParent(None)
    widget.deleteLater()


def look() -> dict:
    state = cw.look_state()
    state.setdefault("taskbar", "center")
    state.setdefault("taskbar_autohide", "off")
    return state


# --------------------------------------------------------------------------
# Widgets
# --------------------------------------------------------------------------

def extra_style(p: dict, accent: str) -> str:
    return f"""
    QLineEdit#Search {{ background: {p['card']}; border: 1px solid {p['border']}; border-bottom: 2px solid {p['border']};
                        border-radius: 8px; padding: 8px 12px 8px 36px; font-size: 14px; }}
    QLineEdit#Search:focus {{ border-bottom: 2px solid {accent}; }}
    QFrame#Row {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 10px; }}
    QFrame#Row[clickable="true"]:hover {{ background: {cw.mix(p['card'], p['text'], 0.05)}; }}
    QFrame#Hero {{ background: {cw.mix(p['card'], accent, 0.10)}; border: 1px solid {cw.mix(p['border'], accent, 0.35)}; border-radius: 12px; }}
    QLabel#RowTitle {{ font-size: 14px; }}
    QLabel#HeroTitle {{ font-size: 20px; font-weight: 700; }}
    QLabel#PageTitle {{ font-size: 28px; font-weight: 700; }}
    QLabel#UserName {{ font-size: 15px; font-weight: 650; }}
    QProgressBar {{ background: {p['card2']}; border: none; border-radius: 3px; height: 6px; }}
    QProgressBar::chunk {{ background: {accent}; border-radius: 3px; }}
    """


class Avatar(QLabel):
    def __init__(self, name: str, win: "Settings"):
        super().__init__()
        self.letter, self.win = (name[:1] or "?").upper(), win
        self.setFixedSize(56, 56)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self.win.accent))
        p.drawEllipse(QRectF(0, 0, 56, 56))
        f = QFont(self.font())
        f.setPixelSize(24)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(QRectF(0, 0, 56, 56), Qt.AlignCenter, self.letter)
        p.end()


class NavList(QWidget):
    """Lista de categorias com ícone colorido e o marcador de destaque do Windows 11."""

    clicked = Signal(str)
    ROW = 40

    def __init__(self, win: "Settings"):
        super().__init__()
        self.win, self.current, self.hover = win, "system", -1
        self.setFixedHeight(len(CATEGORIES) * self.ROW)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def set_current(self, key: str) -> None:
        self.current = key
        self.update()

    def mouseMoveEvent(self, event) -> None:
        self.hover = int(event.position().y() // self.ROW)
        self.update()

    def leaveEvent(self, _event) -> None:
        self.hover = -1
        self.update()

    def mousePressEvent(self, event) -> None:
        index = int(event.position().y() // self.ROW)
        if 0 <= index < len(CATEGORIES):
            self.clicked.emit(CATEGORIES[index][0])

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pal, accent = self.win.palette_colors, self.win.accent
        for i, (key, name, icon, color) in enumerate(CATEGORIES):
            y = i * self.ROW
            selected = key == self.current
            if selected or i == self.hover:
                bg = QColor(pal["text"])
                bg.setAlpha(22 if selected else 12)
                p.setPen(Qt.NoPen)
                p.setBrush(bg)
                p.drawRoundedRect(QRectF(0, y + 2, self.width(), self.ROW - 4), 6, 6)
            if selected:
                p.setBrush(QColor(accent))
                p.drawRoundedRect(QRectF(0, y + 12, 3, self.ROW - 24), 1.5, 1.5)
            p.drawPixmap(14, y + 10, cw.icon_pixmap(icon, color, 20))
            f = QFont(self.font())
            f.setPixelSize(14)
            f.setWeight(QFont.DemiBold if selected else QFont.Normal)
            p.setFont(f)
            p.setPen(QColor(pal["text"]))
            p.drawText(QRectF(46, y, self.width() - 50, self.ROW), Qt.AlignVCenter | Qt.AlignLeft, name)
        p.end()


class Row(QFrame):
    """Linha de configuração: ícone, título, descrição e, à direita, uma seta ou um controle."""

    def __init__(self, icon: str, title: str, subtitle: str = "", action=None, trailing: QWidget | None = None,
                 color_fn=None):
        super().__init__()
        self.action = action
        self.setObjectName("Row")
        self.setProperty("clickable", action is not None)
        self.setMinimumHeight(68)
        if action:
            self.setCursor(Qt.PointingHandCursor)
        line = QHBoxLayout(self)
        line.setContentsMargins(18, 12, 18, 12)
        line.setSpacing(16)
        line.addWidget(cw.IconTile(icon, color_fn or (lambda: Settings.instance.accent), 36))
        text = QVBoxLayout()
        text.setSpacing(1)
        text.addWidget(cw.label(title, "RowTitle"))
        self.subtitle = cw.label(subtitle, "Small", wrap=True)
        self.subtitle.setVisible(bool(subtitle))
        text.addWidget(self.subtitle)
        line.addLayout(text, 1)
        if trailing is not None:
            line.addWidget(trailing, 0, Qt.AlignVCenter)
        elif action:
            chevron = QLabel()
            chevron.setPixmap(cw.icon_pixmap("chevron", Settings.instance.palette_colors["muted"], 16))
            line.addWidget(chevron, 0, Qt.AlignVCenter)

    def mouseReleaseEvent(self, event) -> None:
        if self.action and event.button() == Qt.LeftButton:
            self.action()


# --------------------------------------------------------------------------
# Páginas
# --------------------------------------------------------------------------

class Page(QWidget):
    key = ""
    title = ""

    def __init__(self, win: "Settings"):
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
        self.box = QVBoxLayout(body)
        self.box.setContentsMargins(36, 30, 40, 30)
        self.box.setSpacing(6)
        self.box.addWidget(cw.label(self.title, "PageTitle"))
        self.box.addSpacing(16)
        self.build()
        self.box.addStretch(1)

    def build(self) -> None:
        raise NotImplementedError

    def section(self, text: str) -> None:
        self.box.addSpacing(14)
        self.box.addWidget(cw.label(text, "H2"))
        self.box.addSpacing(4)

    def row(self, icon: str, title: str, subtitle: str = "", action=None, trailing=None, keywords: str = "") -> Row:
        widget = Row(icon, title, subtitle, action, trailing)
        self.box.addWidget(widget)
        if action:
            self.win.registry.append((icon, title, subtitle, action, f"{title} {subtitle} {keywords}".lower()))
        return widget

    def on_enter(self) -> None:
        pass


class SystemPage(Page):
    key, title = "system", "Sistema"

    def build(self) -> None:
        hero, box = cw.card("Hero")
        line = QHBoxLayout()
        line.setSpacing(18)
        logo = QLabel()
        logo.setPixmap(cw.svg_pixmap((cw.SHARE / "logo.svg").read_text(encoding="utf-8"), 56))
        line.addWidget(logo)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(cw.label(socket.gethostname() if not DRY_RUN else "clone-notebook", "HeroTitle"))
        text.addWidget(cw.label(device_model(), "Muted"))
        line.addLayout(text, 1)
        line.addWidget(cw.button("Renomear", None, self.rename))
        box.addLayout(line)
        self.box.addWidget(hero)
        self.box.addSpacing(10)
        self.row("monitor", "Tela", "Resolução, escala, brilho e luz noturna", kcm("kcm_kscreen"), keywords="monitor brilho")
        self.row("sound", "Som", "Saída e entrada de áudio, volume dos aplicativos", kcm("kcm_pulseaudio"),
                 keywords="áudio volume microfone alto-falante fone")
        self.row("bell", "Notificações", "Alertas dos aplicativos e do sistema, não perturbe", kcm("kcm_notifications"))
        self.row("battery", "Energia e bateria", "Suspensão, tela desligada, modo de energia", kcm("kcm_powerdevilprofilesconfig"),
                 keywords="bateria suspender")
        self.row("monitor", "Luz noturna", "Tons mais quentes à noite para descansar a vista", kcm("kcm_nightlight"))
        self.row("info", "Sobre", "Especificações do notebook e do Clone OS", lambda: self.win.go("about"),
                 keywords="processador memória ram versão hardware")

    def rename(self) -> None:
        if DRY_RUN:
            print("[demo] renomear o computador")
            return
        name = output(["kdialog", "--title", "Renomear este computador", "--inputbox",
                       "Novo nome (letras, números e hífen):", socket.gethostname()], timeout=600)
        if name and all(c.isalnum() or c == "-" for c in name):
            run(["hostnamectl", "set-hostname", name])


class AboutPage(Page):
    key, title = "about", "Sistema  ›  Sobre"

    def build(self) -> None:
        specs = [
            ("Nome do computador", socket.gethostname() if not DRY_RUN else "clone-notebook"),
            ("Modelo", device_model()),
            ("Processador", cpu_model()),
            ("Memória RAM", mem_total()),
            ("Placa de vídeo", gpu_name()),
            ("Armazenamento", disk_summary()),
        ]
        system = [
            ("Sistema", os_release("PRETTY_NAME", "Clone OS 0.3.5 (notebook)")),
            ("Base", "Arch Linux"),
            ("Kernel", output(["uname", "-r"], "7.2.9-arch1-1")),
            ("Área de trabalho", output(["plasmashell", "--version"], "plasmashell 6.7.5").replace("plasmashell", "KDE Plasma")),
        ]
        for heading, items in (("Especificações do dispositivo", specs), ("Especificações do sistema", system)):
            frame, box = cw.card()
            box.addWidget(cw.label(heading, "H2"))
            grid = QGridLayout()
            grid.setHorizontalSpacing(30)
            grid.setVerticalSpacing(8)
            for i, (name, value) in enumerate(items):
                grid.addWidget(cw.label(name, "Muted"), i, 0)
                value_label = cw.label(value, None, wrap=True)
                value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                grid.addWidget(value_label, i, 1)
            grid.setColumnStretch(1, 1)
            box.addLayout(grid)
            self.box.addWidget(frame)
            self.box.addSpacing(10)
        self.row("info", "Informações detalhadas", "Hardware, memória, dispositivos e drivers", lambda: run(["kinfocenter"]))


class DevicesPage(Page):
    key, title = "devices", "Bluetooth e dispositivos"

    def build(self) -> None:
        self.row("bluetooth", "Bluetooth", "Parear fones, caixas de som, mouses e celulares", kcm("kcm_bluetooth"))
        self.row("mouse", "Touchpad", "Toque para clicar, rolagem, gestos", kcm("kcm_touchpad"))
        self.row("mouse", "Mouse", "Velocidade do ponteiro, botões, rolagem", kcm("kcm_mouse"))
        self.row("keyboard", "Teclado", "Layout (ABNT2), repetição de teclas, Num Lock", kcm("kcm_keyboard"))
        self.row("drive", "Pendrives e discos", "O que fazer ao conectar um pendrive ou HD externo", kcm("kcm_device_automounter"),
                 keywords="usb pendrive disco externo")


class NetworkPage(Page):
    key, title = "network", "Rede e internet"

    def build(self) -> None:
        self.row("wifi", "Wi-Fi e conexões", "Redes salvas, senhas, cabo, VPN e ancoragem do celular",
                 kcm("kcm_networkmanagement"), keywords="internet wifi rede cabo vpn")
        self.row("shield", "Firewall", "Bloqueia conexões que chegam de fora (ligado por padrão)", kcm("kcm_firewall"))


class PersonalizationPage(Page):
    key, title = "personalization", "Personalização"

    def build(self) -> None:
        state = self.win.look
        self.section("Tema")
        row = QHBoxLayout()
        row.setSpacing(14)
        self.theme_group = QButtonGroup(self)
        for key, title in (("dark", "Escuro"), ("light", "Claro")):
            tc = cw.ThemeCard(key, title, self.win)
            tc.setChecked(state["theme"] == key)
            tc.clicked.connect(lambda _=False, k=key: self.set_theme(k))
            self.theme_group.addButton(tc)
            row.addWidget(tc)
        row.addStretch(1)
        self.box.addLayout(row)

        self.section("Cor de destaque")
        row = QHBoxLayout()
        row.setSpacing(6)
        self.accent_group = QButtonGroup(self)
        current = state["accent"] if state["accent"] != "auto" else cw.ACCENTS[0][1]
        for name, color in cw.ACCENTS:
            sw = cw.Swatch(name, color, self.win)
            sw.setChecked(color.lower() == current.lower())
            sw.clicked.connect(lambda _=False, c=color: self.set_accent(c))
            self.accent_group.addButton(sw)
            row.addWidget(sw)
        row.addSpacing(8)
        row.addWidget(cw.button("Outra cor…", "Ghost", self.pick_accent))
        row.addStretch(1)
        self.box.addLayout(row)

        self.section("Papel de parede")
        grid = QGridLayout()
        grid.setSpacing(12)
        self.wall_group = QButtonGroup(self)
        for i, (key, title) in enumerate(cw.WALLPAPERS):
            tile = cw.WallpaperTile(key, title, cw.wallpaper_image(key), self.win)
            tile.setChecked(state["wallpaper"] == key)
            tile.clicked.connect(lambda _=False, k=key: self.set_wallpaper(k))
            self.wall_group.addButton(tile)
            grid.addWidget(tile, i // 3, i % 3)
        grid.setColumnStretch(3, 1)
        self.box.addLayout(grid)
        self.box.addWidget(cw.button("Escolher uma imagem…", "Ghost", self.pick_wallpaper), 0, Qt.AlignLeft)

        self.section("Barra de tarefas")
        align = QWidget()
        align_box = QHBoxLayout(align)
        align_box.setContentsMargins(0, 0, 0, 0)
        align_box.setSpacing(18)
        self.align_group = QButtonGroup(self)
        for key, title in (("center", "Centro"), ("left", "Esquerda")):
            rb = QRadioButton(title)
            rb.setChecked(state["taskbar"] == key)
            rb.setCursor(Qt.PointingHandCursor)
            rb.toggled.connect(lambda on, k=key: on and self.set_taskbar(k))
            self.align_group.addButton(rb)
            align_box.addWidget(rb)
        self.row("apps", "Alinhamento dos ícones", "No centro, como no Windows 11, ou à esquerda", trailing=align)
        self.autohide = QCheckBox("")
        self.autohide.setChecked(state["taskbar_autohide"] == "on")
        self.autohide.setCursor(Qt.PointingHandCursor)
        self.autohide.toggled.connect(self.set_autohide)
        self.row("apps", "Ocultar automaticamente", "A barra aparece quando o mouse chega na borda de baixo",
                 trailing=self.autohide)

        self.section("Mais opções")
        self.row("lock", "Tela de bloqueio", "Imagem, tempo para bloquear, senha ao voltar da suspensão",
                 kcm("kcm_screenlocker"))
        self.row("font", "Fontes", "Tamanho e tipo das letras do sistema", kcm("kcm_fonts"), keywords="letra tamanho texto")
        self.row("palette", "Ícones e cursor", "Pacotes de ícones e ponteiros do mouse", kcm("kcm_icons"))
        self.row("sparkle", "Efeitos e animações", "Transparências, sombras e animações das janelas", kcm("kcm_kwin_effects"))

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
                                              "Imagens (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.wall_group.setExclusive(False)
            for b in self.wall_group.buttons():
                b.setChecked(False)
            self.wall_group.setExclusive(True)
            self.set_wallpaper(path)

    def set_taskbar(self, align: str) -> None:
        run(["clonectl", "taskbar", align])
        self.win.update_look(taskbar=align)

    def set_autohide(self, on: bool) -> None:
        value = "on" if on else "off"
        run(["clonectl", "taskbar", "autohide", value])
        self.win.update_look(taskbar_autohide=value)


class AppsPage(Page):
    key, title = "apps", "Aplicativos"

    def build(self) -> None:
        self.row("apps", "Aplicativos padrão", "Navegador, e-mail, player e outros programas para cada tipo de arquivo",
                 kcm("kcm_componentchooser"), keywords="padrão navegador")
        self.row("power", "Inicialização", "Programas que abrem sozinhos ao entrar", kcm("kcm_autostart"))
        self.section("Instalar mais programas")
        self.box.addWidget(cw.label(
            "Programas dos repositórios oficiais do Arch, verificados pela assinatura. "
            "A instalação abre no terminal e pede a sua senha.", "Small", wrap=True))
        self.box.addSpacing(4)
        self.buttons: dict[str, QPushButton] = {}
        for package, name, text in OPTIONAL_APPS:
            btn = cw.button("Instalar", None, lambda _=False, p=package: self.install(p))
            self.buttons[package] = btn
            self.row("download", name, text, trailing=btn)
        self.refresh()

    def install(self, package: str) -> None:
        cw.in_terminal(f"Instalar {package}", ["sudo", "pacman", "-S", "--needed", package])

    def refresh(self) -> None:
        for package, btn in self.buttons.items():
            done = installed(package)
            btn.setText("Instalado" if done else "Instalar")
            btn.setEnabled(not done)

    def on_enter(self) -> None:
        self.refresh()


class AccountsPage(Page):
    key, title = "accounts", "Contas"

    def build(self) -> None:
        self.row("user", "Suas informações", "Nome, foto e senha da conta", kcm("kcm_users"), keywords="senha foto usuário")
        self.row("lock", "Bloqueio de tela", "Bloquear automaticamente e pedir senha", kcm("kcm_screenlocker"))


class TimePage(Page):
    key, title = "time", "Hora e idioma"

    def build(self) -> None:
        self.row("clock", "Data e hora", "Fuso horário e ajuste automático pela internet", kcm("kcm_clock"), keywords="relógio fuso")
        self.row("language", "Idioma e região", "Idioma, formatos de data, número e moeda", kcm("kcm_regionandlang"))
        self.row("keyboard", "Teclado", "Layout e atalhos de digitação", kcm("kcm_keyboard"))


class AccessibilityPage(Page):
    key, title = "accessibility", "Acessibilidade"

    def build(self) -> None:
        self.row("access", "Acessibilidade", "Teclas de aderência, alertas visuais, mouse pelo teclado", kcm("kcm_access"))
        self.row("font", "Tamanho do texto", "Letras maiores no sistema todo", kcm("kcm_fonts"))
        self.row("keyboard", "Teclado virtual", "Teclado na tela", kcm("kcm_virtualkeyboard"))
        self.row("sparkle", "Animações", "Deixar as animações mais rápidas ou desligá-las", kcm("kcm_animations"))


class PrivacyPage(Page):
    """O equivalente à "Segurança do Windows": cada proteção com o estado real e uma ação."""

    key, title = "privacy", "Privacidade e segurança"

    def build(self) -> None:
        hero, box = cw.card("Hero")
        line = QHBoxLayout()
        line.setSpacing(16)
        line.addWidget(cw.IconTile("shield", lambda: self.win.accent, 52))
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(cw.label("Segurança do Clone OS", "HeroTitle"))
        self.summary = cw.label("", "Muted", wrap=True)
        text.addWidget(self.summary)
        line.addLayout(text, 1)
        line.addWidget(cw.button("Verificar vírus agora", "Primary", lambda: run(["/usr/local/bin/clone-antivirus"])))
        box.addLayout(line)
        self.box.addWidget(hero)
        self.section("Proteção do dispositivo")
        self.cards = QVBoxLayout()
        self.cards.setSpacing(6)
        self.box.addLayout(self.cards)
        self.section("Claude")
        self.row("sparkle", "O que o Claude pode acessar", "Pastas liberadas e como ele age antes de mudar algo",
                 lambda: run(["clone-welcome", "--page", "3"]), keywords="permissões claude pastas")
        self.section("Outras configurações")
        self.row("folder", "Arquivos recentes", "O que o sistema lembra dos arquivos abertos", kcm("kcm_recentFiles"))
        self.refresh()

    def security_action(self, title: str, command: str):
        return lambda: cw.in_terminal(title, ["sudo", "/usr/local/bin/cloneos-seguranca", command])

    def refresh(self) -> None:
        s = security_status()
        av_time = float(s.get("antivirus_updated") or 0)
        av_fresh = av_time > 0 and time.time() - av_time < 4 * 86400
        av_when = time.strftime("%d/%m", time.localtime(av_time)) if av_time else ""
        kernel_ok = bool(s.get("apparmor")) and s.get("lockdown", "none") != "none"

        if not s.get("uefi", True):
            sb = (False, "Indisponível: o notebook iniciou no modo BIOS antigo.", None)
        elif s.get("secure_boot"):
            sb = (True, "Só sistemas assinados pelo Clone OS (ou pela Microsoft) iniciam neste notebook.", None)
        elif s.get("setup_mode"):
            sb = (False, "Pronta para ativar: falta cadastrar as chaves do Clone OS no firmware.",
                  ("Ativar", self.security_action("Inicialização Segura", "secure-boot")))
        else:
            sb = (False, "Desativada. Protege o boot contra adulteração, como no Windows 11.",
                  ("Ativar", self.security_action("Inicialização Segura", "secure-boot")))

        if s.get("tpm_unlock"):
            tpm = (True, "O disco abre com um PIN, só neste notebook e com o boot original (como o BitLocker).",
                   ("Desativar", self.security_action("TPM + PIN", "tpm-off")))
        elif not s.get("tpm2"):
            tpm = (False, "Não encontrei um chip TPM 2.0. Na BIOS, ative Security Chip (Intel PTT).", None)
        elif not s.get("encrypted"):
            tpm = (False, "Precisa do disco criptografado (escolhido na instalação).", None)
        else:
            tpm = (False, "Desativado: o disco pede a senha completa a cada boot.",
                   ("Ativar", self.security_action("TPM + PIN", "tpm")))

        items = [
            ("shield", "Firewall", bool(s.get("firewall")),
             "Conexões que chegam de fora são bloqueadas." if s.get("firewall") else "Desligado: o notebook fica exposto na rede.",
             ("Configurar", kcm("kcm_firewall"))),
            ("search", "Antivírus", av_fresh,
             f"Vacinas atualizadas em {av_when}. Nada fica rodando em segundo plano: verifique quando quiser."
             if av_fresh else "As vacinas ainda não foram baixadas (o sistema baixa sozinho, com internet).",
             ("Verificar", lambda: run(["/usr/local/bin/clone-antivirus"]))),
            ("lock", "Criptografia do disco", bool(s.get("encrypted")),
             "O HD inteiro só abre com a sua senha (LUKS2)." if s.get("encrypted")
             else "Desativada: só dá para ligar reinstalando.", None),
            ("power", "Inicialização Segura", *sb),
            ("chip", "Desbloqueio com TPM + PIN", *tpm),
            ("shield", "Proteção do kernel", kernel_ok,
             "AppArmor e lockdown ativos: nem programas com senha de administrador alteram o kernel."
             if kernel_ok else "Parcial: o AppArmor ou o lockdown do kernel não está ativo.", None),
            ("update", "Atualizações de segurança", service_active("cloneos-atualizacoes.timer", user=True),
             "O sistema avisa todo dia quando há correções.", ("Abrir", lambda: self.win.go("updates"))),
            ("user", "Conta de administrador", True, "A conta root fica bloqueada e o sudo sempre pede a sua senha.", None),
        ]
        # As linhas são criadas uma vez só; depois só mudam texto, selo e botão
        # (recriar widgets a cada visita bagunça o layout e gasta memória à toa).
        if not hasattr(self, "rows"):
            self.rows, self.actions = [], []
            for i, (icon, title, *_rest) in enumerate(items):
                trailing = QWidget()
                tl = QHBoxLayout(trailing)
                tl.setContentsMargins(0, 0, 0, 0)
                tl.setSpacing(10)
                badge = cw.label("", "BadgeOff")
                btn = cw.button("", None, lambda _=False, n=i: self.actions[n] and self.actions[n][1]())
                tl.addWidget(badge, 0, Qt.AlignVCenter)
                tl.addWidget(btn, 0, Qt.AlignVCenter)
                row = Row(icon, title, " ", trailing=trailing)
                self.cards.addWidget(row)
                self.rows.append((row, badge, btn))
                self.actions.append(None)
        active = 0
        for i, (_icon, _title, ok, subtitle, action) in enumerate(items):
            row, badge, btn = self.rows[i]
            active += ok
            row.subtitle.setText(subtitle)
            badge.setText("✓ Ativado" if ok else "Desativado")
            badge.setObjectName("BadgeOk" if ok else "BadgeOff")
            badge.style().unpolish(badge)
            badge.style().polish(badge)
            self.actions[i] = action
            btn.setVisible(action is not None)
            if action:
                btn.setText(action[0])
        missing = len(items) - active
        self.summary.setText(f"{active} de {len(items)} proteções ativas."
                             + (" Veja abaixo o que falta ligar." if missing else " Tudo protegido."))

    def on_enter(self) -> None:
        self.refresh()


class ClaudePage(Page):
    key, title = "claude", "Claude"

    def build(self) -> None:
        hero, box = cw.card("Hero")
        line = QHBoxLayout()
        line.setSpacing(16)
        line.addWidget(cw.IconTile("sparkle", lambda: CLAY, 52))
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(cw.label("Claude no Clone OS", "HeroTitle"))
        self.status = cw.label("", "Muted", wrap=True)
        text.addWidget(self.status)
        line.addLayout(text, 1)
        line.addWidget(cw.button("Abrir o Terminal Claude", "Claude", lambda: run(["/usr/local/bin/terminal-claude"])))
        box.addLayout(line)
        self.box.addWidget(hero)
        self.box.addSpacing(10)
        self.row("terminal", "Terminal Claude", "O Claude Code numa janela; também pela tecla Windows + C",
                 lambda: run(["/usr/local/bin/terminal-claude"]), keywords="claude code terminal")
        self.row("chat", "App do Claude", "Conversas, projetos e o Claude Code numa janela", lambda: run(["claude-desktop"]))
        self.row("lock", "Permissões", "Pastas que o Claude pode ver e como ele age", lambda: run(["clone-welcome", "--page", "3"]))
        self.row("globe", "Claude no navegador", "claude.ai no Brave; dica: na pesquisa, digite cl: e a pergunta",
                 lambda: run(["brave", "https://claude.ai"]))
        self.row("sparkle", "Assistente de boas-vindas", "Refazer a configuração inicial do Clone OS", lambda: run(["clone-welcome"]))
        self.refresh()

    def refresh(self) -> None:
        code = cw.claude_installed()
        connected = cw.claude_connected()
        if code and connected:
            text = "Conectado à sua conta. O Claude enxerga só as pastas que você liberou."
        elif code:
            text = "Claude Code instalado. Falta entrar com a sua conta: abra o Terminal Claude."
        else:
            text = "O Claude Code não está instalado."
        self.status.setText(text)

    def on_enter(self) -> None:
        self.refresh()


class UpdatesPage(Page):
    key, title = "updates", "Atualizações"

    def build(self) -> None:
        self.state_file = CONFIG_DIR / "atualizacoes.json"
        hero, box = cw.card("Hero")
        line = QHBoxLayout()
        line.setSpacing(16)
        line.addWidget(cw.IconTile("update", lambda: self.win.accent, 52))
        text = QVBoxLayout()
        text.setSpacing(2)
        self.headline = cw.label("", "HeroTitle")
        self.detail = cw.label("", "Muted", wrap=True)
        text.addWidget(self.headline)
        text.addWidget(self.detail)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.hide()
        text.addWidget(self.progress)
        line.addLayout(text, 1)
        self.check_btn = cw.button("Verificar atualizações", None, self.check)
        self.update_btn = cw.button("Atualizar agora", "Primary", lambda: run(["/usr/local/bin/clone-update"]))
        line.addWidget(self.check_btn)
        line.addWidget(self.update_btn)
        box.addLayout(line)
        self.box.addWidget(hero)
        self.box.addSpacing(10)
        self.row("shield", "Por que atualizar", "No Arch, as correções de segurança chegam pelas atualizações. "
                 "Atualize pelo menos uma vez por semana.")
        self.row("info", "Kernel em uso", output(["uname", "-r"], "7.2.9-arch1-1") +
                 " · se uma atualização der problema, aperte Esc ao ligar e escolha o kernel linux-lts")
        self.row("drive", "Firmware (BIOS)", "Atualizações da fabricante do notebook, quando disponíveis",
                 lambda: cw.in_terminal("Firmware", ["sh", "-c", "fwupdmgr refresh; fwupdmgr update; "
                                                     "read -rp 'Pressione Enter para fechar...' _"]),
                 keywords="bios fwupd")
        self.process: QProcess | None = None
        self.show_state()

    def saved(self) -> dict:
        return cw.read_json(self.state_file)

    def show_state(self) -> None:
        data = self.saved()
        when = data.get("checked")
        count = data.get("count")
        if when is None:
            self.headline.setText("Atualizações do Clone OS")
            self.detail.setText("Clique em Verificar atualizações para procurar versões novas.")
            self.update_btn.setVisible(True)
            return
        stamp = time.strftime("%d/%m às %H:%M", time.localtime(when))
        if count:
            self.headline.setText(f"{count} atualização(ões) disponível(is)")
            self.detail.setText(f"Última verificação: {stamp}. Inclui o Arch Linux, o Brave e o Claude.")
        else:
            self.headline.setText("Você está atualizado")
            self.detail.setText(f"Última verificação: {stamp}.")
        self.update_btn.setVisible(bool(count))

    def check(self) -> None:
        self.check_btn.setEnabled(False)
        self.progress.show()
        self.headline.setText("Verificando atualizações…")
        self.detail.setText("Consultando os repositórios do Arch e do AUR.")
        if DRY_RUN:
            QTimer.singleShot(1200, lambda: self.finished_check("linux 7.2.10\nbrave-bin 1.96.70\nmesa 26.2.5\n"))
            return
        self.process = QProcess(self)
        self.process.finished.connect(
            lambda *_: self.finished_check(bytes(self.process.readAllStandardOutput()).decode(errors="replace")))
        self.process.start("sh", ["-c", "checkupdates 2>/dev/null; yay -Qua 2>/dev/null; true"])

    def finished_check(self, out: str) -> None:
        count = len([line for line in out.splitlines() if line.strip()])
        cw.write_json(self.state_file, {"checked": time.time(), "count": count})
        self.progress.hide()
        self.check_btn.setEnabled(True)
        self.show_state()


class SearchPage(Page):
    key, title = "search", "Resultados da pesquisa"

    def build(self) -> None:
        self.results = QVBoxLayout()
        self.results.setSpacing(6)
        self.box.addLayout(self.results)

    def show_results(self, query: str) -> None:
        while self.results.count():
            item = self.results.takeAt(0)
            if item.widget():
                clear_widget(item.widget())
        words = query.lower().split()
        found = [r for r in self.win.registry if all(w in r[4] for w in words)]
        seen = set()
        for icon, title, subtitle, action, _ in found:
            if title in seen:
                continue
            seen.add(title)
            self.results.addWidget(Row(icon, title, subtitle, action))
        if not seen:
            self.results.addWidget(cw.label("Nada encontrado. Tente outra palavra, como “som”, “wi-fi” ou “tema”.", "Muted"))


# --------------------------------------------------------------------------
# Janela
# --------------------------------------------------------------------------

class Settings(QWidget):
    instance: "Settings"

    def __init__(self):
        super().__init__()
        Settings.instance = self
        self.look = look()
        self.registry: list = []
        runtime = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
        self.check_icon = Path(runtime) / "cloneos-check.svg"
        self.check_icon.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            + cw.ICONS["check"].replace('"C"', '"#FFFFFF"') + "</svg>", encoding="utf-8")
        self.setObjectName("Root")
        self.setWindowTitle("Configurações")
        self.setWindowIcon(QIcon.fromTheme("cloneos-configuracoes", QIcon(str(cw.SHARE / "logo.svg"))))
        self.resize(1120, 740)
        self.setMinimumSize(900, 600)
        self.apply_style()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.build_sidebar())
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.pages: dict[str, Page] = {}
        for cls in (SystemPage, AboutPage, DevicesPage, NetworkPage, PersonalizationPage, AppsPage, AccountsPage,
                    TimePage, AccessibilityPage, PrivacyPage, ClaudePage, UpdatesPage, SearchPage):
            page = cls(self)
            self.pages[cls.key] = page
            self.stack.addWidget(page)
        self.go("system")

    @property
    def palette_colors(self) -> dict:
        return cw.PALETTES["light" if self.look["theme"] == "light" else "dark"]

    @property
    def accent(self) -> str:
        return cw.ACCENTS[0][1] if self.look["accent"] == "auto" else self.look["accent"]

    def apply_style(self) -> None:
        pal = self.palette_colors
        QApplication.instance().setStyleSheet(
            cw.stylesheet(pal, self.accent, self.check_icon) + extra_style(pal, self.accent))
        for w in self.findChildren(QWidget):
            w.update()

    def update_look(self, **changes) -> None:
        self.look.update(changes)
        if DRY_RUN:
            cw.write_json(CONFIG_DIR / "look.json", self.look)
        self.apply_style()

    def build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(300)
        box = QVBoxLayout(side)
        box.setContentsMargins(18, 24, 18, 18)
        box.setSpacing(0)
        user = QHBoxLayout()
        user.setSpacing(12)
        name = full_name()
        user.addWidget(Avatar(name, self))
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(cw.label(name, "UserName"))
        names.addWidget(cw.label("Conta local · administrador", "Small"))
        user.addLayout(names, 1)
        box.addLayout(user)
        box.addSpacing(20)

        self.search = QLineEdit()
        self.search.setObjectName("Search")
        self.search.setPlaceholderText("Localizar uma configuração")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.on_search)
        icon = QLabel(self.search)
        icon.setPixmap(cw.icon_pixmap("search", self.palette_colors["muted"], 16))
        icon.move(12, 12)
        box.addWidget(self.search)
        box.addSpacing(16)

        self.nav = NavList(self)
        self.nav.clicked.connect(self.go)
        box.addWidget(self.nav)
        box.addStretch(1)
        box.addWidget(cw.label(os_release("PRETTY_NAME", "Clone OS 0.3.5 (notebook)"), "Small"))
        return side

    def go(self, key: str) -> None:
        page = self.pages[key]
        self.stack.setCurrentWidget(page)
        self.nav.set_current("system" if key == "about" else key)
        page.on_enter()

    def on_search(self, text: str) -> None:
        if text.strip():
            self.pages["search"].show_results(text.strip())
            self.stack.setCurrentWidget(self.pages["search"])
        else:
            self.go(self.nav.current)


def main() -> int:
    parser = argparse.ArgumentParser(description="Configurações do Clone OS")
    parser.add_argument("pagina", nargs="?", default="system", help="página inicial (ex.: personalization, updates)")
    parser.add_argument("--screenshots", metavar="PASTA", help="salva uma imagem de cada página e sai")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("Configurações")
    app.setDesktopFileName("cloneos-configuracoes")
    win = Settings()
    win.go(args.pagina if args.pagina in win.pages else "system")

    if args.screenshots:
        out = Path(args.screenshots)
        out.mkdir(parents=True, exist_ok=True)
        win.show()
        for key in ("system", "about", "personalization", "apps", "privacy", "claude", "updates"):
            win.go(key)
            app.processEvents()
            win.grab().save(str(out / f"config-{key}.png"))
        win.search.setText("som")
        app.processEvents()
        win.grab().save(str(out / "config-pesquisa.png"))
        return 0

    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
