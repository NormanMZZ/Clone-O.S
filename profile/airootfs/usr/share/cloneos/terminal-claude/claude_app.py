#!/usr/bin/env python3
"""Terminal Claude: o Claude Code numa janela no estilo do app oficial do Claude.

Cada mensagem roda o Claude Code sem terminal (claude -p, saída stream-json) na
pasta ~/Clone, retomando a mesma sessão (--resume). Assim continuam valendo a
conta Claude, as ferramentas, o CLAUDE.md e as permissões de
~/.claude/settings.json. Os pedidos de permissão chegam pelo servidor MCP
aprovar_mcp.py e aparecem aqui como cartões com Permitir e Negar.
"""
from __future__ import annotations

import json
import math
import os
import pwd
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPointF, QProcess, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QIcon, QKeySequence, QPainter, QPalette,
                           QPen, QPixmap, QShortcut)
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QInputDialog, QLabel, QListWidget,
                               QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
                               QSizePolicy, QToolButton, QVBoxLayout, QWidget, QWidgetAction)

HOME = Path.home()
WORKSPACE = HOME / "Clone"
SHARE = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "cloneos/terminal-claude/conversas"
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "cloneos/terminal-claude.json"
CLAUDE_BIN = os.environ.get("CLONE_CLAUDE_BIN") or shutil.which("claude") or ""

# Apelidos do Claude Code: sempre apontam para a versão mais nova de cada família.
MODELS = [
    ("opus", "Opus", "5.5", "Inteligente e equilibrado. Recomendado para o dia a dia."),
    ("sonnet", "Sonnet", "5.5", "Rápido e capaz, gasta menos da sua cota."),
    ("haiku", "Haiku", "5.5", "O mais rápido, para perguntas simples."),
    ("fable", "Fable", "5.1", "O mais capaz, para tarefas difíceis. Gasta bem mais da cota."),
]
EFFORTS = [
    ("low", "Baixo", "Respostas rápidas e diretas."),
    ("medium", "Médio", "Pensa um pouco antes de responder."),
    ("high", "Alto", "Pensa com cuidado. Recomendado."),
    ("xhigh", "Muito alto", "Para tarefas longas e trabalhosas."),
    ("max", "Máximo", "Pensa o máximo possível. Mais lento."),
]
DEFAULT_WINDOW = 1_000_000
SMALL_WINDOWS = {"claude-haiku-4-5": 200_000}

PTBR = (
    "Responda sempre em português do Brasil, com linguagem simples, mesmo quando o usuário, os arquivos "
    "ou as ferramentas usarem outro idioma. Seu raciocínio (o pensamento antes da resposta) também deve "
    "ser escrito inteiramente em português do Brasil. Você está no Terminal Claude do Clone OS, uma "
    "janela gráfica: use Markdown simples (parágrafos curtos, listas e blocos de código)."
)

SUGGESTIONS = [
    "Organize minha pasta Downloads por tipo",
    "Crie uma planilha de gastos do mês",
    "Como deixo o notebook mais rápido?",
    "Como o Clone OS protege meus arquivos?",
]

THEMES = {
    "dark": {
        "bg": "#262624", "side": "#1F1E1D", "card": "#30302E", "hover": "#2E2D2B", "border": "#3E3D39",
        "text": "#ECEAE3", "text2": "#C9C6BD", "muted": "#9C998F", "accent": "#D97757", "accent2": "#E58C6E",
        "user": "#3A3935", "code": "#1C1B1A", "error": "#F2A39B", "errorbg": "#3A2421", "ok": "#7DC48A",
        "warn": "#E8B04B", "bad": "#E5675B", "track": "#45443F", "disabled": "#55534D",
    },
    "light": {
        "bg": "#FAF9F5", "side": "#F0EEE6", "card": "#FFFFFF", "hover": "#ECEAE1", "border": "#E2DFD5",
        "text": "#2B2A27", "text2": "#4A4842", "muted": "#77736A", "accent": "#C6613F", "accent2": "#B4552F",
        "user": "#EFEDE5", "code": "#F3F1EA", "error": "#9E2B22", "errorbg": "#FBE7E3", "ok": "#2F8A47",
        "warn": "#B07A12", "bad": "#C2392D", "track": "#E2DFD5", "disabled": "#C9C5BA",
    },
}

TOOL_NAMES = {
    "Bash": "Comando", "Read": "Ler arquivo", "Edit": "Editar arquivo", "MultiEdit": "Editar arquivo",
    "Write": "Criar arquivo", "Glob": "Procurar arquivos", "Grep": "Procurar no conteúdo",
    "WebFetch": "Abrir página", "WebSearch": "Pesquisar na web", "web_search": "Pesquisar na web",
    "Task": "Subtarefa", "Agent": "Subtarefa", "TodoWrite": "Lista de tarefas", "NotebookEdit": "Editar notebook",
    "Skill": "Habilidade", "AskUserQuestion": "Pergunta", "ExitPlanMode": "Plano pronto",
}


# ---------------------------------------------------------------- utilidades

def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def short_path(text: str) -> str:
    return str(text).replace(str(HOME), "~")


def model_label(model_id: str) -> str:
    m = re.match(r"claude-([a-z]+)-(\d+)(?:-(\d{1,2}))?(?:\D|$)", model_id or "")
    if not m:
        return model_id or ""
    version = m.group(2) + (f".{m.group(3)}" if m.group(3) else "")
    return f"{m.group(1).capitalize()} {version}"


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        value = f"{n / 1_000_000:.1f}".replace(".", ",").removesuffix(",0")
        return value + (" milhão" if n < 2_000_000 else " milhões")
    if n >= 1000:
        return f"{round(n / 1000)} mil"
    return str(n)


def tool_summary(name: str, data: dict) -> tuple[str, str]:
    data = data or {}
    label = TOOL_NAMES.get(name, name)
    if name.startswith("mcp__"):
        label = "Ferramenta " + name.split("__")[-1]
    detail = ""
    if name == "Bash":
        detail = data.get("command", "")
    elif name in ("Read", "Edit", "MultiEdit", "Write", "NotebookEdit"):
        detail = short_path(data.get("file_path") or data.get("notebook_path") or "")
    elif name in ("Glob", "Grep"):
        detail = data.get("pattern", "")
    elif name == "WebFetch":
        detail = data.get("url", "")
    elif name in ("WebSearch", "web_search"):
        detail = data.get("query", "")
    elif name in ("Task", "Agent"):
        detail = data.get("description", "")
    elif name == "TodoWrite":
        detail = f"{len(data.get('todos', []))} itens"
    return label, " ".join(str(detail).split())


def tool_result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
            elif isinstance(c, dict) and c.get("type") == "image":
                parts.append("[imagem]")
        return "\n".join(parts)
    return json.dumps(content, ensure_ascii=False) if content else ""


