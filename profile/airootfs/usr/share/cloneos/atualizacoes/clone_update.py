#!/usr/bin/env python3
"""Clone Update: as atualizações do Clone OS num app, no estilo do Windows Update.

Verifica sem senha (checkupdates, AUR e arch-audit), mostra o que vai mudar e
instala com a senha do usuário pela janela do KDE (pkexec + atualizar-sistema).
Brave, app do Claude, Claude Code e yay vêm do AUR: são compilados aqui como
usuário e só são instalados se a receita ainda baixar dos sites oficiais.
"""
from __future__ import annotations

import argparse
import email.utils
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QTextCursor
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout, QMessageBox, QPlainTextEdit,
                               QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "welcome"))
import clone_welcome as cw  # noqa: E402

HOME = Path.home()
STATE = cw.CONFIG_DIR / "atualizacoes.json"
AUR_DIR = HOME / ".cache/cloneos/atualizacoes/aur"
HELPER = os.environ.get("CLONE_UPDATE_HELPER", "/usr/lib/cloneos/atualizar-sistema")
ELEVATE = os.environ.get("CLONE_UPDATE_ELEVATE", "pkexec").split()
CHECK_CMD = os.environ.get("CLONE_UPDATE_CHECK", "checkupdates --nocolor")
PACMAN_LOG = Path(os.environ.get("CLONE_UPDATE_LOG", "/var/log/pacman.log"))
NEWS_URL = "https://archlinux.org/feeds/news/"

# Receitas do AUR aceitas e de onde elas podem baixar (iguais às do clone-update).
OFFICIAL = {
    "brave-bin": ("https://github.com/brave/",),
    "claude-desktop": ("https://downloads.claude.ai/",),
    "claude-code": ("https://downloads.claude.ai/", "https://code.claude.com/"),
    "yay-bin": ("https://github.com/Jguer/yay/",),
}

FRIENDLY = {
    "linux": "Kernel Linux", "linux-lts": "Kernel Linux LTS (reserva)", "linux-firmware": "Firmware do hardware",
    "intel-ucode": "Microcódigo do processador Intel", "systemd": "Base do sistema (systemd)",
    "glibc": "Biblioteca principal do sistema", "mesa": "Driver de vídeo (Mesa)", "vulkan-intel": "Vulkan (Intel)",
    "intel-media-driver": "Aceleração de vídeo (Intel)", "pipewire": "Som (PipeWire)", "wireplumber": "Som (WirePlumber)",
    "sof-firmware": "Firmware de som", "networkmanager": "Rede e Wi-Fi", "bluez": "Bluetooth",
    "plasma-workspace": "Área de trabalho (KDE Plasma)", "plasma-desktop": "Área de trabalho (KDE Plasma)",
    "kwin": "Janelas e efeitos (KWin)", "sddm": "Tela de login", "dolphin": "Explorador de Arquivos",
    "konsole": "Terminal", "kate": "Editor de texto (Kate)", "kwrite": "Bloco de Notas", "spectacle": "Ferramenta de Captura",
    "gwenview": "Fotos", "okular": "Leitor de PDF", "haruna": "Reprodutor de Mídia", "kolourpaint": "Paint",
    "kcalc": "Calculadora", "kamoso": "Câmera", "ark": "Compactador de arquivos", "brave-bin": "Brave",
    "claude-desktop": "Claude (app)", "claude-code": "Claude Code", "yay-bin": "yay (AUR)",
    "libreoffice-fresh": "LibreOffice", "openssl": "Criptografia (OpenSSL)", "sudo": "Permissões de administrador (sudo)",
    "pacman": "Gerenciador de pacotes (pacman)", "archlinux-keyring": "Chaves de segurança do Arch",
    "qt6-base": "Base dos apps (Qt 6)", "python": "Python", "pyside6": "Base dos apps do Clone OS (PySide6)",
    "clamav": "Antivírus (ClamAV)", "ufw": "Firewall", "apparmor": "AppArmor", "sbctl": "Inicialização Segura (sbctl)",
    "cryptsetup": "Criptografia do disco", "plymouth": "Tela de boot", "fwupd": "Atualizador de firmware",
    "thermald": "Controle de temperatura", "power-profiles-daemon": "Perfis de energia",
}
SYSTEM_PREFIXES = (
    "linux", "systemd", "glibc", "gcc", "mesa", "vulkan", "intel-", "libva", "sof-firmware", "alsa", "pipewire",
    "wireplumber", "networkmanager", "wpa_supplicant", "bluez", "openssl", "gnutls", "nss", "ca-certificates", "sudo",
    "pam", "shadow", "util-linux", "coreutils", "pacman", "archlinux-keyring", "cryptsetup", "lvm2", "mkinitcpio",
    "kmod", "dbus", "polkit", "apparmor", "ufw", "clamav", "sbctl", "plymouth", "tpm2", "fwupd", "openssh", "curl",
    "gnupg", "gpgme", "iptables", "nftables", "efibootmgr", "e2fsprogs", "zram", "thermald", "power-profiles",
)
APP_NAMES = {
    "brave-bin", "claude-desktop", "claude-code", "yay-bin", "dolphin", "konsole", "kate", "kwrite", "spectacle",
    "gwenview", "okular", "haruna", "kolourpaint", "kcalc", "kamoso", "ark", "alacritty", "git", "python",
    "pyside6", "htop", "btop", "fastfetch", "jq", "ripgrep",
}
DESKTOP_PREFIXES = (
    "plasma", "kf6", "kwin", "kde", "breeze", "kio", "kscreen", "kwallet", "powerdevil", "bluedevil", "kglobalacc",
    "kdecoration", "libplasma", "layer-shell-qt", "kpipewire", "kactivit", "milou", "kmenuedit", "kinfocenter",
    "systemsettings", "polkit-kde", "xdg-desktop-portal", "qt6", "qt5", "oxygen", "ocean-sound", "aurorae",
    "kwayland", "knighttime", "kirigami", "kitemmodels", "baloo", "frameworkintegration", "sddm", "xorg", "wayland",
    "libkscreen", "ksystemstats", "libksysguard", "kgamma", "drkonqi", "print-manager", "spectacle",
)
REBOOT_PREFIXES = ("linux", "intel-ucode", "systemd", "glibc", "mesa", "plasma-workspace", "kwin", "qt6-base",
                   "sddm", "dbus", "cryptsetup", "mkinitcpio", "plymouth", "nvidia")
