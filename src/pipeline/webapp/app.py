"""Minimal stdlib web app for grading one pseudocode answer at a time.

No framework: http.server + hand-rendered HTML. The app shows a selected
Cambridge pseudocode question with its mark-scheme marking points, accepts a
student answer, parses it with the Rust parser via the AST adapter, grades it
through the OpenRouter client (dry-run without an API key), and displays every
intermediate artifact — AST JSON, parser diagnostics, per-point decisions, and
raw grading JSON — so failures stay visible.
"""

from __future__ import annotations

import html
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..grading.ast_adapter import find_parser_binary, parse_answer
from ..grading.openrouter_client import OpenRouterConfig, grade_answer

RECORD_PATH_PATTERN = re.compile(r"^/record/(\d+)$")
GRADE_PATH_PATTERN = re.compile(r"^/record/(\d+)/grade$")
SCREENSHOT_PATH_PATTERN = re.compile(r"^/screenshot/(\d+)/(selected|context)$")


class RecordStore:
    """Loads canonical pseudocode-question-record/v1 records and indexes by id."""

    def __init__(self, records_path: Path) -> None:
        self.records_path = records_path
        with records_path.open() as handle:
            payload = json.load(handle)
        self.summary: Dict[str, Any] = payload.get("summary") or {}
        self.records: List[Dict[str, Any]] = payload.get("records") or []
        self.by_id: Dict[int, Dict[str, Any]] = {
            int(record["id"]): record for record in self.records if "id" in record
        }

    def first_id(self) -> Optional[int]:
        return min(self.by_id) if self.by_id else None


PAGE_STYLE = """
:root { --border: #d0d4dc; --muted: #5b6472; --accent: #14508c; --bg: #f5f6f8;
        --ok: #1a7f37; --bad: #b42318; --warn: #a15c07; }
* { box-sizing: border-box; }
body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0;
       background: var(--bg); color: #1c2330; line-height: 1.5; }
header { background: #fff; border-bottom: 1px solid var(--border); padding: 0.7rem 1.2rem;
         display: flex; align-items: baseline; gap: 1rem; flex-wrap: wrap; }
header h1 { font-size: 1.05rem; margin: 0; }
header a { color: var(--accent); text-decoration: none; }
main { max-width: 68rem; margin: 1.2rem auto; padding: 0 1.2rem; }
.card { background: #fff; border: 1px solid var(--border); border-radius: 8px;
        padding: 1rem 1.2rem; margin-bottom: 1rem; }
.card h2 { font-size: 0.95rem; margin: 0 0 0.6rem; color: var(--muted);
           text-transform: uppercase; letter-spacing: 0.04em; }
pre { background: #f2f4f7; border: 1px solid var(--border); border-radius: 6px;
      padding: 0.7rem; overflow-x: auto; font-size: 0.85rem; white-space: pre-wrap; }
.question-text { white-space: pre-wrap; font-size: 0.95rem; }
.mp { border: 1px solid var(--border); border-left: 4px solid var(--accent);
      border-radius: 6px; padding: 0.5rem 0.8rem; margin: 0.4rem 0; }
.mp .meta { color: var(--muted); font-size: 0.8rem; }
.badge { display: inline-block; border-radius: 999px; padding: 0.05rem 0.6rem;
         font-size: 0.78rem; border: 1px solid var(--border); margin-left: 0.4rem; }
.badge.ok { color: var(--ok); border-color: var(--ok); }
.badge.bad { color: var(--bad); border-color: var(--bad); }
.badge.warn { color: var(--warn); border-color: var(--warn); }
textarea { width: 100%; min-height: 14rem; font-family: ui-monospace, Menlo, Consolas, monospace;
           font-size: 0.9rem; border: 1px solid var(--border); border-radius: 6px; padding: 0.7rem; }
button { background: var(--accent); border: 0; color: #fff; border-radius: 6px;
         padding: 0.55rem 1.4rem; font-size: 0.95rem; cursor: pointer; margin-top: 0.6rem; }
button:disabled { opacity: 0.6; cursor: wait; }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
td, th { border: 1px solid var(--border); padding: 0.4rem 0.6rem; text-align: left; }
th { background: #f2f4f7; }
details summary { cursor: pointer; color: var(--accent); margin: 0.4rem 0; }
.point-card { border: 1px solid var(--border); border-radius: 6px; padding: 0.6rem 0.8rem;
              margin: 0.4rem 0; }
.point-card.awarded { border-left: 4px solid var(--ok); }
.point-card.not-awarded { border-left: 4px solid var(--bad); }
.error-box { border: 1px solid var(--bad); background: #fdf2f1; color: var(--bad);
             border-radius: 6px; padding: 0.6rem 0.8rem; margin: 0.4rem 0; white-space: pre-wrap; }
.notice { border: 1px solid var(--warn); background: #fffaf0; color: var(--warn);
          border-radius: 6px; padding: 0.5rem 0.8rem; margin: 0.4rem 0; }
img.shot { max-width: 100%; border: 1px solid var(--border); border-radius: 6px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 55rem) { .grid2 { grid-template-columns: 1fr; } }
"""