def friendly_error(text: str) -> str:
    low = (text or "").lower()
    if "not logged in" in low or "authentication" in low or "/login" in low:
        return "Você ainda não entrou na sua conta Claude. Use o botão Entrar com o Claude."
    if "usage limit" in low or "rate limit" in low or "rate_limit" in low or "limit reached" in low:
        return "Você atingiu o limite de uso do seu plano Claude. Tente de novo mais tarde ou troque para um modelo mais leve."
    if "overloaded" in low or "529" in low:
        return "Os servidores do Claude estão sobrecarregados agora. Espere um pouco e mande de novo."
    if "no conversation found" in low:
        return "A conversa anterior não foi encontrada no Claude Code. Mande a mensagem de novo para começar do zero."
    if "connection" in low or "network" in low or "enotfound" in low or "fetch failed" in low:
        return "Sem conexão com o Claude. Confira o Wi-Fi e tente de novo."
    return "Algo deu errado: " + (text.strip() or "o Claude Code fechou sem responder.")


def first_name() -> str:
    try:
        gecos = pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0].strip()
    except KeyError:
        gecos = ""
    return (gecos or os.environ.get("USER", "")).split(" ")[0]


def greeting() -> str:
    hour = datetime.now().hour
    word = "Bom dia" if 5 <= hour < 12 else "Boa tarde" if 12 <= hour < 18 else "Boa noite"
    name = first_name()
    return f"{word}, {name}" if name else word


def effort_icon(level: int, on: str, off: str, size: int = 16) -> QIcon:
    pix = QPixmap(size * 2, size * 2)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(2, 2)
    bar_w, gap = 2.2, 1.1
    for i in range(5):
        h = 3 + i * 2.4
        x = 1.5 + i * (bar_w + gap)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(on if i <= level else off))
        p.drawRoundedRect(QRectF(x, size - 2 - h, bar_w, h), 1, 1)
    p.end()
    return QIcon(pix)


# ---------------------------------------------------------------- widgets básicos