GROUPS = [
    ("sistema", "Sistema e segurança", "Kernel, drivers, som, rede e proteções. Estas trazem as correções de segurança."),
    ("apps", "Aplicativos", "Brave, Claude e os apps do dia a dia."),
    ("desktop", "Área de trabalho (KDE Plasma)", "Barra de tarefas, janelas, menu Iniciar e a base dos apps."),
    ("outros", "Outros componentes", "Bibliotecas usadas pelos programas."),
]
ICONS = {
    "update": '<path d="M19.5 12a7.5 7.5 0 0 1-13.2 4.9M4.5 12A7.5 7.5 0 0 1 17.7 7.1" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round"/><path d="M18.5 3.5v4h-4M5.5 20.5v-4h4" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="C" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
    "alert": '<path d="M12 4l9 16H3z" fill="none" stroke="C" stroke-width="1.8" stroke-linejoin="round"/><path d="M12 10v4.5" stroke="C" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="17.3" r="1.1" fill="C"/>',
    "power": '<path d="M12 3.5v8" stroke="C" stroke-width="1.9" stroke-linecap="round"/><path d="M7 6.5a7.5 7.5 0 1 0 10 0" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round"/>',
    "news": '<rect x="3.5" y="4.5" width="17" height="15" rx="2.2" fill="none" stroke="C" stroke-width="1.8"/><path d="M7 9h10M7 12.5h10M7 16h6" stroke="C" stroke-width="1.7" stroke-linecap="round"/>',
    "history": '<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3M4.5 4.5v3.7h3.7" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 8v4.3l3 1.8" fill="none" stroke="C" stroke-width="1.8" stroke-linecap="round"/>',
}
for _k, _v in ICONS.items():
    cw.ICONS.setdefault(_k, _v)


def plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


# ---------------------------------------------------------------- verificação (sem senha)

def sh(cmd, timeout: int = 120) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


def group_of(name: str) -> str:
    if name in APP_NAMES or name.startswith(("libreoffice", "claude")):
        return "apps"
    if name.startswith(SYSTEM_PREFIXES) or "firmware" in name or "ucode" in name:
        return "sistema"
    if name.startswith(DESKTOP_PREFIXES):
        return "desktop"
    return "outros"


def needs_reboot(names) -> bool:
    return any(n.startswith(REBOOT_PREFIXES) for n in names)


def vercmp(a: str, b: str) -> int:
    code, out = sh(["vercmp", a, b], 10)
    try:
        return int(out.strip())
    except ValueError:
        return 0


def check_official() -> tuple[list[dict], str]:
    code, out = sh(CHECK_CMD, 300)
    if code not in (0, 2):
        return [], "Não foi possível consultar os repositórios do Arch. Confira a internet e tente de novo."
    items = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[2] == "->":
            items.append({"name": parts[0], "old": parts[1], "new": parts[3], "aur": False})
    return items, ""


def download_size(items: list[dict]) -> int:
    db = Path(os.environ.get("TMPDIR", "/tmp")) / f"checkup-db-{os.getuid()}"
    if not items or not db.is_dir():
        return 0
    code, out = sh(["pacman", "-Sup", "--dbpath", str(db), "--logfile", "/dev/null", "--print-format", "%s"], 60)
    total = 0
    for line in out.splitlines():
        if line.strip().isdigit():
            total += int(line)
    return total


def check_aur() -> tuple[list[dict], str]:
    code, out = sh(["pacman", "-Qm"], 30)
    local = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in OFFICIAL:
            local[parts[0]] = parts[1]
    if not local:
        return [], ""
    query = "&".join(f"arg[]={n}" for n in local)
    try:
        with urllib.request.urlopen(f"https://aur.archlinux.org/rpc/v5/info?{query}", timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError):
        return [], "Não foi possível consultar o AUR (Brave e Claude). Eles ficam para a próxima verificação."
    items = []
    for res in data.get("results", []):
        name, new = res.get("Name"), res.get("Version", "")
        if name in local and new and vercmp(new, local[name]) > 0:
            items.append({"name": name, "old": local[name], "new": new, "aur": True})
    return items, ""


def check_security() -> dict:
    code, out = sh(["arch-audit", "--upgradable", "--format", "%n|%s"], 60)
    found = {}
    for line in out.splitlines():
        if "|" in line:
            name, sev = line.split("|", 1)
            found[name.strip()] = sev.strip()
    return found


def last_full_upgrade() -> float:
    try:
        lines = PACMAN_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return 0.0
    first = 0.0
    for line in reversed(lines):
        if "starting full system upgrade" in line:
            return parse_log_time(line)
    if lines:
        first = parse_log_time(lines[0])
    return first