GRADE_SCRIPT = """
async function submitAnswer(recordId) {
  const button = document.getElementById('grade-button');
  const answer = document.getElementById('answer-input').value;
  const results = document.getElementById('results');
  button.disabled = true;
  results.innerHTML = '<div class="card"><h2>Grading</h2><p>Parsing and grading…</p></div>';
  try {
    const response = await fetch(`/record/${recordId}/grade`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({answer}),
    });
    const payload = await response.json();
    if (!response.ok) {
      results.innerHTML = `<div class="card"><h2>Error</h2><div class="error-box">${esc(payload.error || response.statusText)}</div></div>`;
      return;
    }
    results.innerHTML = renderResults(payload);
  } catch (error) {
    results.innerHTML = `<div class="card"><h2>Error</h2><div class="error-box">${esc(String(error))}</div></div>`;
  } finally {
    button.disabled = false;
  }
}

function esc(text) {
  return String(text ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

function renderResults(payload) {
  const parse = payload.parsed_answer.parse;
  const runner = payload.parsed_answer.runner || {};
  let out = '';

  out += '<div class="card"><h2>Compilation / Parsing</h2>';
  out += parse.ok
    ? '<p>Status <span class="badge ok">parsed</span></p>'
    : '<p>Status <span class="badge bad">parse failed</span></p>';
  if (runner.error) {
    out += `<div class="error-box">Parser runner error: ${esc(runner.error)}</div>`;
  }
  if ((parse.diagnostics || []).length) {
    out += '<h2>Diagnostics</h2>';
    for (const diag of parse.diagnostics) {
      const where = diag.line != null ? ` (line ${diag.line}, column ${diag.column})` : '';
      out += `<div class="error-box">${esc(diag.severity || 'error')}: ${esc(diag.message)}${esc(where)}` +
             (diag.hint ? `\nHint: ${esc(diag.hint)}` : '') + '</div>';
    }
  }
  out += `<details open><summary>AST JSON (${esc(parse.ast_version || '')})</summary>` +
         `<pre>${esc(JSON.stringify(parse.ast, null, 2))}</pre></details>`;
  out += '</div>';

  const grading = payload.grading;
  out += '<div class="card"><h2>Grading (Qwen via OpenRouter)</h2>';
  if (grading.dry_run) {
    out += '<div class="notice">Dry run: OPENROUTER_API_KEY is not set, so this grading result is a deterministic placeholder.</div>';
  }
  if (!grading.ok) {
    out += `<div class="error-box">Grading failed: ${esc(grading.error)}</div>`;
    if (grading.raw_response) {
      out += `<details><summary>Raw model response</summary><pre>${esc(grading.raw_response)}</pre></details>`;
    }
  } else {
    const result = grading.result;
    out += `<p><strong>${esc(result.total_awarded)} / ${esc(result.max_marks)} marks</strong>` +
           ` <span class="badge">${esc(grading.model)}</span></p>`;
    for (const point of result.points || []) {
      const cls = point.awarded ? 'awarded' : 'not-awarded';
      const badge = point.awarded ? '<span class="badge ok">awarded</span>' : '<span class="badge bad">not awarded</span>';
      out += `<div class="point-card ${cls}"><strong>${esc(point.marking_point_id)}</strong> ${badge}` +
             ` <span class="badge">${esc(point.marks_awarded)} mark(s)</span>` +
             (point.confidence ? ` <span class="badge">confidence: ${esc(point.confidence)}</span>` : '') +
             `<div>${esc(point.evidence)}</div>` +
             ((point.concerns || []).length ? `<div class="meta">Concerns: ${esc((point.concerns || []).join('; '))}</div>` : '') +
             '</div>';
    }
    if (result.overall_explanation) {
      out += `<p>${esc(result.overall_explanation)}</p>`;
    }
  }
  out += `<details><summary>Raw grading JSON</summary><pre>${esc(JSON.stringify(grading, null, 2))}</pre></details>`;
  out += '</div>';
  return out;
}
"""


def _page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title>"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<style>{PAGE_STYLE}</style></head><body>"
        "<header><h1>Cambridge Pseudocode Grading</h1>"
        "<nav><a href=\"/records\">All records</a></nav></header>"
        f"<main>{body}</main></body></html>"
    )


