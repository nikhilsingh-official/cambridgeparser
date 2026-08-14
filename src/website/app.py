"""Stdlib IDE web app for Cambridge pseudocode practice and grading."""

from __future__ import annotations

import html
import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

from src.pipeline.grading.ast_adapter import find_parser_binary, parse_answer
from src.pipeline.grading.openrouter_client import OpenRouterConfig, grade_answer
from src.resources.paths import QP_OUTPUT_DIR, SOURCE_PDF_DIR
try:
    from .figure_render import render_region_png
    from .marker_regions import DEFAULT_MARKER_ROOT, MarkerRegionStore
    from .question_layout import build_question_layout, find_segment_node
except ImportError:  # Allows `python src/website/app.py` during local debugging.
    from src.website.figure_render import render_region_png
    from src.website.marker_regions import DEFAULT_MARKER_ROOT, MarkerRegionStore
    from src.website.question_layout import build_question_layout, find_segment_node

RECORD_PATH_PATTERN = re.compile(r"^/record/(\d+)$")
GRADE_PATH_PATTERN = re.compile(r"^/record/(\d+)/grade$")
SCREENSHOT_PATH_PATTERN = re.compile(r"^/screenshot/(\d+)/(selected|context)$")
FIGURE_PATH_PATTERN = re.compile(r"^/figure/(\d+)/(\d+)$")

DEFAULT_QP_DIR = QP_OUTPUT_DIR
DEFAULT_PDF_DIR = SOURCE_PDF_DIR
STATIC_DIR = Path(__file__).resolve().parent / "static"


class RecordStore:
    """Loads canonical pseudocode-question-record/v1 records and indexes by id."""

    def __init__(
        self,
        records_path: Path,
        qp_dir: Path = DEFAULT_QP_DIR,
        marker_root: Path = DEFAULT_MARKER_ROOT,
        pdf_dir: Path = DEFAULT_PDF_DIR,
    ) -> None:
        self.records_path = records_path
        self.qp_dir = qp_dir
        self.pdf_dir = pdf_dir
        self.marker_store = MarkerRegionStore(marker_root)
        with records_path.open() as handle:
            payload = json.load(handle)
        self.summary: Dict[str, Any] = payload.get("summary") or {}
        self.records: List[Dict[str, Any]] = payload.get("records") or []
        self.by_id: Dict[int, Dict[str, Any]] = {
            int(record["id"]): record for record in self.records if "id" in record
        }
        self._qp_cache: Dict[str, Optional[Dict[str, Any]]] = {}
        self._layout_cache: Dict[int, Dict[str, Any]] = {}

    def first_id(self) -> Optional[int]:
        return min(self.by_id) if self.by_id else None

    def _load_qp(self, paper_code: str) -> Optional[Dict[str, Any]]:
        if paper_code not in self._qp_cache:
            path = self.qp_dir / paper_code / "segmented_questions.json"
            data = None
            if path.is_file():
                with path.open() as handle:
                    data = json.load(handle)
            self._qp_cache[paper_code] = data
        return self._qp_cache[paper_code]

    def layout_for(self, record: Dict[str, Any]) -> Dict[str, Any]:
        record_id = int(record["id"])
        if record_id in self._layout_cache:
            return self._layout_cache[record_id]

        paper_code = record.get("paper_code") or ""
        empty = {"pages": [], "figure_count": 0, "blank_count": 0, "has_blanks": False}
        qp_payload = self._load_qp(paper_code)
        node = (
            find_segment_node(qp_payload, record.get("segment_key") or {})
            if qp_payload is not None
            else None
        )
        if node is None:
            self._layout_cache[record_id] = empty
            return empty

        layout = build_question_layout(
            node,
            self.marker_store.figures_by_page(paper_code),
            self.marker_store.code_by_page(paper_code),
        )
        self._layout_cache[record_id] = layout
        return layout

    def figure_region(
        self, record: Dict[str, Any], figure_index: int
    ) -> Optional[Dict[str, Any]]:
        layout = self.layout_for(record)
        for page in layout["pages"]:
            for figure in page["figures"]:
                if figure["index"] == figure_index:
                    return figure
        return None