def parse_log_time(line: str) -> float:
    m = re.match(r"\[(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)([+-]\d{4})?\]", line)
    if not m:
        return 0.0
    try:
        stamp = datetime.strptime(m.group(1) + (m.group(2) or "+0000"), "%Y-%m-%dT%H:%M:%S%z")
        return stamp.timestamp()
    except ValueError:
        return 0.0


def check_news(since: float) -> list[dict]:
    try:
        with urllib.request.urlopen(NEWS_URL, timeout=15) as r:
            root = ET.fromstring(r.read())
    except (OSError, ET.ParseError):
        return []
    news = []
    for item in root.iter("item"):
        try:
            when = email.utils.parsedate_to_datetime(item.findtext("pubDate", "")).timestamp()
        except (TypeError, ValueError):
            continue
        if when > since:
            news.append({"title": item.findtext("title", ""), "link": item.findtext("link", ""), "when": when})
    return news[:3]


def history(limit: int = 6) -> list[dict]:
    try:
        lines = PACMAN_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    days: dict[str, list[str]] = {}
    for line in lines:
        m = re.search(r"\[ALPM\] upgraded (\S+) \((\S+) -> (\S+)\)", line)
        if m:
            day = line[1:11]
            days.setdefault(day, []).append(f"{m.group(1)}  {m.group(2)} → {m.group(3)}")
    out = []
    for day in sorted(days, reverse=True)[:limit]:
        try:
            label = datetime.strptime(day, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            label = day
        out.append({"day": label, "items": days[day]})
    return out


def boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return ""


def kernel_replaced() -> bool:
    return not Path(f"/usr/lib/modules/{os.uname().release}").is_dir()


def battery_warning() -> str:
    for bat in Path("/sys/class/power_supply").glob("BAT*"):
        try:
            cap = int((bat / "capacity").read_text().strip())
            status = (bat / "status").read_text().strip()
        except (OSError, ValueError):
            continue
        if status == "Discharging" and cap < 30:
            return f"A bateria está em {cap}%. Ligue o carregador antes de atualizar: se o notebook desligar no meio, o sistema pode ficar danificado."
    return ""


def space_warning() -> str:
    try:
        free = shutil.disk_usage("/").free
    except OSError:
        return ""
    if free < 3 * 1024 ** 3:
        return f"Só restam {free / 1024 ** 3:.1f} GB livres no disco do sistema. Libere espaço antes de atualizar."
    return ""


def fmt_size(n: int) -> str:
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.1f} GB".replace(".", ",")
    if n >= 1024 ** 2:
        return f"{round(n / 1024 ** 2)} MB"
    return f"{max(1, round(n / 1024))} KB" if n else ""


def when_text(ts: float) -> str:
    if not ts:
        return "nunca"
    d = datetime.fromtimestamp(ts)
    today = datetime.now().date()
    if d.date() == today:
        return f"hoje às {d:%H:%M}"
    if (today - d.date()).days == 1:
        return f"ontem às {d:%H:%M}"
    return f"{d:%d/%m} às {d:%H:%M}"