def _marker_label(record: Dict[str, Any]) -> str:
    key = record.get("segment_key") or {}
    label = f"Q{key.get('question_marker')}"
    if key.get("primary_marker"):
        label += str(key["primary_marker"])
    if key.get("secondary_marker"):
        label += str(key["secondary_marker"])
    return label


def render_records_page(store: RecordStore) -> str:
    rows = []
    for record in store.records:
        mark_scheme = record.get("mark_scheme") or {}
        points = mark_scheme.get("marking_points") or []
        snippet = html.escape((record.get("question_text") or "")[:110]).replace("\n", " ")
        rows.append(
            "<tr>"
            f"<td><a href=\"/record/{record['id']}\">{record['id']}</a></td>"
            f"<td>{html.escape(record.get('paper_code') or '')}</td>"
            f"<td>{html.escape(_marker_label(record))}</td>"
            f"<td>{html.escape(str(mark_scheme.get('max_marks') if mark_scheme.get('max_marks') is not None else '?'))}</td>"
            f"<td>{len(points)}</td>"
            f"<td>{snippet}…</td>"
            "</tr>"
        )
    body = (
        "<div class=\"card\"><h2>Pseudocode question records</h2>"
        f"<p>{len(store.records)} records loaded from "
        f"<code>{html.escape(str(store.records_path))}</code>.</p>"
        "<table><tr><th>ID</th><th>Paper</th><th>Question</th><th>Marks</th>"
        "<th>Marking points</th><th>Question text</th></tr>"
        + "".join(rows)
        + "</table></div>"
    )
    return _page("Records", body)


def render_record_page(record: Dict[str, Any], parser_available: bool) -> str:
    mark_scheme = record.get("mark_scheme") or {}
    marking_points = mark_scheme.get("marking_points") or []
    diagnostics = record.get("diagnostics") or []
    screenshots = (record.get("provenance") or {}).get("screenshots") or {}

    mp_html = ""
    if marking_points:
        for point in marking_points:
            mp_html += (
                "<div class=\"mp\">"
                f"<strong>{html.escape(str(point.get('id')))}</strong> "
                f"{html.escape(str(point.get('text')))}"
                f"<div class=\"meta\">{html.escape(str(point.get('marks', 1)))} mark(s)"
                f" · {html.escape(str(point.get('style') or 'unknown'))}"
                f" · confidence: {html.escape(str(point.get('confidence') or '?'))}</div>"
                "</div>"
            )
    else:
        mp_html = (
            "<div class=\"notice\">No structured marking points were extracted for this "
            "record; the grader will derive points from the raw mark-scheme answer below.</div>"
        )

    answer_text = mark_scheme.get("answer_text") or ""
    answer_details = (
        f"<details><summary>Mark-scheme answer text</summary><pre>{html.escape(answer_text)}</pre></details>"
        if answer_text
        else "<div class=\"error-box\">This record has no mark-scheme answer text.</div>"
    )

    marks_bits = []
    if mark_scheme.get("marks_value") is not None:
        marks_bits.append(f"mark scheme: {mark_scheme['marks_value']}")
    if record.get("qp_marks_value") is not None:
        marks_bits.append(f"question paper: {record['qp_marks_value']}")
    marks_line = " · ".join(marks_bits) or "unknown"

    diag_html = "".join(
        f"<div class=\"notice\">extraction: {html.escape(str(diag))}</div>" for diag in diagnostics
    )
    parser_note = (
        ""
        if parser_available
        else "<div class=\"error-box\">The Rust parser binary is not built. Run "
        "<code>cargo build --release</code> inside <code>pseudocode-parser/</code> "
        "so submissions can be parsed.</div>"
    )

    shot_html = ""
    if screenshots.get("selected_segment"):
        shot_html += (
            f"<details><summary>Question screenshot</summary>"
            f"<img class=\"shot\" src=\"/screenshot/{record['id']}/selected\" alt=\"question screenshot\"></details>"
        )
    if screenshots.get("question_context"):
        shot_html += (
            f"<details><summary>Full question context screenshot</summary>"
            f"<img class=\"shot\" src=\"/screenshot/{record['id']}/context\" alt=\"context screenshot\"></details>"
        )

    context_text = record.get("question_context_text") or ""
    context_html = ""
    if context_text and context_text != record.get("question_text"):
        context_html = (
            f"<details><summary>Parent question context</summary>"
            f"<div class=\"question-text\">{html.escape(context_text)}</div></details>"
        )

    body = (
        f"<div class=\"card\"><h2>{html.escape(record.get('paper_code') or '')} · "
        f"{html.escape(_marker_label(record))} · record {record['id']} · marks: {html.escape(marks_line)}</h2>"
        + diag_html
        + f"<div class=\"question-text\">{html.escape(record.get('question_text') or '')}</div>"
        + context_html
        + shot_html
        + "</div>"
        "<div class=\"grid2\">"
        f"<div class=\"card\"><h2>Mark-scheme marking points</h2>{mp_html}{answer_details}</div>"
        "<div class=\"card\"><h2>Student answer</h2>"
        + parser_note
        + "<textarea id=\"answer-input\" spellcheck=\"false\" "
        "placeholder=\"Write your Cambridge pseudocode answer here…\"></textarea>"
        f"<br><button id=\"grade-button\" onclick=\"submitAnswer({record['id']})\">Submit for grading</button>"
        "</div></div>"
        "<div id=\"results\"></div>"
        f"<script>{GRADE_SCRIPT}</script>"
    )
    return _page(f"Record {record['id']}", body)