def _marker_label(record: Dict[str, Any]) -> str:
    key = record.get("segment_key") or {}
    label = f"Q{key.get('question_marker')}"
    if key.get("primary_marker"):
        label += str(key["primary_marker"])
    if key.get("secondary_marker"):
        label += str(key["secondary_marker"])
    return label


def _record_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    mark_scheme = record.get("mark_scheme") or {}
    points = mark_scheme.get("marking_points") or []
    return {
        "id": record.get("id"),
        "paper_code": record.get("paper_code") or "",
        "label": _marker_label(record),
        "question_text": record.get("question_text") or "",
        "marks": mark_scheme.get("max_marks")
        if mark_scheme.get("max_marks") is not None
        else record.get("qp_marks_value"),
        "marking_point_count": len(points),
        "url": f"/record/{record.get('id')}",
    }


def _page(
    title: str,
    body: str,
    *,
    active: str = "IDE",
    bootstrap: Optional[Dict[str, Any]] = None,
) -> str:
    nav = []
    for label, href in (
        ("IDE", "/ide"),
        ("Problems", "/problems"),
        ("Learn", "/learn"),
    ):
        cls = "active" if label == active else ""
        nav.append(f"<a class=\"{cls}\" href=\"{href}\">{label}</a>")

    bootstrap_tag = ""
    if bootstrap is not None:
        data = json.dumps(bootstrap).replace("</", "<\\/")
        bootstrap_tag = (
            f"<script id=\"ide-bootstrap\" type=\"application/json\">{data}</script>"
        )

    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title>"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<link rel=\"stylesheet\" href=\"/static/app.css\">"
        "<script defer src=\"/static/app.js\"></script>"
        "</head><body>"
        "<header class=\"topbar\"><a class=\"brand\" href=\"/ide\">Cambridge IDE</a>"
        f"<nav>{''.join(nav)}</nav></header>"
        f"{bootstrap_tag}{body}</body></html>"
    )


def _mark_scheme_html(record: Dict[str, Any]) -> str:
    mark_scheme = record.get("mark_scheme") or {}
    marking_points = mark_scheme.get("marking_points") or []
    diagnostics = record.get("diagnostics") or []

    chunks = []
    for diag in diagnostics:
        chunks.append(
            f"<div class=\"notice\">extraction: {html.escape(str(diag))}</div>"
        )

    if marking_points:
        point_html = []
        for point in marking_points:
            point_html.append(
                "<div class=\"mark-point\">"
                f"<strong>{html.escape(str(point.get('id')))}</strong>"
                f"<span>{html.escape(str(point.get('text')))}</span>"
                f"<small>{html.escape(str(point.get('marks', 1)))} mark(s)"
                f" &middot; {html.escape(str(point.get('style') or 'unknown'))}"
                f" &middot; confidence: {html.escape(str(point.get('confidence') or '?'))}</small>"
                "</div>"
            )
        chunks.append(
            "<details><summary>Mark Scheme Points</summary>"
            f"{''.join(point_html)}</details>"
        )
    else:
        chunks.append(
            "<div class=\"notice\">No structured marking points were extracted for this "
            "record; the grader will derive points from the raw mark-scheme answer.</div>"
        )

    answer_text = mark_scheme.get("answer_text") or ""
    if answer_text:
        chunks.append(
            "<details><summary>Mark-Scheme Answer Text</summary>"
            f"<pre class=\"plain-pre\">{html.escape(answer_text)}</pre></details>"
        )
    else:
        chunks.append(
            "<div class=\"error-box\">This record has no mark-scheme answer text.</div>"
        )
    return "".join(chunks)


