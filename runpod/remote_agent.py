"""Minimal authenticated control channel for non-root Isaac Sim containers.

RunPod terminates TLS at its HTTPS proxy. Never expose this server directly to
the public internet or run it without a long random JEPA_AGENT_TOKEN.
"""

from __future__ import annotations

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ["JEPA_AGENT_TOKEN"]


class Handler(BaseHTTPRequestHandler):
    def _authorized(self):
        return self.headers.get("Authorization") == f"Bearer {TOKEN}"

    def _json(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._authorized():
            return self._json(401, {"error": "unauthorized"})
        self._json(200, {"status": "ok", "uid": os.getuid()})

    def do_POST(self):
        if not self._authorized():
            return self._json(401, {"error": "unauthorized"})
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        command = request.get("command")
        if not isinstance(command, list) or not all(isinstance(v, str) for v in command):
            return self._json(400, {"error": "command must be a string array"})
        try:
            result = subprocess.run(
                command, cwd=request.get("cwd", "/workspace"), text=True,
                capture_output=True, timeout=min(int(request.get("timeout", 300)), 1800),
            )
            self._json(200, {
                "returncode": result.returncode,
                "stdout": result.stdout[-20000:], "stderr": result.stderr[-20000:],
            })
        except subprocess.TimeoutExpired as error:
            self._json(408, {"error": "timeout", "stdout": error.stdout, "stderr": error.stderr})

    def log_message(self, *_):
        pass


ThreadingHTTPServer(("0.0.0.0", 8888), Handler).serve_forever()
