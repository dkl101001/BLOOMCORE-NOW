# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Loopback demonstration server for BLOOMCORE RECEIPT."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

RELEASE_ROOT = pathlib.Path(__file__).resolve().parents[2]
VALIDATOR_ROOT = RELEASE_ROOT / "packages" / "evidence-validator"
sys.path.insert(0, str(VALIDATOR_ROOT))

from bloomcore_receipt import audit_text  # noqa: E402

MAX_REQUEST_BYTES = 1_000_000

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BLOOMCORE RECEIPT</title>
  <style>
    :root { color-scheme: dark; --ink:#f5f1e8; --muted:#b9b2a4; --red:#ff665e;
      --green:#81d39a; --gold:#efc56b; --panel:#17191d; --edge:#36383e; }
    * { box-sizing: border-box; }
    body { margin:0; font:16px/1.5 ui-sans-serif,system-ui,sans-serif;
      color:var(--ink); background:#0c0d0f; }
    main { width:min(980px,92vw); margin:4rem auto; }
    h1 { font-size:clamp(2rem,7vw,4.5rem); margin:0; letter-spacing:-.05em; }
    .tag { color:var(--gold); font-weight:700; margin:.5rem 0 2rem; }
    textarea { width:100%; min-height:260px; resize:vertical; padding:1rem;
      color:var(--ink); background:var(--panel); border:1px solid var(--edge);
      border-radius:12px; font:14px/1.55 ui-monospace,SFMono-Regular,monospace; }
    .actions { display:flex; gap:1rem; align-items:center; margin:1rem 0 2rem; flex-wrap:wrap; }
    button { border:0; border-radius:999px; padding:.8rem 1.3rem; font-weight:800;
      background:var(--gold); color:#15120c; cursor:pointer; }
    label { color:var(--muted); }
    .summary { display:grid; grid-template-columns:repeat(4,1fr); gap:.8rem; }
    .card { padding:1rem; background:var(--panel); border:1px solid var(--edge);
      border-radius:12px; }
    .card strong { display:block; font-size:1.7rem; }
    table { width:100%; border-collapse:collapse; margin-top:1rem; font-size:.9rem; }
    th,td { text-align:left; vertical-align:top; padding:.75rem; border-bottom:1px solid var(--edge); }
    .red_flag { color:var(--red); } .aligned { color:var(--green); }
    .unresolved,.weak_alignment { color:var(--gold); }
    .fine { color:var(--muted); font-size:.85rem; margin-top:2rem; }
    @media(max-width:650px){ .summary{grid-template-columns:repeat(2,1fr)}
      table{display:block;overflow-x:auto} }
  </style>
</head>
<body>
<main>
  <div class="fine">BLOOMCORE NOW · WEEK ONE</div>
  <h1>BLOOMCORE RECEIPT</h1>
  <p class="tag">Paste an AI answer. Get receipts—or red flags.</p>
  <textarea id="input" aria-label="Text to inspect"
    placeholder="Paste an AI answer or report containing URLs or DOI citations…"></textarea>
  <div class="actions">
    <button id="audit">Inspect evidence</button>
    <label><input id="online" type="checkbox"> Check public citation targets online</label>
  </div>
  <section id="output" hidden>
    <div id="summary" class="summary"></div>
    <table>
      <thead><tr><th>Verdict</th><th>Source</th><th>Alignment</th><th>Claim or note</th></tr></thead>
      <tbody id="findings"></tbody>
    </table>
    <p class="fine">Observational inspection only. Reachability and token overlap do not certify truth.</p>
  </section>
</main>
<script>
const esc = value => String(value ?? "").replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
document.getElementById("audit").onclick = async () => {
  const button = document.getElementById("audit");
  button.disabled = true; button.textContent = "Inspecting…";
  try {
    const response = await fetch("/api/audit", {method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({text:document.getElementById("input").value,
        online:document.getElementById("online").checked})});
    const receipt = await response.json();
    if (!response.ok) throw new Error(receipt.error || "Inspection failed");
    const s = receipt.summary;
    document.getElementById("summary").innerHTML =
      [["Claims",s.claims],["References",s.references],["Red flags",s.red_flags],
       ["Unresolved",s.unresolved]].map(([k,v]) =>
       `<div class="card"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join("");
    document.getElementById("findings").innerHTML = receipt.findings.map(f =>
      `<tr><td class="${esc(f.verdict)}">${esc(f.verdict)}</td>
       <td>${esc(f.reference || "—")}</td>
       <td>${f.alignment == null ? "—" : esc(f.alignment.toFixed(2))}</td>
       <td>${esc(f.claim || f.reason)}</td></tr>`).join("");
    document.getElementById("output").hidden = false;
  } catch (error) { alert(error.message); }
  finally { button.disabled = false; button.textContent = "Inspect evidence"; }
};
</script>
</body>
</html>
"""


class ReceiptHandler(BaseHTTPRequestHandler):
    server_version = "BLOOMCORE-RECEIPT/0.1"

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.send_header("x-content-type-options", "nosniff")
        self.send_header("content-security-policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'")
        self.send_header("referrer-policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, value: dict[str, Any]) -> None:
        self._send(
            status,
            (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            self._send(HTTPStatus.OK, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/health":
            self._json(HTTPStatus.OK, {"status": "ok", "service": "bloomcore-receipt"})
        elif self.path == "/source":
            self.send_response(HTTPStatus.FOUND)
            self.send_header("location", "https://github.com/")
            self.end_headers()
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/audit":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid content length"})
            return
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request size rejected"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            text = payload.get("text", "")
            online = payload.get("online", False)
            if not isinstance(text, str) or not isinstance(online, bool):
                raise ValueError("text must be a string and online must be a boolean")
            if len(text.encode("utf-8")) > MAX_REQUEST_BYTES:
                raise ValueError("text is too large")
            self._json(HTTPStatus.OK, audit_text(text, online=online))
        except (json.JSONDecodeError, ValueError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write(f"{self.address_string()} - {format % args}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("v0.1 demonstration server binds to loopback only")
    server = ThreadingHTTPServer((args.host, args.port), ReceiptHandler)
    print(f"BLOOMCORE RECEIPT listening at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