def _question_viewer_html(record: Dict[str, Any], layout: Dict[str, Any]) -> str:
    record_id = record["id"]
    screenshots = (record.get("provenance") or {}).get("screenshots") or {}
    has_selected_image = bool(screenshots.get("selected_segment"))
    has_text_layer = bool(layout.get("pages"))
    plain_text = html.escape(record.get("question_text") or "")

    if has_selected_image:
        image_body = (
            f"<div id=\"qview-image\" class=\"qview-image\">"
            f"<img src=\"/screenshot/{record_id}/selected\" alt=\"question image\"></div>"
        )
    else:
        image_body = (
            f"<div id=\"qview-image\" class=\"qview-image fallback-text\">{plain_text}</div>"
        )
    text_body = "<div id=\"qview-text\" class=\"qview-text\" hidden></div>"

    text_button = (
        "<button id=\"qview-btn-text\" class=\"seg-button\" type=\"button\">Text</button>"
        if has_text_layer
        else ""
    )
    fill_button = (
        "<button id=\"qview-fill\" class=\"ghost-button\" type=\"button\" hidden>"
        "Use Filled Text</button>"
        if has_text_layer and layout.get("has_blanks")
        else ""
    )

    meta = []
    if layout.get("figure_count"):
        meta.append(f"{layout['figure_count']} figure/table region(s)")
    if layout.get("blank_count"):
        meta.append(f"{layout['blank_count']} fill-in blank(s)")
    meta_text = " &middot; ".join(html.escape(item) for item in meta)

    return (
        "<section class=\"panel question-panel\">"
        "<div class=\"panel-title-row\"><h1>Question</h1>"
        "<div class=\"viewer-toolbar\"><span class=\"segmented\">"
        "<button id=\"qview-btn-image\" class=\"seg-button active\" type=\"button\">Image</button>"
        f"{text_button}</span>{fill_button}</div></div>"
        f"<p class=\"question-meta\">{html.escape(record.get('paper_code') or '')} &middot; "
        f"{html.escape(_marker_label(record))}"
        + (f" &middot; {meta_text}" if meta_text else "")
        + "</p>"
        "<div id=\"qview\" class=\"qview\">"
        f"<div class=\"qview-body\">{image_body}{text_body}</div>"
        "</div>"
        "<div class=\"question-details\">"
        + _mark_scheme_html(record)
        + "</div>"
        "</section>"
    )


def _editor_html(parser_available: bool) -> str:
    parser_note = (
        ""
        if parser_available
        else "<div class=\"error-box compact\">The Rust parser binary is not built. Run "
        "<code>cargo build --release</code> inside <code>pseudocode-parser/</code>.</div>"
    )
    return (
        "<section class=\"panel editor-panel\">"
        "<div class=\"panel-title-row\"><h1>Editor</h1>"
        "<div class=\"editor-actions\">"
        "<button id=\"run-button\" class=\"primary-button\" type=\"button\">Run</button>"
        "<button id=\"grade-button\" class=\"secondary-button\" type=\"button\">Grade</button>"
        "</div></div>"
        f"{parser_note}"
        "<div id=\"editor-mount\" data-codemirror-mount aria-label=\"Pseudocode editor\"></div>"
        "<textarea id=\"answer-input\" class=\"editor-fallback\" spellcheck=\"false\" "
        "placeholder=\"Write Cambridge pseudocode here\"></textarea>"
        "</section>"
    )


def _terminal_html() -> str:
    return (
        "<section class=\"terminal-panel\" aria-label=\"Kernel terminal\">"
        "<div class=\"terminal-toolbar\"><strong>Kernel Terminal</strong>"
        "<div class=\"terminal-actions\">"
        "<button id=\"terminal-copy-ast\" class=\"toggle-button\" type=\"button\">AST</button>"
        "<button id=\"terminal-copy-diagnostics\" class=\"toggle-button\" type=\"button\">Diagnostics</button>"
        "<button id=\"clear-terminal\" class=\"ghost-button\" type=\"button\">Clear</button>"
        "</div></div>"
        "<pre id=\"terminal-output\" class=\"terminal-output\">Ready.</pre>"
        "<div id=\"terminal-debug\" class=\"terminal-debug\" hidden>"
        "<pre id=\"ast-output\"></pre><pre id=\"diagnostics-output\"></pre>"
        "</div>"
        "</section>"
    )