def srcinfo_ok(path: Path, prefixes: tuple[str, ...]) -> tuple[bool, list[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False, ["receita sem .SRCINFO"]
    bad = []
    for line in text.splitlines():
        m = re.match(r"\s*source(?:_x86_64)?\s*=\s*(.+)$", line)
        if not m:
            continue
        url = m.group(1).strip()
        if "::" in url:
            url = url.split("::", 1)[1]
        if re.match(r"^[a-z+]+://", url) and not url.startswith(prefixes):
            bad.append(url)
    return not bad, bad


# ---------------------------------------------------------------- widgets

class StatusIcon(QWidget):
    def __init__(self, size: int = 64):
        super().__init__()
        self.setFixedSize(size, size)
        self.kind, self.color, self.angle = "update", "#1793D1", 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    def set(self, kind: str, color: str, spinning: bool = False) -> None:
        self.kind, self.color = kind, color
        if spinning:
            self.timer.start(40)
        else:
            self.timer.stop()
            self.angle = 0
        self.update()

    def tick(self) -> None:
        self.angle = (self.angle + 8) % 360
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = QColor(self.color)
        bg.setAlpha(40)
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawEllipse(QRectF(0, 0, self.width(), self.height()))
        s = int(self.width() * 0.5)
        p.translate(self.width() / 2, self.height() / 2)
        p.rotate(self.angle)
        p.drawPixmap(-s // 2, -s // 2, cw.icon_pixmap(self.kind, self.color, s))


class Group(QFrame):
    def __init__(self, title: str, hint: str, items: list[dict], security: dict, accent: str, open_: bool):
        super().__init__()
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(6)
        head = QPushButton()
        head.setObjectName("GroupHead")
        head.setCursor(Qt.PointingHandCursor)
        sec = sum(1 for i in items if i["name"] in security)
        extra = f"  ·  {sec} de segurança" if sec else ""
        self.title = f"{title}  ·  {len(items)}{extra}"
        head.clicked.connect(self.toggle)
        lay.addWidget(head)
        self.head = head
        self.hint = cw.label(hint, "Small", wrap=True)
        lay.addWidget(self.hint)
        self.body = QWidget()
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 4, 0, 0)
        body.setSpacing(2)
        for it in sorted(items, key=lambda i: (i["name"] not in security, FRIENDLY.get(i["name"], i["name"]))):
            row = QHBoxLayout()
            row.setSpacing(10)
            name = FRIENDLY.get(it["name"])
            left = QVBoxLayout()
            left.setSpacing(0)
            left.addWidget(cw.label(name or it["name"], None))
            if name:
                left.addWidget(cw.label(it["name"], "Small"))
            row.addLayout(left, 1)
            if it["name"] in security:
                badge = cw.label("Segurança", "SecBadge")
                badge.setToolTip(f"Corrige uma falha de segurança (gravidade: {security[it['name']]})")
                row.addWidget(badge)
            if it.get("aur"):
                aur = cw.label("site oficial", "Pill")
                aur.setToolTip("Baixado do site oficial e conferido antes de instalar")
                row.addWidget(aur)
            ver = cw.label(f"{it['old']}  →  {it['new']}", "Version")
            row.addWidget(ver)
            holder = QWidget()
            holder.setLayout(row)
            body.addWidget(holder)
        lay.addWidget(self.body)
        # Estado próprio: isVisible() é falso enquanto a janela ainda não apareceu.
        self.opened = open_
        self.body.setVisible(open_)
        self.refresh()

    def toggle(self) -> None:
        self.opened = not self.opened
        self.body.setVisible(self.opened)
        self.refresh()

    def refresh(self) -> None:
        self.head.setText(("▾  " if self.opened else "▸  ") + self.title)


class Checker(QObject):
    done = Signal(dict)

    def run(self) -> None:
        threading.Thread(target=self.work, daemon=True).start()

    def work(self) -> None:
        official, err1 = check_official()
        aur, err2 = check_aur()
        security = check_security() if official else {}
        result = {
            "official": official, "aur": aur, "security": security, "errors": [e for e in (err1, err2) if e],
            "size": download_size(official), "news": check_news(last_full_upgrade()), "checked": time.time(),
        }
        self.done.emit(result)


# ---------------------------------------------------------------- janela

class Window(QWidget):
    def __init__(self, auto_check: bool):
        super().__init__()
        self.look = cw.look_state()
        self.p = cw.PALETTES["light" if self.look["theme"] == "light" else "dark"]
        self.accent = cw.ACCENTS[0][1] if self.look["accent"] == "auto" else self.look["accent"]
        self.setObjectName("Root")
        self.setWindowTitle("Clone Update")
        self.setWindowIcon(QIcon.fromTheme("system-software-update"))
        self.resize(980, 760)
        self.setMinimumSize(760, 560)
        runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
        check_icon = Path(runtime) / "cloneos-check.svg"
        check_icon.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
                              + cw.ICONS["check"].replace('"C"', '"#FFFFFF"') + "</svg>", encoding="utf-8")
        QApplication.instance().setStyleSheet(cw.stylesheet(self.p, self.accent, check_icon) + self.extra_style())

        self.state = cw.read_json(STATE)
        self.result: dict | None = self.state.get("result")
        self.running = False
        self.proc: QProcess | None = None
        self.upgraded: list[str] = []
        self.counts = {"down": 0, "inst": 0}
        self.total = 0
        self.errors: list[str] = []
        self.aur_queue: list[str] = []
        self.aur_files: list[str] = []
        self.aur_failed: list[str] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        host = QWidget()
        scroll.setWidget(host)
        hrow = QHBoxLayout(host)
        hrow.setContentsMargins(28, 26, 28, 26)
        hrow.addStretch(1)
        col = QWidget()
        col.setMaximumWidth(880)
        self.col = QVBoxLayout(col)
        self.col.setContentsMargins(0, 0, 0, 0)
        self.col.setSpacing(14)
        hrow.addWidget(col, 100)
        hrow.addStretch(1)

        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(cw.IconTile("update", lambda: self.accent, 44))
        tcol = QVBoxLayout()
        tcol.setSpacing(0)
        tcol.addWidget(cw.label("Clone Update", "H1"))
        tcol.addWidget(cw.label("Atualizações do Clone OS: Arch Linux, KDE Plasma, Brave e Claude", "Muted"))
        top.addLayout(tcol, 1)
        self.col.addLayout(top)

        # Cartão principal: estado, progresso e o botão da vez.
        hero, hbox = cw.card("Banner")
        line = QHBoxLayout()
        line.setSpacing(18)
        self.icon = StatusIcon(64)
        line.addWidget(self.icon, 0, Qt.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(4)
        self.headline = cw.label("", "HeroTitle", wrap=True)
        self.detail = cw.label("", "Muted", wrap=True)
        text.addWidget(self.headline)
        text.addWidget(self.detail)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        self.bar.hide()
        text.addWidget(self.bar)
        self.step = cw.label("", "Small", wrap=True)
        self.step.hide()
        text.addWidget(self.step)
        line.addLayout(text, 1)
        btns = QVBoxLayout()
        btns.setSpacing(8)
        self.primary = cw.button("", "Primary", self.primary_action)
        self.secondary = cw.button("Verificar atualizações", None, self.check)
        self.helpbtn = cw.button("Pedir ajuda ao Claude", "Claude", self.ask_claude)
        self.helpbtn.hide()
        for b in (self.primary, self.secondary, self.helpbtn):
            btns.addWidget(b)
        btns.addStretch(1)
        line.addLayout(btns)
        hbox.addLayout(line)
        self.col.addWidget(hero)

        self.notices = QVBoxLayout()
        self.notices.setSpacing(10)
        self.col.addLayout(self.notices)
        self.list_title = cw.label("", "Section")
        self.col.addWidget(self.list_title)
        self.groups = QVBoxLayout()
        self.groups.setSpacing(10)
        self.col.addLayout(self.groups)

        # Detalhes: a saída completa, como num terminal.
        self.log_toggle = cw.button("Mostrar detalhes (saída do pacman)", "Ghost", self.toggle_log)
        self.col.addWidget(self.log_toggle, 0, Qt.AlignLeft)
        self.log = QPlainTextEdit()
        self.log.setObjectName("Log")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(4000)
        self.log.setMinimumHeight(220)
        self.log.hide()
        self.col.addWidget(self.log)

        self.col.addWidget(cw.label("HISTÓRICO", "Section"))
        self.hist = QVBoxLayout()
        self.hist.setSpacing(8)
        self.col.addLayout(self.hist)

        self.col.addWidget(cw.label("OPÇÕES", "Section"))
        opts, obox = cw.card()
        self.daily = QCheckBox("Verificar todo dia e me avisar quando houver atualizações")
        self.daily.setChecked(self.timer_enabled())
        self.daily.toggled.connect(self.set_timer)
        obox.addWidget(self.daily)
        orow = QHBoxLayout()
        orow.addWidget(cw.button("Atualizar pelo terminal", None,
                                 lambda: cw.run(["/usr/local/bin/clone-update"])))
        orow.addWidget(cw.button("Firmware do notebook (BIOS)", None, lambda: cw.in_terminal(
            "Firmware", ["sh", "-c", "fwupdmgr refresh; fwupdmgr update; read -rp 'Pressione Enter para fechar...' _"])))
        orow.addStretch(1)
        obox.addLayout(orow)
        obox.addWidget(cw.label(
            "Se o notebook não iniciar depois de uma atualização: ligue segurando a barra de espaço e escolha "
            "o kernel linux-lts (o de reserva). Depois, atualize de novo por aqui.", "Small", wrap=True))
        self.col.addWidget(opts)
        self.col.addStretch(1)

        self.checker = Checker()
        self.checker.done.connect(self.check_done)
        self.show_history()
        self.render()
        if auto_check or not self.result or time.time() - self.state.get("checked", 0) > 6 * 3600:
            QTimer.singleShot(300, self.check)

    def extra_style(self) -> str:
        p, a = self.p, self.accent
        return f"""
        QLabel#HeroTitle {{ font-size: 22px; font-weight: 700; }}
        QLabel#Version {{ font-family: "JetBrains Mono", monospace; font-size: 12px; color: {p['muted']}; }}
        QLabel#SecBadge {{ background: {cw.mix(p['card'], '#E5675B', 0.2)}; color: #E5675B; border-radius: 9px;
                           padding: 2px 9px; font-size: 11px; font-weight: 700; }}
        QPushButton#GroupHead {{ background: transparent; border: none; padding: 4px 0; text-align: left;
                                 font-size: 15px; font-weight: 650; }}
        QPushButton#GroupHead:hover {{ color: {a}; }}
        QPlainTextEdit#Log {{ background: #14161C; color: #C9D1D9; border: 1px solid {p['border']}; border-radius: 10px;
                              font-family: "JetBrains Mono", monospace; font-size: 12px; padding: 8px; }}
        QProgressBar {{ background: {p['card2']}; border: none; border-radius: 4px; }}
        QProgressBar::chunk {{ background: {a}; border-radius: 4px; }}
        QFrame#Warn {{ background: {cw.mix(p['card'], '#F2A65A', 0.14)}; border: 1px solid {cw.mix(p['border'], '#F2A65A', 0.5)};
                       border-radius: 14px; }}
        """

    # ------------------------------------------------------------ estado na tela

    def items(self) -> list[dict]:
        if not self.result:
            return []
        return self.result.get("official", []) + self.result.get("aur", [])

    def render(self) -> None:
        cw_clear(self.notices)
        cw_clear(self.groups)
        items = self.items()
        reboot = self.state.get("reiniciar") == boot_id() and boot_id()
        self.primary.setVisible(False)
        self.helpbtn.hide()
        if reboot:
            self.icon.set("power", "#F2A65A")
            self.headline.setText("Reinicie para concluir a atualização")
            self.detail.setText("O kernel ou partes centrais do sistema foram atualizados. Salve o que estiver aberto e reinicie.")
            self.primary.setText("Reiniciar agora")
            self.primary.setVisible(True)
        elif items:
            sec = sum(1 for i in items if i["name"] in self.result.get("security", {}))
            size = fmt_size(self.result.get("size", 0))
            self.icon.set("update", self.accent)
            self.headline.setText(plural(len(items), "atualização disponível", "atualizações disponíveis"))
            parts = [f"Última verificação: {when_text(self.result.get('checked', 0))}"]
            if size:
                parts.append(f"download de {size}")
            if sec:
                parts.append(plural(sec, "correção de segurança", "correções de segurança"))
            self.detail.setText(" · ".join(parts) + ".")
            self.primary.setText("Baixar e instalar")
            self.primary.setVisible(True)
        elif self.result:
            self.icon.set("check", "#2FB67A")
            self.headline.setText("Você está atualizado")
            self.detail.setText(f"Última verificação: {when_text(self.result.get('checked', 0))}.")
        else:
            self.icon.set("update", self.accent)
            self.headline.setText("Atualizações do Clone OS")
            self.detail.setText("Clique em Verificar atualizações para procurar versões novas.")
        for err in (self.result or {}).get("errors", []):
            self.add_notice("alert", "Atenção", err)
        for n in (self.result or {}).get("news", []):
            when = datetime.fromtimestamp(n["when"]).strftime("%d/%m/%Y")
            self.add_notice("news", f"Aviso do Arch Linux ({when})", n["title"] +
                            "\nOs avisos do Arch explicam mudanças que pedem atenção. Leia antes de atualizar.",
                            ("Ler o aviso", lambda link=n["link"]: cw.run(["xdg-open", link])),
                            ("Explicar com o Claude", lambda t=n["title"], link=n["link"]: self.ask_claude(
                                f"O Arch Linux publicou o aviso \"{t}\" ({link}). O que ele significa para o meu "
                                "Clone OS? Preciso fazer algo antes de atualizar?")))
        self.list_title.setText("ATUALIZAÇÕES DISPONÍVEIS" if items and not reboot else "")
        self.list_title.setVisible(bool(items) and not reboot)
        if items and not reboot:
            security = self.result.get("security", {})
            for key, title, hint in GROUPS:
                grp = [i for i in items if group_of(i["name"]) == key]
                if grp:
                    self.groups.addWidget(Group(title, hint, grp, security, self.accent,
                                                open_=key in ("sistema", "apps") and len(grp) <= 12))

    def add_notice(self, icon: str, title: str, text: str, *actions) -> None:
        frame, box = cw.card("Warn")
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(cw.IconTile(icon, lambda: "#F2A65A", 36), 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.addWidget(cw.label(title, "H2"))
        col.addWidget(cw.label(text, "Muted", wrap=True))
        if actions:
            arow = QHBoxLayout()
            for text_, slot in actions:
                arow.addWidget(cw.button(text_, None, slot))
            arow.addStretch(1)
            col.addLayout(arow)
        row.addLayout(col, 1)
        box.addLayout(row)
        self.notices.addWidget(frame)

    def show_history(self) -> None:
        cw_clear(self.hist)
        entries = history()
        if not entries:
            self.hist.addWidget(cw.label("Nenhuma atualização registrada ainda.", "Muted"))
            return
        for e in entries:
            g = Group(f"{e['day']}", plural(len(e["items"]), "pacote atualizado", "pacotes atualizados"),
                      [{"name": s.split()[0], "old": s.split()[1], "new": s.split()[3], "aur": False}
                       for s in e["items"]], {}, self.accent, open_=False)
            self.hist.addWidget(g)

    def toggle_log(self) -> None:
        self.log.setVisible(not self.log.isVisible())
        self.log_toggle.setText(("Esconder" if self.log.isVisible() else "Mostrar") + " detalhes (saída do pacman)")

    def write_log(self, text: str) -> None:
        self.log.moveCursor(QTextCursor.End)
        self.log.insertPlainText(text)
        self.log.moveCursor(QTextCursor.End)

    # ------------------------------------------------------------ verificar

    def check(self) -> None:
        if self.running:
            return
        self.running = True
        self.secondary.setEnabled(False)
        self.primary.hide()
        self.icon.set("update", self.accent, spinning=True)
        self.headline.setText("Procurando atualizações…")
        self.detail.setText("Consultando o Arch Linux, o AUR (Brave e Claude) e o banco de falhas de segurança.")
        self.bar.setRange(0, 0)
        self.bar.show()
        self.checker.run()

    def check_done(self, result: dict) -> None:
        self.running = False
        self.bar.hide()
        self.secondary.setEnabled(True)
        self.result = result
        self.state.update({"checked": result["checked"], "count": len(self.items()), "result": result})
        cw.write_json(STATE, self.state)
        self.render()
        print(f"[clone-update] verificado: {len(self.items())} atualizações", flush=True)

    # ------------------------------------------------------------ instalar

    def primary_action(self) -> None:
        if self.primary.text() == "Reiniciar agora":
            self.reboot()
        elif self.primary.text() == "Tentar de novo":
            self.check()
        else:
            self.install()

    def install(self) -> None:
        warnings = [w for w in (battery_warning(), space_warning()) if w]
        if warnings:
            answer = QMessageBox.question(self, "Antes de atualizar", "\n\n".join(warnings) + "\n\nContinuar mesmo assim?")
            if answer != QMessageBox.Yes:
                return
        self.official = (self.result or {}).get("official", [])
        self.aur_queue = [i["name"] for i in (self.result or {}).get("aur", [])]
        self.aur_files, self.aur_failed, self.errors, self.upgraded = [], [], [], []
        self.total = len(self.official)
        self.counts = {"down": 0, "inst": 0}
        self.running = True
        self.secondary.setEnabled(False)
        self.primary.hide()
        self.helpbtn.hide()
        self.icon.set("update", self.accent, spinning=True)
        self.headline.setText("Instalando atualizações…")
        self.detail.setText("Não desligue o notebook. Você pode continuar usando os outros programas.")
        self.bar.setRange(0, 0)
        self.bar.show()
        self.step.show()
        self.log.clear()
        # Primeiro o Brave e o Claude (como usuário, sem senha); depois uma senha só para tudo.
        self.next_aur()

    def install_all(self) -> None:
        if self.official:
            args = ["sistema", *self.aur_files]
        elif self.aur_files:
            args = ["aur", *self.aur_files]
        else:
            self.finish(not self.aur_failed, "Não foi possível preparar o Brave e o Claude: " + "; ".join(self.aur_failed))
            return
        self.total = len(self.official) + len(self.aur_files)
        self.bar.setRange(0, 0)
        self.set_step("Esperando a sua senha…")
        self.start_helper(args, self.after_install)

    def set_step(self, text: str) -> None:
        self.step.setText(text)
        print(f"[clone-update] {text}", flush=True)

    def start_helper(self, args: list[str], on_done) -> None:
        # systemd-inhibit: o notebook não dorme (nem com a tampa fechada) enquanto o pacman trabalha.
        cmd = [*ELEVATE, HELPER, *args]
        if shutil.which("systemd-inhibit"):
            cmd = ["systemd-inhibit", "--what=sleep:shutdown:idle:handle-lid-switch", "--who=Clone Update",
                   "--why=Instalando atualizações", *cmd]
        self.run_proc(cmd, on_done, parse=True)

    def run_proc(self, cmd: list[str], on_done, parse: bool = False, cwd: str | None = None, env: dict | None = None) -> None:
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        if cwd:
            proc.setWorkingDirectory(cwd)
        if env:
            e = QProcessEnvironment.systemEnvironment()
            for k, v in env.items():
                e.insert(k, v)
            proc.setProcessEnvironment(e)
        self.proc = proc
        self.buf = ""
        self.fim = ""

        def read() -> None:
            self.buf += bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
            while "\n" in self.buf:
                line, self.buf = self.buf.split("\n", 1)
                self.on_line(line, parse)

        proc.readyReadStandardOutput.connect(read)
        proc.finished.connect(lambda code, _st: (read(), self.on_line(self.buf, parse) if self.buf else None,
                                                  on_done(code)))
        self.write_log(f"$ {' '.join(cmd)}\n")
        proc.start(cmd[0], cmd[1:])

    def on_line(self, line: str, parse: bool) -> None:
        self.write_log(line + "\n")
        if not parse:
            return
        line = line.strip()
        if line.startswith("@@ETAPA"):
            step = line.split(maxsplit=1)[1] if " " in line else ""
            self.phase = step
            self.set_step({
                "sincronizar": "Baixando a lista de versões do Arch Linux…",
                "chaves": "Atualizando as chaves de segurança do Arch…",
                "sistema": "Preparando os pacotes…",
                "aur-instalar": "Instalando o Brave e o Claude…",
            }.get(step, step))
        elif line.startswith("@@FIM"):
            self.fim = line
        elif line.endswith(" downloading..."):
            # Na sincronização, as linhas são as listas de versões (core, extra), não pacotes.
            if getattr(self, "phase", "") in ("sistema", "aur-instalar"):
                self.counts["down"] += 1
                self.progress("Baixando", self.counts["down"])
        elif line.startswith("checking package integrity"):
            self.set_step("Conferindo as assinaturas dos pacotes…")
        elif m := re.match(r"(upgrading|installing|reinstalling|removing|downgrading) (\S+)\.\.\.$", line):
            self.counts["inst"] += 1
            self.upgraded.append(m.group(2))
            self.progress("Instalando", self.counts["inst"], m.group(2))
        elif line.startswith(":: Running post-transaction hooks"):
            self.bar.setRange(0, 0)
            if any(n.startswith("linux") for n in self.upgraded):
                self.set_step("Finalizando: preparando o boot com o kernel novo e assinando…")
            else:
                self.set_step("Finalizando os ajustes do sistema…")
        elif line.startswith("error:"):
            self.errors.append(line)

    def progress(self, verb: str, n: int, name: str = "") -> None:
        total = max(self.total, n)
        self.bar.setRange(0, total)
        self.bar.setValue(n)
        label = FRIENDLY.get(name, name)
        self.set_step(f"{verb} {n} de {total}" + (f": {label}" if label else "") + "…")

    def after_install(self, code: int) -> None:
        if code in (126, 127) and not self.fim:
            self.finish(False, "A senha não foi confirmada, então nada foi instalado.")
            return
        if not self.fim.startswith("@@FIM ok"):
            reason = self.fim.split(maxsplit=2)[2] if self.fim.count(" ") >= 2 else ""
            self.finish(False, self.explain(reason))
            return
        self.finish(True)

    def explain(self, reason: str) -> str:
        if reason.startswith("ocupado"):
            return "Outro programa está instalando pacotes agora. Espere ele terminar e tente de novo."
        if reason.startswith("trava"):
            return ("O sistema de pacotes ficou travado por uma atualização interrompida. Feche outros instaladores e "
                    "peça ajuda ao Claude para remover a trava com segurança.")
        if reason.startswith("sincronizar"):
            return "Não foi possível baixar a lista de versões. Confira a internet e tente de novo."
        if reason.startswith(("aur", "arquivo", "nao-permitido")):
            return ("O sistema foi atualizado, mas o Brave e o Claude não puderam ser instalados agora. "
                    "Tente de novo mais tarde.")
        detail = self.errors[-1].removeprefix("error:").strip() if self.errors else ""
        return "A atualização não terminou" + (f": {detail}" if detail else ".") + \
            " Nada ficou pela metade: o pacman só troca os arquivos depois de baixar e conferir tudo."

    # Brave, Claude e Claude Code: receita do AUR conferida, compilada como usuário.
    def next_aur(self) -> None:
        if not self.aur_queue:
            self.install_all()
            return
        pkg = self.aur_queue.pop(0)
        self.bar.setRange(0, 0)
        self.set_step(f"Baixando a receita de {FRIENDLY.get(pkg, pkg)}…")
        d = AUR_DIR / pkg
        AUR_DIR.mkdir(parents=True, exist_ok=True)
        if (d / ".git").is_dir():
            cmd = ["sh", "-c", f"git -C '{d}' fetch -q origin && git -C '{d}' reset -q --hard origin/master"]
        else:
            cmd = ["git", "clone", "-q", f"https://aur.archlinux.org/{pkg}.git", str(d)]
        self.run_proc(cmd, lambda code: self.aur_fetched(pkg, code))

    def aur_fetched(self, pkg: str, code: int) -> None:
        d = AUR_DIR / pkg
        if code != 0:
            self.aur_failed.append(f"{FRIENDLY.get(pkg, pkg)}: não foi possível baixar a receita")
            self.next_aur()
            return
        ok, bad = srcinfo_ok(d / ".SRCINFO", OFFICIAL[pkg])
        if not ok:
            self.write_log(f"RECUSADO {pkg}: a receita aponta para fora do site oficial: {' '.join(bad)}\n")
            self.aur_failed.append(f"{FRIENDLY.get(pkg, pkg)}: a receita aponta para fora do site oficial e não foi instalada")
            self.next_aur()
            return
        self.set_step(f"Preparando {FRIENDLY.get(pkg, pkg)} (baixando do site oficial)…")
        out = d / "pacotes"
        for old in out.glob("*.pkg.tar.zst"):
            old.unlink(missing_ok=True)
        self.run_proc(["makepkg", "-f", "--noconfirm", "--cleanbuild", "--noprogressbar"],
                      lambda c: self.aur_built(pkg, c), cwd=str(d), env={"PKGDEST": str(out), "LC_ALL": "C"})

    def aur_built(self, pkg: str, code: int) -> None:
        out = AUR_DIR / pkg / "pacotes"
        files = sorted(out.glob(f"{pkg}-*.pkg.tar.zst"), key=lambda f: f.stat().st_mtime)
        if code != 0 or not files:
            self.aur_failed.append(f"{FRIENDLY.get(pkg, pkg)}: não foi possível preparar o pacote")
        else:
            self.aur_files.append(str(files[-1]))
        self.next_aur()

    def finish(self, ok: bool, message: str = "") -> None:
        print(f"[clone-update] fim: {'ok' if ok else 'erro'} {message}".rstrip(), flush=True)
        self.running = False
        self.proc = None
        self.bar.hide()
        self.step.hide()
        self.secondary.setEnabled(True)
        if not ok:
            self.icon.set("alert", "#E5675B")
            self.headline.setText("A atualização não foi concluída")
            self.detail.setText(message)
            self.primary.setText("Tentar de novo")
            self.primary.show()
            self.helpbtn.show()
            self.last_error = message + ("\n" + "\n".join(self.errors[-5:]) if self.errors else "")
            QApplication.alert(self)
            return
        if needs_reboot(self.upgraded) or kernel_replaced():
            self.state["reiniciar"] = boot_id()
        self.state["last_update"] = time.time()
        cw.write_json(STATE, self.state)
        self.result = {"official": [], "aur": [], "security": {}, "errors": [], "size": 0, "news": [],
                       "checked": time.time()}
        if self.aur_failed:
            self.result["errors"] = ["Algumas atualizações ficaram para depois: " + "; ".join(self.aur_failed) + "."]
        self.state.update({"checked": time.time(), "count": 0, "result": self.result})
        cw.write_json(STATE, self.state)
        self.render()
        if not self.state.get("reiniciar"):
            self.detail.setText(plural(len(self.upgraded), "pacote atualizado", "pacotes atualizados") + " agora há pouco. Tudo pronto.")
        self.show_history()
        QApplication.alert(self)

    def ask_claude(self, question: str | bool = False) -> None:
        if not isinstance(question, str):
            question = ("A atualização do Clone OS falhou com esta mensagem:\n\n" + getattr(self, "last_error", "") +
                        "\n\nO que aconteceu e como eu resolvo com segurança?")
        cw.run(["/usr/local/bin/terminal-claude", "--pergunta", question])

    def reboot(self) -> None:
        if QMessageBox.question(self, "Reiniciar", "Reiniciar o notebook agora? Salve o que estiver aberto.") != QMessageBox.Yes:
            return
        if shutil.which("qdbus6"):
            cw.run(["qdbus6", "org.kde.Shutdown", "/Shutdown", "logoutAndReboot"])
        else:
            cw.run(["systemctl", "reboot"])

    # ------------------------------------------------------------ opções

    def timer_enabled(self) -> bool:
        code, _ = sh(["systemctl", "--user", "is-enabled", "--quiet", "cloneos-atualizacoes.timer"], 10)
        return code == 0

    def set_timer(self, on: bool) -> None:
        sh(["systemctl", "--user", "enable" if on else "disable", "--now", "cloneos-atualizacoes.timer"], 20)

    def closeEvent(self, event) -> None:
        if self.proc and self.proc.state() != QProcess.NotRunning:
            QMessageBox.information(self, "Atualização em andamento",
                                    "Espere a atualização terminar antes de fechar. Interromper o pacman no meio "
                                    "pode deixar o sistema danificado.")
            event.ignore()
            return
        super().closeEvent(event)


def cw_clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.hide()
            w.deleteLater()


def main() -> int:
    parser = argparse.ArgumentParser(description="Clone Update: atualizações do Clone OS")
    parser.add_argument("--verificar", action="store_true", help="procura atualizações ao abrir")
    args = parser.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("Clone Update")
    app.setDesktopFileName("clone-atualizacoes")
    app.setFont(QFont("Inter", 10))
    win = Window(args.verificar)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
