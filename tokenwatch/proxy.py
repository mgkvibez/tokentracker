"""A pass-through proxy that records usage.

Point your client's base URL at it and keep working; every response's usage
block is appended to a JSONL log that `tokenwatch report` can read. No keys are
stored, nothing is inspected beyond the usage field, and requests are forwarded
byte for byte.

Limit worth knowing: streamed responses (text/event-stream) are forwarded but
not counted, because the usage block arrives in fragments. Use non-streaming
calls, or read your harness's own logs instead.
"""

from __future__ import annotations

import json
import pathlib
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Optional, Tuple

from .adapters import _usage_from
from .usage import Usage

HOP_BY_HOP = {"host", "content-length", "connection", "accept-encoding"}


def usage_from_body(body: bytes) -> Tuple[Optional[Usage], str]:
    """Pull (usage, model) out of a JSON response body."""
    try:
        data = json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        return None, ""
    if not isinstance(data, dict):
        return None, ""
    raw = data.get("usage")
    if not isinstance(raw, dict):
        return None, ""
    model = str(data.get("model") or "")
    usage = _usage_from(raw)
    return (usage if usage.total else None), model


def append_record(path: pathlib.Path, model: str, usage: Usage, label: str) -> None:
    """One JSONL line per proxied call, in the shape the generic adapter reads."""
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "session": path.parent.name if path.parent.name else "proxy",
        "model": model,
        "usage": {
            "input_tokens": usage.input,
            "output_tokens": usage.output,
            "cache_read_input_tokens": usage.cache_read,
            "cache_creation_input_tokens": usage.cache_write,
        },
        "skill": "",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def make_handler(upstream: str, log_path: pathlib.Path, verbose: bool = False):
    """Build a handler class bound to one upstream and one log file."""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:  # quieter than the default
            if verbose:
                super().log_message(fmt, *args)

        def _forward(self, method: str) -> None:
            length = int(self.headers.get("content-length") or 0)
            body = self.rfile.read(length) if length else None
            target = upstream.rstrip("/") + self.path
            headers: Dict[str, str] = {
                k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP
            }
            request = urllib.request.Request(target, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    payload = response.read()
                    status = response.status
                    resp_headers = response.getheaders()
            except urllib.error.HTTPError as exc:
                payload = exc.read()
                status = exc.code
                resp_headers = list(exc.headers.items())
            except urllib.error.URLError as exc:
                message = json.dumps({"error": f"upstream unreachable: {exc.reason}"}).encode()
                self.send_response(502)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(message)))
                self.end_headers()
                self.wfile.write(message)
                return

            if b"text/event-stream" not in payload[:64]:
                usage, model = usage_from_body(payload)
                if usage is not None:
                    append_record(log_path, model or "unknown", usage, self.path)

            self.send_response(status)
            for key, value in resp_headers:
                if key.lower() in HOP_BY_HOP or key.lower() == "transfer-encoding":
                    continue
                self.send_header(key, value)
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:
            self._forward("POST")

        def do_GET(self) -> None:
            self._forward("GET")

    return Handler


def serve(port: int, upstream: str, log_path: pathlib.Path, verbose: bool = False) -> None:
    """Run the proxy until interrupted."""
    handler = make_handler(upstream, log_path, verbose)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"tokenwatch proxy: http://127.0.0.1:{port} -> {upstream}")
    print(f"logging usage to {log_path}  (ctrl-c to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nproxy stopped")
    finally:
        server.server_close()