def _explorer_html(store: RecordStore, selected_id: Optional[int]) -> str:
    items = []
    for record in store.records:
        summary = _record_summary(record)
        active = "active" if summary["id"] == selected_id else ""
        snippet = html.escape(summary["question_text"][:90]).replace("\n", " ")
        marks = "?" if summary["marks"] is None else summary["marks"]
        items.append(
            f"<a class=\"problem-link {active}\" href=\"/record/{summary['id']}\" "
            f"data-search=\"{html.escape((summary['paper_code'] + ' ' + summary['label'] + ' ' + summary['question_text']).lower())}\">"
            f"<strong>{html.escape(summary['paper_code'])}</strong>"
            f"<span>{html.escape(summary['label'])} &middot; {html.escape(str(marks))} mark(s)</span>"
            f"<small>{snippet}</small></a>"
        )
    return (
        "<aside class=\"explorer\"><div class=\"explorer-header\"><h2>Problems</h2>"
        f"<span>{len(store.records)}</span></div>"
        "<input id=\"problem-search\" type=\"search\" placeholder=\"Search records\" "
        "aria-label=\"Search generated question records\">"
        f"<div id=\"problem-list\" class=\"problem-list\">{''.join(items)}</div></aside>"
    )


def _bootstrap_payload(
    store: RecordStore, record: Optional[Dict[str, Any]], layout: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    return {
        "records": [_record_summary(item) for item in store.records],
        "selectedRecord": _record_summary(record) if record else None,
        "selectedRecordId": record.get("id") if record else None,
        "layout": layout or {"pages": [], "figure_count": 0, "blank_count": 0, "has_blanks": False},
        "initialSource": "",
    }


def render_ide_page(
    store: RecordStore,
    record: Optional[Dict[str, Any]],
    parser_available: bool,
    layout: Optional[Dict[str, Any]] = None,
) -> str:
    if record is None:
        body = (
            "<main class=\"empty-state\"><h1>Cambridge IDE</h1>"
            "<p>The records file contains no generated question records.</p></main>"
        )
        return _page(
            "Cambridge IDE",
            body,
            active="IDE",
            bootstrap=_bootstrap_payload(store, None, None),
        )

    resolved_layout = layout or {
        "pages": [],
        "figure_count": 0,
        "blank_count": 0,
        "has_blanks": False,
    }
    body = (
        "<main class=\"ide-shell\" data-page=\"ide\" "
        f"data-record-id=\"{html.escape(str(record['id']))}\">"
        f"{_explorer_html(store, int(record['id']))}"
        "<div class=\"workspace\">"
        "<div class=\"work-grid\">"
        f"{_question_viewer_html(record, resolved_layout)}"
        f"{_editor_html(parser_available)}"
        "</div>"
        f"{_terminal_html()}"
        "</div></main>"
    )
    return _page(
        f"IDE - Record {record['id']}",
        body,
        active="IDE",
        bootstrap=_bootstrap_payload(store, record, resolved_layout),
    )


def render_problems_page(store: RecordStore) -> str:
    rows = []
    for record in store.records:
        summary = _record_summary(record)
        snippet = html.escape(summary["question_text"][:130]).replace("\n", " ")
        marks = "?" if summary["marks"] is None else summary["marks"]
        rows.append(
            "<tr>"
            f"<td><a href=\"/record/{summary['id']}\">{summary['id']}</a></td>"
            f"<td>{html.escape(summary['paper_code'])}</td>"
            f"<td>{html.escape(summary['label'])}</td>"
            f"<td>{html.escape(str(marks))}</td>"
            f"<td>{summary['marking_point_count']}</td>"
            f"<td>{snippet}</td>"
            "</tr>"
        )
    body = (
        "<main class=\"problems-page\" data-page=\"problems\"><section class=\"panel\">"
        "<div class=\"panel-title-row\"><h1>Generated Problems</h1>"
        f"<span class=\"count-pill\">{len(store.records)} records</span></div>"
        f"<p class=\"path-note\">Loaded from <code>{html.escape(str(store.records_path))}</code>.</p>"
        "<div class=\"table-wrap\"><table><thead><tr><th>ID</th><th>Paper</th>"
        "<th>Question</th><th>Marks</th><th>Points</th><th>Question Text</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div></section></main>"
    )
    return _page("Problems", body, active="Problems")


def _terminal_text(parsed: Dict[str, Any]) -> str:
    parse_block = parsed.get("parse") or {}
    runner = parsed.get("runner") or {}
    compiler_output = parse_block.get("compiler_output") or {}
    runtime_stdout = str(compiler_output.get("stdout") or "")
    if runtime_stdout.strip():
        return runtime_stdout

    raw_stdout = str(runner.get("stdout") or "")
    if raw_stdout.strip():
        try:
            return json.dumps(json.loads(raw_stdout), indent=2)
        except json.JSONDecodeError:
            return raw_stdout

    stderr = str(runner.get("stderr") or "")
    if stderr.strip():
        return stderr

    diagnostics = parse_block.get("diagnostics") or []
    if diagnostics:
        return "\n".join(
            f"{diag.get('severity', 'error')}: {diag.get('message', '')}"
            for diag in diagnostics
        )
    return "Parser completed without output."


class GradingRequestHandler(BaseHTTPRequestHandler):
    # Injected by make_server:
    store: RecordStore
    openrouter_config: OpenRouterConfig
    parse_timeout: float

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass

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
            self.send_response(302)
            self.send_header("Location", "/ide")
            self.end_headers()
            return

        if path == "/ide":
            first = self.store.first_id()
            record = self._record_or_none(first) if first is not None else None
            self._send_html(
                render_ide_page(
                    self.store,
                    record,
                    parser_available=find_parser_binary() is not None,
                    layout=self.store.layout_for(record) if record else None,
                )
            )
            return

        if path in {"/problems", "/records"}:
            self._send_html(render_problems_page(self.store))
            return

        if path == "/learn":
            # Keep the curriculum canonical in the Vue application. The
            # stdlib server remains a supported entry point and hands this
            # route to the same built Learn page used in production.
            self.send_response(302)
            self.send_header("Location", "/static/index.html#/learn")
            self.end_headers()
            return

        if path.startswith("/static/"):
            self._serve_static(path)
            return

        record_match = RECORD_PATH_PATTERN.match(path)
        if record_match:
            record = self._record_or_none(int(record_match.group(1)))
            if record is None:
                self._send_html(
                    _page(
                        "Not Found",
                        "<main class=\"empty-state\"><h1>Not Found</h1>"
                        "<p>No record with that id.</p></main>",
                    ),
                    status=404,
                )
                return
            self._send_html(
                render_ide_page(
                    self.store,
                    record,
                    parser_available=find_parser_binary() is not None,
                    layout=self.store.layout_for(record),
                )
            )
            return

        screenshot_match = SCREENSHOT_PATH_PATTERN.match(path)
        if screenshot_match:
            self._serve_screenshot(
                int(screenshot_match.group(1)), screenshot_match.group(2)
            )
            return

        figure_match = FIGURE_PATH_PATTERN.match(path)
        if figure_match:
            self._serve_figure(
                int(figure_match.group(1)), int(figure_match.group(2))
            )
            return

        self._send_html(
            _page("Not Found", "<main class=\"empty-state\"><h1>Not Found</h1></main>"),
            status=404,
        )

    def _serve_static(self, path: str) -> None:
        relative = unquote(path.removeprefix("/static/"))
        if not relative or relative.startswith("/"):
            self.send_response(404)
            self.end_headers()
            return
        candidate = (STATIC_DIR / relative).resolve()
        try:
            candidate.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self.send_response(404)
            self.end_headers()
            return
        if not candidate.is_file():
            self.send_response(404)
            self.end_headers()
            return
        data = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if candidate.suffix == ".js":
            content_type = "application/javascript"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_screenshot(self, record_id: int, kind: str) -> None:
        record = self._record_or_none(record_id)
        key = "selected_segment" if kind == "selected" else "question_context"
        stored_path = (
            ((record or {}).get("provenance") or {}).get("screenshots") or {}
        ).get(key)
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

    def _serve_figure(self, record_id: int, figure_index: int) -> None:
        record = self._record_or_none(record_id)
        figure = (
            self.store.figure_region(record, figure_index) if record is not None else None
        )
        pdf_path = (
            self.store.pdf_dir / f"{record.get('paper_code')}.pdf"
            if record is not None
            else None
        )
        if figure is None or pdf_path is None or not pdf_path.is_file():
            self.send_response(404)
            self.end_headers()
            return
        page_index = figure["page_index"]
        page_size = self.store.marker_store.page_size(
            record.get("paper_code") or "", page_index
        )
        try:
            data = render_region_png(
                pdf_path,
                page_index,
                figure["bbox"],
                image_page_size=page_size or (794.0, 1123.0),
            )
        except Exception:  # noqa: BLE001 - a bad crop must not 500 the page
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw)

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        path = self.path.split("?", 1)[0]
        if path == "/kernel/run":
            self._handle_kernel_run()
            return

        match = GRADE_PATH_PATTERN.match(path)
        if match:
            self._handle_grade(int(match.group(1)))
            return

        self._send_json({"error": "unknown endpoint"}, status=404)

    def _handle_kernel_run(self) -> None:
        try:
            request_payload = self._read_json_body()
            if not isinstance(request_payload, dict):
                self._send_json({"error": "request body must be a JSON object"}, status=400)
                return
            source_text = request_payload.get("source")
            record_id = request_payload.get("record_id")
            if record_id is not None and type(record_id) is not int:
                self._send_json({"error": "record_id must be an integer or null"}, status=400)
                return
            if record_id is not None and self._record_or_none(record_id) is None:
                self._send_json({"error": "record not found"}, status=404)
                return
            if not isinstance(source_text, str) or not source_text.strip():
                self._send_json({"error": "source is empty"}, status=400)
                return
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": f"invalid request body: {error}"}, status=400)
            return

        parsed = parse_answer(source_text, timeout=self.parse_timeout)
        self._send_json(
            {
                "ok": bool((parsed.get("parse") or {}).get("ok")),
                "terminal_text": _terminal_text(parsed),
                "source": source_text,
                "parsed_answer": parsed,
            }
        )

    def _handle_grade(self, record_id: int) -> None:
        record = self._record_or_none(record_id)
        if record is None:
            self._send_json({"error": "record not found"}, status=404)
            return

        try:
            request_payload = self._read_json_body()
            if not isinstance(request_payload, dict):
                self._send_json({"error": "request body must be a JSON object"}, status=400)
                return
            answer_text = request_payload.get("answer")
            if not isinstance(answer_text, str) or not answer_text.strip():
                self._send_json({"error": "answer text is empty"}, status=400)
                return
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": f"invalid request body: {error}"}, status=400)
            return

        parsed = request_payload.get("parsed_answer")
        if not (
            isinstance(parsed, dict)
            and parsed.get("schema_version") == "parsed-answer/v1"
            and parsed.get("source_text") == answer_text
        ):
            parsed = parse_answer(answer_text, timeout=self.parse_timeout)

        try:
            grading = grade_answer(record, parsed, config=self.openrouter_config)
            self._send_json(
                {
                    "record_id": record["id"],
                    "terminal_text": _terminal_text(parsed),
                    "parsed_answer": parsed,
                    "grading": grading,
                }
            )
        except Exception as error:  # noqa: BLE001 - surface, never hide, failures
            self._send_json({"error": f"internal error: {error}"}, status=500)


def make_server(
    records_path: Path,
    host: str = "127.0.0.1",
    port: int = 8000,
    parse_timeout: float = 10.0,
    qp_dir: Path = DEFAULT_QP_DIR,
    marker_root: Path = DEFAULT_MARKER_ROOT,
    pdf_dir: Path = DEFAULT_PDF_DIR,
) -> ThreadingHTTPServer:
    store = RecordStore(
        records_path, qp_dir=qp_dir, marker_root=marker_root, pdf_dir=pdf_dir
    )
    config = OpenRouterConfig()

    class BoundHandler(GradingRequestHandler):
        pass

    BoundHandler.store = store
    BoundHandler.openrouter_config = config
    BoundHandler.parse_timeout = parse_timeout
    return ThreadingHTTPServer((host, port), BoundHandler)