class GradingRequestHandler(BaseHTTPRequestHandler):
    # Injected by make_server:
    store: RecordStore
    openrouter_config: OpenRouterConfig
    parse_timeout: float

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass  # keep the console quiet; errors are shown in responses

    def _send_html(self, content: str, status: int = 200) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _record_or_none(self, record_id: int) -> Optional[Dict[str, Any]]:
        return self.store.by_id.get(record_id)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        path = self.path.split("?", 1)[0]
        if path == "/":
            first = self.store.first_id()
            if first is None:
                self._send_html(
                    _page("No records", "<div class=\"card\"><h2>No records</h2>"
                          "<p>The records file contains no records.</p></div>"),
                    status=200,
                )
                return
            self.send_response(302)
            self.send_header("Location", f"/record/{first}")
            self.end_headers()
            return

        if path == "/records":
            self._send_html(render_records_page(self.store))
            return

        record_match = RECORD_PATH_PATTERN.match(path)
        if record_match:
            record = self._record_or_none(int(record_match.group(1)))
            if record is None:
                self._send_html(
                    _page("Not found", "<div class=\"card\"><h2>Not found</h2>"
                          "<p>No record with that id.</p></div>"),
                    status=404,
                )
                return
            self._send_html(
                render_record_page(record, parser_available=find_parser_binary() is not None)
            )
            return

        screenshot_match = SCREENSHOT_PATH_PATTERN.match(path)
        if screenshot_match:
            self._serve_screenshot(
                int(screenshot_match.group(1)), screenshot_match.group(2)
            )
            return

        self._send_html(
            _page("Not found", "<div class=\"card\"><h2>Not found</h2></div>"), status=404
        )

    def _serve_screenshot(self, record_id: int, kind: str) -> None:
        record = self._record_or_none(record_id)
        key = "selected_segment" if kind == "selected" else "question_context"
        stored_path = (
            ((record or {}).get("provenance") or {}).get("screenshots") or {}
        ).get(key)
        # Only paths recorded in the loaded records file are ever served.
        path = Path(stored_path) if stored_path else None
        if path is None or not path.is_file():
            self.send_response(404)
            self.end_headers()
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        match = GRADE_PATH_PATTERN.match(self.path.split("?", 1)[0])
        if not match:
            self._send_json({"error": "unknown endpoint"}, status=404)
            return
        record = self._record_or_none(int(match.group(1)))
        if record is None:
            self._send_json({"error": "record not found"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            request_payload = json.loads(raw)
            answer_text = request_payload.get("answer")
            if not isinstance(answer_text, str) or not answer_text.strip():
                self._send_json({"error": "answer text is empty"}, status=400)
                return
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": f"invalid request body: {error}"}, status=400)
            return

        try:
            parsed = parse_answer(answer_text, timeout=self.parse_timeout)
            grading = grade_answer(record, parsed, config=self.openrouter_config)
            self._send_json(
                {"record_id": record["id"], "parsed_answer": parsed, "grading": grading}
            )
        except Exception as error:  # noqa: BLE001 - surface, never hide, failures
            self._send_json({"error": f"internal error: {error}"}, status=500)


def make_server(
    records_path: Path,
    host: str = "127.0.0.1",
    port: int = 8000,
    parse_timeout: float = 10.0,
) -> ThreadingHTTPServer:
    store = RecordStore(records_path)
    config = OpenRouterConfig()

    class BoundHandler(GradingRequestHandler):
        pass

    BoundHandler.store = store
    BoundHandler.openrouter_config = config
    BoundHandler.parse_timeout = parse_timeout
    return ThreadingHTTPServer((host, port), BoundHandler)