class Spark(QWidget):
    """O asterisco do Claude, desenhado (não depende de fonte)."""

    def __init__(self, color: str, size: int = 22, parent: QWidget | None = None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(size, size)
        self.spin = 0.0

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        r = self.width() / 2 - 1.5
        pen = QPen(self.color, max(1.6, self.width() / 9), Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        for i in range(8):
            a = math.radians(i * 45 + self.spin)
            inner = r * 0.18
            p.drawLine(QPointF(c.x() + inner * math.cos(a), c.y() + inner * math.sin(a)),
                       QPointF(c.x() + r * math.cos(a), c.y() + r * math.sin(a)))


class ContextRing(QWidget):
    """Roda que mostra quanto do contexto da conversa já foi usado."""

    def __init__(self, colors: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.colors = colors
        self.used = 0
        self.window = DEFAULT_WINDOW
        self.setFixedSize(22, 22)

    def ratio(self) -> float:
        return min(1.0, self.used / self.window) if self.window else 0.0

    def set_usage(self, used: int, window: int) -> None:
        self.used, self.window = max(0, used), max(1, window)
        pct = self.ratio() * 100
        self.setToolTip(
            f"Contexto desta conversa: {fmt_tokens(self.used)} de {fmt_tokens(self.window)} tokens ({pct:.0f}%).\n"
            "Quando enche, o Claude resume a conversa sozinho para continuar.")
        self.update()

    def color(self) -> str:
        r = self.ratio()
        return self.colors["ok"] if r < 0.6 else self.colors["warn"] if r < 0.85 else self.colors["bad"]

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(3, 3, self.width() - 6, self.height() - 6)
        p.setPen(QPen(QColor(self.colors["track"]), 3.2, Qt.SolidLine, Qt.FlatCap))
        p.drawEllipse(rect)
        span = self.ratio()
        if span > 0:
            p.setPen(QPen(QColor(self.color()), 3.2, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(rect, 90 * 16, -max(8, int(span * 360 * 16)))


class MenuRow(QWidget):
    """Linha de menu com título e descrição, no estilo do app do Claude."""
    clicked = Signal()

    def __init__(self, title: str, desc: str, checked: bool, icon: QIcon | None = None):
        super().__init__()
        self.setObjectName("MenuRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 7, 12, 7)
        row.setSpacing(10)
        if icon is not None:
            ic = QLabel()
            ic.setPixmap(icon.pixmap(16, 16))
            row.addWidget(ic, 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(1)
        t = QLabel(title)
        t.setObjectName("MenuTitle")
        d = QLabel(desc)
        d.setObjectName("Muted")
        col.addWidget(t)
        col.addWidget(d)
        row.addLayout(col, 1)
        mark = QLabel("✓" if checked else "")
        mark.setObjectName("Check")
        mark.setFixedWidth(14)
        row.addWidget(mark, 0, Qt.AlignVCenter)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


def md_label(text: str = "", name: str = "Md") -> QLabel:
    lab = QLabel()
    lab.setObjectName(name)
    lab.setTextFormat(Qt.MarkdownText)
    lab.setWordWrap(True)
    lab.setOpenExternalLinks(True)
    lab.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
    lab.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
    lab.setText(text)
    return lab


def plain_label(text: str, name: str, selectable: bool = True) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName(name)
    lab.setTextFormat(Qt.PlainText)
    lab.setWordWrap(True)
    if selectable:
        lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lab


# ---------------------------------------------------------------- partes da conversa

class Part:
    kind = ""
    final = False


class TextPart(QWidget, Part):
    kind = "text"

    def __init__(self, item: dict):
        super().__init__()
        self.item = item
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.label = md_label(item.get("text", ""))
        lay.addWidget(self.label)
        self.dirty = False

    def append(self, delta: str) -> None:
        self.item["text"] = self.item.get("text", "") + delta
        self.dirty = True

    def set_text(self, text: str) -> None:
        self.item["text"] = text
        self.final = True
        self.flush(force=True)

    def flush(self, force: bool = False) -> None:
        if self.dirty or force:
            self.label.setText(self.item.get("text", ""))
            self.dirty = False


class Collapsible(QFrame):
    def __init__(self, name: str, title: str):
        super().__init__()
        self.setObjectName(name)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.header = QPushButton()
        self.header.setObjectName("PartHeader")
        self.header.setFlat(True)
        self.header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.clicked.connect(self.toggle)
        lay.addWidget(self.header)
        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(12, 0, 12, 10)
        self.body_lay.setSpacing(6)
        self.body.setVisible(False)
        lay.addWidget(self.body)
        self.title = title
        self.set_title(title)

    def set_title(self, title: str) -> None:
        self.title = title
        self.header.setText(("▾  " if self.body.isVisible() else "▸  ") + title)

    def toggle(self) -> None:
        self.body.setVisible(not self.body.isVisible())
        self.set_title(self.title)


class ThinkingPart(Collapsible, Part):
    kind = "thinking"

    def __init__(self, item: dict):
        super().__init__("Thinking", "Pensando…")
        self.item = item
        self.text = plain_label(item.get("text", ""), "ThinkingText")
        self.body_lay.addWidget(self.text)
        self.started = time.monotonic()
        self.dirty = False
        if "seconds" in item:
            self.final = True
            self.update_title()

    def append(self, delta: str) -> None:
        self.item["text"] = self.item.get("text", "") + delta
        self.dirty = True

    def stop(self) -> None:
        if "seconds" not in self.item:
            self.item["seconds"] = max(1, round(time.monotonic() - self.started))
        self.update_title()

    def set_text(self, text: str) -> None:
        if text:
            self.item["text"] = text
        self.final = True
        self.stop()
        self.flush(force=True)

    def update_title(self) -> None:
        secs = self.item.get("seconds")
        base = f"Raciocínio · {secs} s" if secs else "Raciocínio"
        if not self.item.get("text"):
            base = f"Pensou por {secs} s" if secs else "Pensou"
            self.header.setEnabled(False)
        else:
            self.header.setEnabled(True)
        self.set_title(base)

    def flush(self, force: bool = False) -> None:
        if self.dirty or force:
            self.text.setText(self.item.get("text", ""))
            self.dirty = False
            if self.item.get("text") and "seconds" not in self.item:
                self.set_title("Pensando…")
                self.header.setEnabled(True)


class ToolPart(Collapsible, Part):
    kind = "tool_use"

    def __init__(self, item: dict, colors: dict):
        super().__init__("Tool", "")
        self.item = item
        self.colors = colors
        self.detail = plain_label("", "Mono")
        self.result = plain_label("", "Mono")
        self.result.setVisible(False)
        self.body_lay.addWidget(self.detail)
        self.body_lay.addWidget(self.result)
        self.refresh()
        if "result" in item:
            self.final = True

    def set_input(self, name: str, data: dict, tool_id: str) -> None:
        self.item.update({"name": name, "input": data, "id": tool_id})
        self.final = True
        self.refresh()

    def set_result(self, text: str, error: bool) -> None:
        self.item["result"] = text[:6000] + ("\n…" if len(text) > 6000 else "")
        self.item["error"] = bool(error)
        self.refresh()

    def refresh(self) -> None:
        name = self.item.get("name", "")
        label, detail = tool_summary(name, self.item.get("input", {}))
        if "result" in self.item:
            mark = "✕" if self.item.get("error") else "✓"
        else:
            mark = "…"
        short = detail if len(detail) < 70 else detail[:67] + "…"
        self.set_title(f"{mark}  {label}" + (f"  ·  {short}" if short else ""))
        data = self.item.get("input", {})
        if name == "Bash":
            body = data.get("command", "")
        else:
            body = json.dumps(data, ensure_ascii=False, indent=2) if data else ""
        self.detail.setText(short_path(body))
        if "result" in self.item:
            self.result.setVisible(True)
            self.result.setText(self.item["result"] or "(sem saída)")


class ApprovalCard(QFrame):
    answered = Signal(str, bool)

    def __init__(self, request: dict):
        super().__init__()
        self.setObjectName("Approval")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)
        name = request.get("tool_name", "")
        data = request.get("input", {}) or {}
        label, detail = tool_summary(name, data)
        title = QLabel(f"O Claude quer usar: {label}")
        title.setObjectName("ApprovalTitle")
        lay.addWidget(title)
        if name == "Bash":
            body = data.get("command", "")
            if data.get("description"):
                lay.addWidget(plain_label(data["description"], "Muted"))
        elif name in ("Edit", "MultiEdit"):
            body = short_path(data.get("file_path", ""))
            new = data.get("new_string", "")
            if new:
                body += "\n\n" + (new if len(new) < 600 else new[:600] + "\n…")
        elif name == "Write":
            content = data.get("content", "")
            body = short_path(data.get("file_path", "")) + "\n\n" + (content if len(content) < 600 else content[:600] + "\n…")
        else:
            body = detail or json.dumps(data, ensure_ascii=False, indent=2)
        if body:
            lay.addWidget(plain_label(short_path(body), "Mono"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.buttons = []
        for text, obj, behavior, always in (("Permitir", "Primary", "allow", False),
                                            ("Permitir sempre nesta conversa", "Secondary", "allow", True),
                                            ("Negar", "Secondary", "deny", False)):
            b = QPushButton(text)
            b.setObjectName(obj)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, bh=behavior, al=always: self.answer(bh, al))
            row.addWidget(b)
            self.buttons.append(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.status = plain_label("", "Muted", selectable=False)
        self.status.setVisible(False)
        lay.addWidget(self.status)
        self.done = False

    def answer(self, behavior: str, always: bool) -> None:
        if self.done:
            return
        self.close_card("Permitido." if behavior == "allow" else "Negado.")
        self.answered.emit(behavior, always)

    def close_card(self, text: str) -> None:
        self.done = True
        for b in self.buttons:
            b.setVisible(False)
        self.status.setText(text)
        self.status.setVisible(True)


class AssistantBlock(QWidget):
    def __init__(self, colors: dict):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(12)
        self.spark = Spark(colors["accent"], 22)
        row.addWidget(self.spark, 0, Qt.AlignTop)
        self.col = QVBoxLayout()
        self.col.setSpacing(8)
        row.addLayout(self.col, 1)

    def add(self, w: QWidget) -> None:
        self.col.addWidget(w)


class UserBubble(QWidget):
    def __init__(self, text: str):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(60, 4, 0, 4)
        row.addStretch(1)
        lab = plain_label(text, "UserBubble")
        lab.setMaximumWidth(560)
        lab.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)
        row.addWidget(lab)


# ---------------------------------------------------------------- área da conversa

class ChatView(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setObjectName("ChatView")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QWidget()
        host.setObjectName("ChatHost")
        outer = QHBoxLayout(host)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch(1)
        self.column = QWidget()
        self.column.setMaximumWidth(780)
        self.column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lay = QVBoxLayout(self.column)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(14)
        self.lay.addStretch(1)
        outer.addWidget(self.column, 100)
        outer.addStretch(1)
        self.setWidget(host)
        self.stick = True
        bar = self.verticalScrollBar()
        bar.valueChanged.connect(lambda v: setattr(self, "stick", v >= bar.maximum() - 40))
        bar.rangeChanged.connect(lambda _a, b: self.stick and bar.setValue(b))

    def add(self, w: QWidget) -> None:
        self.lay.insertWidget(self.lay.count() - 1, w)

    def clear(self) -> None:
        while self.lay.count() > 1:
            item = self.lay.takeAt(0)
            if item.widget():
                # Fora do layout o widget continuaria desenhado até ser apagado.
                item.widget().hide()
                item.widget().deleteLater()
        self.stick = True

    def to_bottom(self) -> None:
        self.stick = True
        bar = self.verticalScrollBar()
        QTimer.singleShot(30, lambda: bar.setValue(bar.maximum()))


class Input(QPlainTextEdit):
    send = Signal()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers() & Qt.ShiftModifier:
            self.send.emit()
            return
        super().keyPressEvent(event)


# ---------------------------------------------------------------- janela

class MainWindow(QWidget):
    def __init__(self, colors: dict):
        super().__init__()
        self.c = colors
        self.setObjectName("Root")
        self.setWindowTitle("Terminal Claude")
        self.setWindowIcon(QIcon.fromTheme("terminal-claude"))
        self.resize(1120, 760)
        self.setMinimumSize(760, 520)

        cfg = read_json(CONFIG)
        self.model = cfg.get("model", "opus")
        self.effort = cfg.get("effort", "high")
        self.versions = cfg.get("versions", {})
        self.chat: dict | None = None
        self.proc: QProcess | None = None
        self.turn: dict | None = None
        self.stderr = ""
        self.stopping = False
        self.logged_in: bool | None = None
        self.pending_cards: list[tuple[ApprovalCard, object]] = []

        self.server = QLocalServer(self)
        runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
        self.sock_path = os.path.join(runtime, f"cloneos-claude-{os.getpid()}.sock")
        QLocalServer.removeServer(self.sock_path)
        self.server.listen(self.sock_path)
        self.server.newConnection.connect(self.on_connection)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.build_sidebar())
        main = QVBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        main.addWidget(self.build_header())
        self.view = ChatView()
        main.addWidget(self.view, 1)
        main.addWidget(self.build_composer())
        root.addLayout(main, 1)

        self.flush_timer = QTimer(self)
        self.flush_timer.timeout.connect(self.flush_parts)
        self.flush_timer.start(70)
        self.spin_timer = QTimer(self)
        self.spin_timer.timeout.connect(self.spin)
        self.auth_timer = QTimer(self)
        self.auth_timer.timeout.connect(self.check_auth)

        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.new_chat)
        QShortcut(QKeySequence("Escape"), self, activated=self.stop)

        self.load_chat_list()
        self.new_chat()
        self.check_auth()

    # ------------------------------------------------------------ montagem

    def build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(260)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(12, 14, 12, 12)
        lay.setSpacing(10)
        brand = QHBoxLayout()
        brand.setSpacing(9)
        brand.addWidget(Spark(self.c["accent"], 20))
        name = QLabel("Terminal Claude")
        name.setObjectName("Brand")
        brand.addWidget(name)
        brand.addStretch(1)
        lay.addLayout(brand)
        new = QPushButton("+   Nova conversa")
        new.setObjectName("NewChat")
        new.setCursor(Qt.PointingHandCursor)
        new.setToolTip("Nova conversa (Ctrl+N)")
        new.clicked.connect(self.new_chat)
        lay.addWidget(new)
        sec = QLabel("CONVERSAS")
        sec.setObjectName("Section")
        lay.addWidget(sec)
        self.chat_list = QListWidget()
        self.chat_list.setObjectName("Chats")
        self.chat_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_list.setTextElideMode(Qt.ElideRight)
        self.chat_list.setWordWrap(False)
        self.chat_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chat_list.customContextMenuRequested.connect(self.chat_menu)
        self.chat_list.itemClicked.connect(lambda it: self.open_chat(it.data(Qt.UserRole)))
        lay.addWidget(self.chat_list, 1)
        foot = QHBoxLayout()
        self.account = QLabel("Verificando a conta…")
        self.account.setObjectName("Muted")
        foot.addWidget(self.account, 1)
        more = QToolButton()
        more.setObjectName("Pick")
        more.setText("•••")
        more.setPopupMode(QToolButton.InstantPopup)
        more.setCursor(Qt.PointingHandCursor)
        menu = QMenu(more)
        menu.addAction("Abrir a pasta de trabalho (~/Clone)", lambda: subprocess.Popen(["xdg-open", str(WORKSPACE)]))
        menu.addAction("Abrir no modo texto (terminal)", lambda: subprocess.Popen(["/usr/local/bin/terminal-claude", "--texto"]))
        menu.addSeparator()
        menu.addAction("Entrar com outra conta", self.login)
        more.setMenu(menu)
        foot.addWidget(more)
        lay.addLayout(foot)
        return side

    def build_header(self) -> QWidget:
        head = QFrame()
        head.setObjectName("Header")
        row = QHBoxLayout(head)
        row.setContentsMargins(24, 10, 18, 10)
        self.title = QLabel("Nova conversa")
        self.title.setObjectName("ChatTitle")
        row.addWidget(self.title, 1)
        folder = QLabel("Pasta de trabalho: ~/Clone")
        folder.setObjectName("Muted")
        folder.setToolTip("O Claude trabalha nesta pasta e nas pastas que você liberou no Clone Welcome.")
        row.addWidget(folder)
        return head

    def build_composer(self) -> QWidget:
        wrap = QWidget()
        outer = QHBoxLayout(wrap)
        outer.setContentsMargins(24, 6, 24, 18)
        outer.addStretch(1)
        box = QFrame()
        box.setObjectName("Composer")
        box.setMaximumWidth(800)
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(14, 10, 10, 10)
        lay.setSpacing(6)
        self.input = Input()
        self.input.setObjectName("Input")
        self.input.setPlaceholderText("Pergunte ou peça algo ao Claude…")
        self.input.setTabChangesFocus(True)
        self.input.send.connect(self.send)
        self.input.textChanged.connect(self.grow_input)
        self.input.setFixedHeight(46)
        lay.addWidget(self.input)
        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.model_btn = QToolButton()
        self.model_btn.setObjectName("Pick")
        self.model_btn.setCursor(Qt.PointingHandCursor)
        self.model_btn.setPopupMode(QToolButton.InstantPopup)
        self.model_btn.setToolTip("Escolher o modelo do Claude")
        bar.addWidget(self.model_btn)
        self.effort_btn = QToolButton()
        self.effort_btn.setObjectName("Pick")
        self.effort_btn.setCursor(Qt.PointingHandCursor)
        self.effort_btn.setPopupMode(QToolButton.InstantPopup)
        self.effort_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.effort_btn.setToolTip("Grau de esforço: quanto o Claude pensa antes de responder")
        bar.addWidget(self.effort_btn)
        bar.addStretch(1)
        self.ring = ContextRing(self.c)
        bar.addWidget(self.ring)
        self.ring_label = QLabel("0%")
        self.ring_label.setObjectName("Muted")
        self.ring_label.setToolTip("Quanto do contexto desta conversa já foi usado")
        self.ring_label.setMinimumWidth(self.ring_label.fontMetrics().horizontalAdvance("100%") + 4)
        bar.addWidget(self.ring_label)
        bar.addSpacing(6)
        self.send_btn = QPushButton("↑")
        self.send_btn.setObjectName("Send")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setToolTip("Enviar (Enter). Shift+Enter quebra a linha.")
        self.send_btn.clicked.connect(self.send_or_stop)
        bar.addWidget(self.send_btn)
        lay.addLayout(bar)
        outer.addWidget(box, 100)
        outer.addStretch(1)
        self.build_pickers()
        return wrap

    def build_pickers(self) -> None:
        for btn in (self.model_btn, self.effort_btn):
            if btn.menu():
                btn.menu().deleteLater()
        menu = QMenu(self.model_btn)
        self.add_head(menu, "Modelo")
        for alias, name, version, desc in MODELS:
            label = model_label(self.versions.get(alias, "")) or f"{name} {version}"
            self.add_row(menu, label, desc, alias == self.model, None, lambda a=alias: self.set_model(a))
        self.model_btn.setMenu(menu)
        cur = next(m for m in MODELS if m[0] == self.model) if any(m[0] == self.model for m in MODELS) else MODELS[0]
        self.model_btn.setText((model_label(self.versions.get(cur[0], "")) or f"{cur[1]} {cur[2]}") + "  ▾")

        menu = QMenu(self.effort_btn)
        self.add_head(menu, "Grau de esforço")
        for i, (key, name, desc) in enumerate(EFFORTS):
            self.add_row(menu, name, desc, key == self.effort, effort_icon(i, self.c["accent"], self.c["track"]),
                         lambda k=key: self.set_effort(k))
        self.effort_btn.setMenu(menu)
        idx = next((i for i, e in enumerate(EFFORTS) if e[0] == self.effort), 2)
        self.effort_btn.setIcon(effort_icon(idx, self.c["accent"], self.c["track"]))
        self.effort_btn.setText(f"{EFFORTS[idx][1]}  ▾")

    def add_head(self, menu: QMenu, text: str) -> None:
        head = QWidgetAction(menu)
        lab = QLabel(text)
        lab.setObjectName("MenuHead")
        head.setDefaultWidget(lab)
        menu.addAction(head)

    def add_row(self, menu: QMenu, title: str, desc: str, checked: bool, icon, slot) -> None:
        act = QWidgetAction(menu)
        row = MenuRow(title, desc, checked, icon)
        # Adiado: o slot recria os menus, e um menu não pode ser trocado dentro do próprio clique.
        row.clicked.connect(lambda: (menu.close(), QTimer.singleShot(0, slot)))
        act.setDefaultWidget(row)
        menu.addAction(act)

    def grow_input(self) -> None:
        doc_h = self.input.document().size().height() * self.input.fontMetrics().lineSpacing()
        self.input.setFixedHeight(int(min(180, max(46, doc_h + 14))))

    # ------------------------------------------------------------ configurações

    def save_config(self) -> None:
        write_json(CONFIG, {"model": self.model, "effort": self.effort, "versions": self.versions})

    def set_model(self, alias: str) -> None:
        if alias == self.model:
            return
        self.model = alias
        self.save_config()
        self.build_pickers()
        if self.chat and self.chat.get("items"):
            label = self.model_btn.text().replace("  ▾", "")
            self.add_notice(f"Modelo trocado para {label}. Vale a partir da próxima mensagem.")

    def set_effort(self, key: str) -> None:
        if key == self.effort:
            return
        self.effort = key
        self.save_config()
        self.build_pickers()

    # ------------------------------------------------------------ conta

    def check_auth(self) -> None:
        if not CLAUDE_BIN:
            self.logged_in = False
            self.account.setText("Claude Code não instalado")
            return
        if getattr(self, "auth_proc", None):
            return
        # Em segundo plano: no HD, a primeira execução do claude leva alguns segundos.
        proc = QProcess(self)
        proc.finished.connect(lambda *_: self.auth_done(proc))
        self.auth_proc = proc
        proc.start(CLAUDE_BIN, ["auth", "status"])

    def auth_done(self, proc: QProcess) -> None:
        self.auth_proc = None
        try:
            status = json.loads(bytes(proc.readAllStandardOutput()).decode("utf-8", "replace") or "{}")
        except (ValueError, RuntimeError):
            return
        proc.deleteLater()
        was = self.logged_in
        self.logged_in = bool(status.get("loggedIn"))
        self.account.setText("●  Conectado" if self.logged_in else "○  Não conectado")
        self.account.setStyleSheet(f"color: {self.c['ok'] if self.logged_in else self.c['muted']};")
        if self.logged_in:
            self.auth_timer.stop()
        if was != self.logged_in and self.chat is not None and not self.chat.get("items"):
            self.show_empty_state()

    def login(self) -> None:
        cmd = [CLAUDE_BIN or "claude", "auth", "login", "--claudeai"]
        for term in (["konsole", "-p", "tabtitle=Entrar no Claude", "-e"], ["alacritty", "-e"]):
            if shutil.which(term[0]):
                subprocess.Popen(term + cmd, cwd=str(WORKSPACE))
                break
        self.auth_timer.start(3000)

    # ------------------------------------------------------------ conversas

    def chat_path(self, chat_id: str) -> Path:
        return DATA_DIR / f"{chat_id}.json"

    def load_chat_list(self) -> None:
        self.chat_list.clear()
        chats = []
        if DATA_DIR.is_dir():
            for f in DATA_DIR.glob("*.json"):
                data = read_json(f)
                if data.get("id"):
                    chats.append(data)
        chats.sort(key=lambda d: d.get("updated", 0), reverse=True)
        for data in chats:
            it = QListWidgetItem(data.get("title") or "Conversa")
            it.setData(Qt.UserRole, data["id"])
            it.setToolTip(datetime.fromtimestamp(data.get("updated", 0)).strftime("%d/%m/%Y %H:%M"))
            self.chat_list.addItem(it)
            if self.chat and data["id"] == self.chat.get("id"):
                it.setSelected(True)

    def save_chat(self) -> None:
        if self.chat and self.chat.get("items"):
            self.chat["updated"] = time.time()
            write_json(self.chat_path(self.chat["id"]), self.chat)

    def new_chat(self) -> None:
        if self.proc:
            return
        self.chat = {"id": uuid.uuid4().hex, "session_id": "", "title": "", "items": [],
                     "context": {"used": 0, "window": 0}, "allow": [], "created": time.time()}
        self.chat_list.clearSelection()
        self.title.setText("Nova conversa")
        self.update_ring()
        self.show_empty_state()
        self.input.setFocus()

    def open_chat(self, chat_id: str) -> None:
        if self.proc:
            return
        data = read_json(self.chat_path(chat_id))
        if not data:
            return
        self.chat = data
        self.title.setText(data.get("title") or "Conversa")
        self.view.clear()
        block = None
        for item in data.get("items", []):
            kind = item.get("kind")
            if kind == "user":
                block = None
                self.view.add(UserBubble(item.get("text", "")))
                continue
            if kind == "notice":
                block = None
                self.view.add(self.notice_label(item))
                continue
            if block is None:
                block = AssistantBlock(self.c)
                self.view.add(block)
            if kind == "text":
                block.add(TextPart(item))
            elif kind == "thinking":
                block.add(ThinkingPart(item))
            elif kind == "tool":
                block.add(ToolPart(item, self.c))
        self.update_ring()
        self.view.to_bottom()
        self.input.setFocus()

    def chat_menu(self, pos) -> None:
        it = self.chat_list.itemAt(pos)
        if not it:
            return
        chat_id = it.data(Qt.UserRole)
        menu = QMenu(self)
        menu.addAction("Renomear", lambda: self.rename_chat(chat_id))
        menu.addAction("Apagar", lambda: self.delete_chat(chat_id))
        menu.exec(self.chat_list.mapToGlobal(pos))

    def rename_chat(self, chat_id: str) -> None:
        data = read_json(self.chat_path(chat_id))
        name, ok = QInputDialog.getText(self, "Renomear conversa", "Nome:", text=data.get("title", ""))
        if ok and name.strip():
            data["title"] = name.strip()
            write_json(self.chat_path(chat_id), data)
            if self.chat and self.chat["id"] == chat_id:
                self.chat["title"] = data["title"]
                self.title.setText(data["title"])
            self.load_chat_list()

    def delete_chat(self, chat_id: str) -> None:
        if QMessageBox.question(self, "Apagar conversa", "Apagar esta conversa da lista?") != QMessageBox.Yes:
            return
        self.chat_path(chat_id).unlink(missing_ok=True)
        if self.chat and self.chat["id"] == chat_id:
            self.new_chat()
        self.load_chat_list()

    # ------------------------------------------------------------ estado vazio

    def show_empty_state(self) -> None:
        self.view.clear()
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 60, 0, 0)
        lay.setSpacing(16)
        top = QHBoxLayout()
        top.addStretch(1)
        top.addWidget(Spark(self.c["accent"], 34))
        hi = QLabel(greeting())
        hi.setObjectName("Greeting")
        top.addSpacing(10)
        top.addWidget(hi)
        top.addStretch(1)
        lay.addLayout(top)
        if not CLAUDE_BIN:
            lay.addWidget(self.center(plain_label(
                "O Claude Code não está instalado. Instale com: sudo pacman -S claude-code", "Error")))
        elif self.logged_in is False:
            msg = plain_label("Entre com a sua conta Claude para conversar. É preciso um plano Pro, Max, Team "
                              "ou Enterprise. O navegador abre na página de login: entre e clique em Autorizar.",
                              "Muted")
            msg.setAlignment(Qt.AlignCenter)
            lay.addWidget(msg)
            b = QPushButton("Entrar com o Claude")
            b.setObjectName("Primary")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(self.login)
            lay.addWidget(self.center(b))
        else:
            sub = QLabel("Como posso ajudar? Eu trabalho na pasta ~/Clone e peço sua permissão antes de mudar algo.")
            sub.setObjectName("Muted")
            sub.setAlignment(Qt.AlignCenter)
            sub.setWordWrap(True)
            lay.addWidget(sub)
            grid = QVBoxLayout()
            grid.setSpacing(8)
            for i in range(0, len(SUGGESTIONS), 2):
                row = QHBoxLayout()
                row.setSpacing(8)
                for text in SUGGESTIONS[i:i + 2]:
                    b = QPushButton(text)
                    b.setObjectName("Suggestion")
                    b.setCursor(Qt.PointingHandCursor)
                    b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    b.clicked.connect(lambda _=False, t=text: (self.input.setPlainText(t), self.send()))
                    row.addWidget(b)
                grid.addLayout(row)
            lay.addLayout(grid)
        self.view.add(box)

    def center(self, w: QWidget) -> QWidget:
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(w)
        row.addStretch(1)
        return holder

    # ------------------------------------------------------------ itens

    def notice_label(self, item: dict) -> QLabel:
        lab = plain_label(item.get("text", ""), "Error" if item.get("error") else "Notice")
        if not item.get("error"):
            lab.setAlignment(Qt.AlignCenter)
        return lab

    def add_notice(self, text: str, error: bool = False) -> None:
        if not self.chat:
            return
        item = {"kind": "notice", "text": text, "error": error}
        self.chat["items"].append(item)
        self.view.add(self.notice_label(item))
        self.view.to_bottom()

    def update_ring(self) -> None:
        ctx = (self.chat or {}).get("context", {})
        window = ctx.get("window") or DEFAULT_WINDOW
        self.ring.set_usage(ctx.get("used", 0), window)
        self.ring_label.setText(f"{self.ring.ratio() * 100:.0f}%")

    # ------------------------------------------------------------ envio

    def send_or_stop(self) -> None:
        if self.proc:
            self.stop()
        else:
            self.send()

    def send(self) -> None:
        text = self.input.toPlainText().strip()
        if not text or self.proc or not self.chat:
            return
        if not CLAUDE_BIN:
            return
        if not self.chat["items"]:
            self.view.clear()
            self.chat["title"] = " ".join(text.split())[:48]
            self.title.setText(self.chat["title"])
        self.input.clear()
        self.chat["items"].append({"kind": "user", "text": text})
        self.view.add(UserBubble(text))
        block = AssistantBlock(self.c)
        self.view.add(block)
        self.view.to_bottom()
        self.turn = {"block": block, "msg": "", "stream": {}, "parts": {}, "tools": {}, "done": False}
        self.stderr = ""
        self.stopping = False

        mcp = {"mcpServers": {"cloneos": {"command": sys.executable,
                                          "args": [str(SHARE / "aprovar_mcp.py")],
                                          "env": {"CLONE_CLAUDE_SOCK": self.sock_path}}}}
        args = ["-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
                "--model", self.model, "--effort", self.effort, "--append-system-prompt", PTBR,
                "--mcp-config", json.dumps(mcp), "--permission-prompt-tool", "mcp__cloneos__aprovar"]
        if self.chat.get("session_id"):
            args += ["--resume", self.chat["session_id"]]
        WORKSPACE.mkdir(parents=True, exist_ok=True)
        proc = QProcess(self)
        proc.setWorkingDirectory(str(WORKSPACE))
        proc.readyReadStandardOutput.connect(self.on_stdout)
        proc.readyReadStandardError.connect(lambda: self.collect_stderr(proc))
        proc.finished.connect(self.on_finished)
        self.buffer = b""
        self.proc = proc
        proc.start(CLAUDE_BIN, args)
        proc.write(text.encode("utf-8"))
        proc.closeWriteChannel()
        self.set_running(True)

    def set_running(self, running: bool) -> None:
        self.send_btn.setText("■" if running else "↑")
        self.send_btn.setToolTip("Parar a resposta (Esc)" if running else "Enviar (Enter). Shift+Enter quebra a linha.")
        self.input.setPlaceholderText("O Claude está respondendo…" if running else "Pergunte ou peça algo ao Claude…")
        self.input.viewport().update()  # o Qt não redesenha o texto de fundo sozinho com o foco na caixa
        if running:
            self.spin_timer.start(60)
        else:
            self.spin_timer.stop()
            if self.turn:
                self.turn["block"].spark.spin = 0
                self.turn["block"].spark.update()

    def spin(self) -> None:
        if self.turn:
            sp = self.turn["block"].spark
            sp.spin = (sp.spin + 6) % 360
            sp.update()

    def stop(self) -> None:
        if not self.proc:
            return
        self.stopping = True
        self.proc.terminate()
        proc = self.proc
        QTimer.singleShot(3000, lambda: proc.state() != QProcess.NotRunning and proc.kill())

    def collect_stderr(self, proc: QProcess) -> None:
        self.stderr = (self.stderr + bytes(proc.readAllStandardError()).decode("utf-8", "replace"))[-4000:]

    def on_stdout(self) -> None:
        if not self.proc:
            return
        self.buffer += bytes(self.proc.readAllStandardOutput())
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                self.handle(json.loads(line))
            except ValueError:
                continue

    # ------------------------------------------------------------ eventos do Claude Code

    def handle(self, obj: dict) -> None:
        kind = obj.get("type")
        if kind == "system":
            sub = obj.get("subtype")
            if sub == "init":
                if obj.get("session_id"):
                    self.chat["session_id"] = obj["session_id"]
                model = obj.get("model", "")
                if model and model_label(model) != model:
                    self.versions[self.model] = model
                    self.save_config()
                    self.build_pickers()
            elif sub == "compact_boundary":
                self.add_notice("A conversa ficou longa e foi resumida para liberar espaço no contexto.")
            return
        if obj.get("parent_tool_use_id"):
            return
        if kind == "stream_event":
            self.on_stream(obj.get("event", {}))
        elif kind == "assistant":
            self.on_assistant(obj)
        elif kind == "user":
            content = obj.get("message", {}).get("content", [])
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        part = self.turn["tools"].get(b.get("tool_use_id")) if self.turn else None
                        if part:
                            part.set_result(tool_result_text(b.get("content")), b.get("is_error", False))
        elif kind == "result":
            self.on_result(obj)

    def new_part(self, kind: str):
        if not self.turn:
            return None
        if kind == "text":
            item = {"kind": "text", "text": ""}
            part = TextPart(item)
        elif kind in ("thinking", "redacted_thinking"):
            item = {"kind": "thinking", "text": ""}
            part = ThinkingPart(item)
        elif kind in ("tool_use", "server_tool_use"):
            item = {"kind": "tool", "name": "", "input": {}}
            part = ToolPart(item, self.c)
        else:
            return None
        self.chat["items"].append(item)
        self.turn["block"].add(part)
        return part

    def on_stream(self, ev: dict) -> None:
        t = ev.get("type")
        turn = self.turn
        if not turn:
            return
        if t == "message_start":
            turn["msg"] = ev.get("message", {}).get("id", "")
            turn["parts"].setdefault(turn["msg"], [])
        elif t == "content_block_start":
            block = ev.get("content_block", {})
            part = self.new_part(block.get("type", ""))
            if part is not None:
                if block.get("type") in ("tool_use", "server_tool_use"):
                    part.item["name"] = block.get("name", "")
                    part.refresh()
                turn["stream"][(turn["msg"], ev.get("index"))] = part
                turn["parts"].setdefault(turn["msg"], []).append(part)
        elif t == "content_block_delta":
            part = turn["stream"].get((turn["msg"], ev.get("index")))
            delta = ev.get("delta", {})
            if part is None:
                return
            if delta.get("type") == "text_delta":
                part.append(delta.get("text", ""))
            elif delta.get("type") == "thinking_delta":
                part.append(delta.get("thinking", ""))
        elif t == "content_block_stop":
            part = turn["stream"].get((turn["msg"], ev.get("index")))
            if isinstance(part, ThinkingPart):
                part.stop()

    def on_assistant(self, obj: dict) -> None:
        msg = obj.get("message", {})
        if obj.get("error") == "authentication_failed":
            self.logged_in = False
            self.check_auth()
            return
        if msg.get("model") == "<synthetic>":
            return
        turn = self.turn
        if not turn:
            return
        mid = msg.get("id", "")
        parts = turn["parts"].setdefault(mid, [])
        for b in msg.get("content", []):
            kind = b.get("type", "")
            want = {"redacted_thinking": "thinking", "server_tool_use": "tool_use"}.get(kind, kind)
            part = next((p for p in parts if p.kind == want and not p.final), None)
            if part is None:
                part = self.new_part(kind)
                if part is None:
                    continue
                parts.append(part)
            if want == "text":
                part.set_text(b.get("text", ""))
            elif want == "thinking":
                part.set_text(b.get("thinking", ""))
            elif want == "tool_use":
                part.set_input(b.get("name", ""), b.get("input", {}), b.get("id", ""))
                turn["tools"][b.get("id", "")] = part
        usage = msg.get("usage") or {}
        used = sum(int(usage.get(k) or 0) for k in
                   ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"))
        if used:
            ctx = self.chat.setdefault("context", {})
            ctx["used"] = used
            if not ctx.get("window"):
                ctx["window"] = SMALL_WINDOWS.get(msg.get("model", ""), DEFAULT_WINDOW)
            self.update_ring()

    def on_result(self, obj: dict) -> None:
        if not self.turn:
            return
        self.turn["done"] = True
        if obj.get("session_id"):
            self.chat["session_id"] = obj["session_id"]
        windows = [v.get("contextWindow") for v in (obj.get("modelUsage") or {}).values()
                   if isinstance(v, dict) and v.get("contextWindow")]
        if windows:
            self.chat.setdefault("context", {})["window"] = max(windows)
            self.update_ring()
        if obj.get("is_error"):
            text = obj.get("result") or "; ".join(obj.get("errors", []) or [])
            if "not logged in" in (text or "").lower():
                self.logged_in = False
                self.check_auth()
            if "no conversation found" in (text or "").lower():
                self.chat["session_id"] = ""
            self.add_notice(friendly_error(text), error=True)
            if self.logged_in is False:
                b = QPushButton("Entrar com o Claude")
                b.setObjectName("Primary")
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(self.login)
                self.view.add(self.center(b))
        elif obj.get("subtype") == "error_max_turns":
            self.add_notice("O Claude parou porque a tarefa ficou longa demais. Peça para ele continuar.")

    def on_finished(self, _code: int, _status) -> None:
        self.on_stdout()
        for card, sock in self.pending_cards:
            if not card.done:
                card.close_card("A resposta terminou antes da sua escolha.")
        self.pending_cards.clear()
        if self.turn and not self.turn["done"]:
            if self.stopping:
                self.add_notice("Resposta interrompida.")
            else:
                tail = self.stderr.strip().splitlines()[-1:] if self.stderr.strip() else []
                self.add_notice(friendly_error(tail[0] if tail else ""), error=True)
        self.flush_parts()
        if self.turn:
            for parts in self.turn["parts"].values():
                for p in parts:
                    if isinstance(p, ThinkingPart):
                        p.stop()
            block = self.turn["block"]
            if block.col.count() == 0:
                block.hide()
                block.deleteLater()
        self.proc = None
        self.set_running(False)
        self.turn = None
        self.save_chat()
        self.load_chat_list()
        self.input.setFocus()

    def flush_parts(self) -> None:
        if not self.turn:
            return
        for parts in self.turn["parts"].values():
            for p in parts:
                if hasattr(p, "flush"):
                    p.flush()

    # ------------------------------------------------------------ permissões

    def on_connection(self) -> None:
        sock = self.server.nextPendingConnection()
        if sock is None:
            return
        sock.setProperty("buf", b"")

        def ready() -> None:
            buf = sock.property("buf") + bytes(sock.readAll())
            sock.setProperty("buf", buf)
            if b"\n" in buf:
                try:
                    req = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
                except ValueError:
                    req = {}
                self.on_approval(sock, req)

        sock.readyRead.connect(ready)

    def reply(self, sock, behavior: str, message: str = "") -> None:
        data = {"behavior": behavior}
        if message:
            data["message"] = message
        sock.write((json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8"))
        sock.flush()
        QTimer.singleShot(500, lambda: sock.disconnectFromServer())

    def on_approval(self, sock, req: dict) -> None:
        name = req.get("tool_name", "")
        data = req.get("input", {}) or {}
        key = f"Bash:{data.get('command', '')}" if name == "Bash" else name
        if self.chat and key in self.chat.get("allow", []):
            self.reply(sock, "allow")
            return
        if not self.turn:
            self.reply(sock, "deny", "Nenhuma conversa ativa.")
            return
        card = ApprovalCard(req)
        self.turn["block"].add(card)
        self.pending_cards.append((card, sock))
        self.view.to_bottom()
        QApplication.alert(self)
        label, detail = tool_summary(name, data)

        def answered(behavior: str, always: bool) -> None:
            if always and self.chat is not None:
                self.chat.setdefault("allow", []).append(key)
            self.reply(sock, behavior, "" if behavior == "allow" else "O usuário negou esta ação.")
            verb = "Permitido" if behavior == "allow" else "Negado"
            self.chat["items"].append({"kind": "notice", "text": f"{verb}: {label}" + (f" · {detail[:80]}" if detail else "")})

        card.answered.connect(answered)

    def closeEvent(self, event) -> None:
        for proc in (self.proc, getattr(self, "auth_proc", None)):
            if proc:
                try:
                    proc.finished.disconnect()
                except (RuntimeError, TypeError):
                    pass
                proc.kill()
                proc.waitForFinished(2000)
        self.proc = self.auth_proc = None
        self.save_chat()
        self.server.close()
        super().closeEvent(event)


# ---------------------------------------------------------------- aparência

def pick_font(*families: str) -> str:
    available = set(QFontDatabase.families())
    return next((f for f in families if f in available), families[-1])


def stylesheet(c: dict, sans: str, serif: str, mono: str) -> str:
    return f"""
    QWidget#Root {{ background: {c['bg']}; }}
    QWidget {{ color: {c['text']}; font-family: '{sans}'; font-size: 10.5pt; }}
    QFrame#Sidebar {{ background: {c['side']}; border-right: 1px solid {c['border']}; }}
    QLabel#Brand {{ font-family: '{serif}'; font-size: 13.5pt; font-weight: 600; }}
    QPushButton#NewChat {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 10px;
        padding: 9px 12px; text-align: left; font-weight: 600; }}
    QPushButton#NewChat:hover {{ border-color: {c['accent']}; }}
    QListWidget#Chats {{ background: transparent; border: none; outline: 0; }}
    QListWidget#Chats::item {{ padding: 8px 10px; border-radius: 8px; color: {c['text2']}; }}
    QListWidget#Chats::item:hover {{ background: {c['hover']}; }}
    QListWidget#Chats::item:selected {{ background: {c['card']}; color: {c['text']}; }}
    QLabel#Section {{ color: {c['muted']}; font-size: 8.5pt; font-weight: 600; letter-spacing: 1px; padding-top: 6px; }}
    QLabel#Muted {{ color: {c['muted']}; }}
    QFrame#Header {{ background: {c['bg']}; border-bottom: 1px solid {c['border']}; }}
    QLabel#ChatTitle {{ font-weight: 600; font-size: 11pt; }}
    QScrollArea#ChatView, QWidget#ChatHost {{ background: {c['bg']}; border: none; }}
    QLabel#Greeting {{ font-family: '{serif}'; font-size: 24pt; color: {c['text']}; }}
    QPushButton#Suggestion {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 12px;
        padding: 11px 14px; text-align: left; color: {c['text2']}; }}
    QPushButton#Suggestion:hover {{ border-color: {c['accent']}; color: {c['text']}; }}
    QLabel#UserBubble {{ background: {c['user']}; border-radius: 14px; padding: 10px 14px; font-size: 11pt; }}
    QLabel#Md {{ font-family: '{serif}'; font-size: 11.5pt; color: {c['text']}; }}
    QFrame#Thinking, QFrame#Tool {{ background: transparent; border: 1px solid {c['border']}; border-radius: 10px; }}
    QPushButton#PartHeader {{ border: none; background: transparent; color: {c['muted']}; padding: 7px 12px;
        text-align: left; font-size: 9.5pt; }}
    QPushButton#PartHeader:hover {{ color: {c['text']}; }}
    QPushButton#PartHeader:disabled {{ color: {c['muted']}; }}
    QLabel#ThinkingText {{ color: {c['muted']}; font-style: italic; font-size: 10pt; }}
    QLabel#Mono {{ font-family: '{mono}'; font-size: 9pt; background: {c['code']}; border-radius: 8px;
        padding: 8px 10px; color: {c['text2']}; }}
    QFrame#Approval {{ background: {c['card']}; border: 1px solid {c['accent']}; border-radius: 12px; }}
    QLabel#ApprovalTitle {{ font-weight: 600; }}
    QPushButton#Primary {{ background: {c['accent']}; color: #FFFFFF; border: none; border-radius: 9px;
        padding: 8px 16px; font-weight: 600; }}
    QPushButton#Primary:hover {{ background: {c['accent2']}; }}
    QPushButton#Secondary {{ background: transparent; border: 1px solid {c['border']}; border-radius: 9px; padding: 8px 14px; }}
    QPushButton#Secondary:hover {{ background: {c['hover']}; }}
    QLabel#Notice {{ color: {c['muted']}; font-size: 9pt; }}
    QLabel#Error {{ color: {c['error']}; background: {c['errorbg']}; border-radius: 10px; padding: 10px 12px; }}
    QFrame#Composer {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 18px; }}
    QPlainTextEdit#Input {{ background: transparent; border: none; font-size: 11pt; selection-background-color: {c['accent']}; }}
    QToolButton#Pick {{ background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 5px 9px;
        color: {c['text2']}; font-size: 9.5pt; }}
    QToolButton#Pick:hover {{ background: {c['hover']}; border-color: {c['border']}; }}
    QToolButton#Pick::menu-indicator {{ image: none; width: 0; }}
    QPushButton#Send {{ background: {c['accent']}; border: none; border-radius: 16px; min-width: 32px; max-width: 32px;
        min-height: 32px; max-height: 32px; color: #FFFFFF; font-size: 13pt; font-weight: 700; }}
    QPushButton#Send:hover {{ background: {c['accent2']}; }}
    QMenu {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 12px; padding: 6px; }}
    QMenu::item {{ padding: 8px 18px 8px 12px; border-radius: 7px; }}
    QMenu::item:selected {{ background: {c['hover']}; }}
    QWidget#MenuRow {{ border-radius: 8px; min-width: 280px; }}
    QWidget#MenuRow:hover {{ background: {c['hover']}; }}
    QLabel#MenuTitle {{ font-weight: 600; }}
    QLabel#MenuHead {{ color: {c['muted']}; font-size: 8.5pt; font-weight: 600; padding: 4px 10px; }}
    QLabel#Check {{ color: {c['accent']}; font-weight: 700; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 4px; min-height: 30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QToolTip {{ background: {c['card']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 6px; }}
    """


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Terminal Claude")
    app.setDesktopFileName("terminal-claude")
    dark = app.palette().color(QPalette.Window).lightness() < 128
    if os.environ.get("CLONE_CLAUDE_TEMA") in ("dark", "light"):
        dark = os.environ["CLONE_CLAUDE_TEMA"] == "dark"
    colors = THEMES["dark" if dark else "light"]
    pal = app.palette()
    pal.setColor(QPalette.Link, QColor(colors["accent"]))
    pal.setColor(QPalette.LinkVisited, QColor(colors["accent2"]))
    pal.setColor(QPalette.Highlight, QColor(colors["accent"]))
    app.setPalette(pal)
    sans = pick_font("Inter", "Noto Sans", "Sans Serif")
    serif = pick_font("Noto Serif", "DejaVu Serif", "Serif")
    mono = pick_font("JetBrains Mono", "Noto Sans Mono", "Monospace")
    app.setFont(QFont(sans, 10))
    app.setStyleSheet(stylesheet(colors, sans, serif, mono))
    win = MainWindow(colors)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
