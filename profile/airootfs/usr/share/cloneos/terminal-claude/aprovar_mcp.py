#!/usr/bin/env python3
"""Pedidos de permissão do Claude Code para a janela do Terminal Claude.

O Claude Code roda sem terminal (modo -p) e, quando precisa de autorização para
editar um arquivo ou rodar um comando, chama a ferramenta "aprovar" deste
servidor MCP (stdio, JSON-RPC por linha). O pedido segue pelo socket da janela
(variável CLONE_CLAUDE_SOCK), que mostra os botões Permitir/Negar e devolve a
resposta. Sem a janela, o pedido é negado.
"""
from __future__ import annotations

import json
import os
import socket
import sys

TOOL = {
    "name": "aprovar",
    "description": "Pede ao usuário, na janela do Terminal Claude, permissão para usar uma ferramenta.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string"},
            "input": {"type": "object"},
            "tool_use_id": {"type": "string"},
        },
        "required": ["tool_name", "input"],
    },
}


def send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def ask_window(request: dict) -> dict:
    path = os.environ.get("CLONE_CLAUDE_SOCK", "")
    denied = {"behavior": "deny", "message": "Não foi possível pedir a confirmação do usuário."}
    if not path:
        return denied
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(path)
            sock.sendall((json.dumps(request, ensure_ascii=False) + "\n").encode())
            data = b""
            while not data.endswith(b"\n"):
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
        answer = json.loads(data.decode() or "{}")
    except (OSError, ValueError):
        return denied
    if answer.get("behavior") == "allow":
        return {"behavior": "allow", "updatedInput": request.get("input", {})}
    return {"behavior": "deny", "message": answer.get("message") or "O usuário negou esta ação."}


def handle(msg: dict) -> None:
    method = msg.get("method", "")
    mid = msg.get("id")
    if mid is None:
        return
    if method == "initialize":
        version = msg.get("params", {}).get("protocolVersion", "2025-06-18")
        send({"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": version,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "cloneos", "version": "0.4"},
        }})
    elif method == "tools/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [TOOL]}})
    elif method == "tools/call":
        args = msg.get("params", {}).get("arguments", {}) or {}
        answer = ask_window({
            "tool_name": args.get("tool_name", ""),
            "input": args.get("input", {}) or {},
            "tool_use_id": args.get("tool_use_id", ""),
        })
        send({"jsonrpc": "2.0", "id": mid, "result": {
            "content": [{"type": "text", "text": json.dumps(answer, ensure_ascii=False)}],
        }})
    elif method == "ping":
        send({"jsonrpc": "2.0", "id": mid, "result": {}})
    else:
        send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"método desconhecido: {method}"}})


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            handle(json.loads(line))
        except ValueError:
            continue
    return 0


if __name__ == "__main__":
    sys.exit(main())
