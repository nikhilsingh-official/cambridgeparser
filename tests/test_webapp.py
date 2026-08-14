import json
import http.client
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = REPO_ROOT / "src" / "website" / "frontend"
STATIC_ROOT = REPO_ROOT / "src" / "website" / "static"


class StaticVueWebsiteTests(unittest.TestCase):
    def test_public_question_images_are_tracked_for_deployment(self):
        layouts_path = (
            FRONTEND_ROOT / "public" / "resources" / "question_layouts.json"
        )
        layouts = json.loads(layouts_path.read_text()).get("layouts") or {}
        referenced = {
            FRONTEND_ROOT / "public" / "resources" / descriptor["src"]
            for layout in layouts.values()
            for descriptor in (layout.get("image"), layout.get("context_image"))
            if descriptor
        }
        tracked_result = subprocess.run(
            ["git", "ls-files", "-z", "--", "src/website/frontend/public/resources/images"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        )
        tracked = {
            REPO_ROOT / path.decode()
            for path in tracked_result.stdout.split(b"\0")
            if path
        }

        self.assertTrue(referenced)
        self.assertEqual(referenced - tracked, set())

    def test_question_panel_only_exposes_a_selectable_image_surface(self):
        panel = (FRONTEND_ROOT / "src" / "components" / "QuestionPanel.vue").read_text()
        ide = (FRONTEND_ROOT / "src" / "views" / "IdeView.vue").read_text()
        surface_path = (
            FRONTEND_ROOT / "src" / "components" / "SelectableQuestionImage.vue"
        )

        self.assertTrue(surface_path.is_file())
        surface = surface_path.read_text()
        self.assertIn("SelectableQuestionImage", panel)
        self.assertIn("SelectableTextOverlay", surface)
        self.assertIn("text-overlay", surface)
        self.assertNotIn("viewMode", panel)
        self.assertNotIn("viewMode", ide)
        self.assertNotIn(">Position</button>", panel)

    def test_static_resource_build_removes_stale_question_images(self):
        from src.website.build_static_resources import _prune_stale_layout_images

        with tempfile.TemporaryDirectory() as directory:
            images_dir = Path(directory)
            for name in ("q_1.png", "q_2.png", "ctx_1.png", "keep-me.png"):
                (images_dir / name).write_bytes(b"fixture")

            _prune_stale_layout_images(images_dir, {"q_1.png", "ctx_1.png"})

            self.assertTrue((images_dir / "q_1.png").is_file())
            self.assertTrue((images_dir / "ctx_1.png").is_file())
            self.assertFalse((images_dir / "q_2.png").exists())
            self.assertTrue((images_dir / "keep-me.png").is_file())

    def test_vue_scaffold_layout_exists(self):
        expected = [
            FRONTEND_ROOT / "index.html",
            FRONTEND_ROOT / "vite.config.js",
            FRONTEND_ROOT / "src" / "main.js",
            FRONTEND_ROOT / "src" / "App.vue",
            FRONTEND_ROOT / "src" / "router" / "index.js",
            FRONTEND_ROOT / "src" / "views" / "IdeView.vue",
            FRONTEND_ROOT / "src" / "views" / "LandingView.vue",
            FRONTEND_ROOT / "src" / "views" / "ProblemsView.vue",
            FRONTEND_ROOT / "src" / "components" / "CodeEditor.vue",
            FRONTEND_ROOT / "src" / "components" / "SelectableTextOverlay.vue",
            FRONTEND_ROOT / "src" / "services" / "staticParser.js",
        ]
        missing = [str(path) for path in expected if not path.is_file()]
        self.assertEqual(missing, [])

    def test_vue_router_uses_static_friendly_hash_history(self):
        router_source = (FRONTEND_ROOT / "src" / "router" / "index.js").read_text()
        self.assertIn("createRouter", router_source)
        self.assertIn("createWebHashHistory", router_source)
        self.assertIn("name: 'landing'", router_source)
        self.assertIn("path: '/ide'", router_source)
        self.assertNotIn("component: IdeView", router_source)
        self.assertIn("path: '/problems'", router_source)
        self.assertIn("path: '/learn'", router_source)
        self.assertIn("scrollBehavior", router_source)
        self.assertNotIn("path: '/exam'", router_source)
        app_source = (FRONTEND_ROOT / "src" / "App.vue").read_text()
        self.assertNotIn("Exam Mode", app_source)

    def test_components_use_composition_api_script_setup(self):
        for relative in [
            "src/App.vue",
            "src/views/IdeView.vue",
            "src/views/LearnView.vue",
            "src/components/CodeEditor.vue",
            "src/components/SelectableTextOverlay.vue",
            "src/components/ProblemExplorer.vue",
            "src/components/TerminalPanel.vue",
        ]:
            source = (FRONTEND_ROOT / relative).read_text()
            self.assertIn("<script setup>", source, relative)
            self.assertNotIn("export default", source, relative)

    def test_learn_page_is_populated_from_syllabus_and_corpus(self):
        source = (FRONTEND_ROOT / "src" / "views" / "LearnView.vue").read_text()
        for topic in [
            "Linear search",
            "Bubble sort",
            "Arrays",
            "Stacks, queues & linked lists",
            "Binary search & insertion sort",
            "Recursion & binary trees",
            "Decomposition & stepwise refinement",
            "Testing, tracing & complexity",
        ]:
            self.assertIn(topic, source)
        self.assertIn("syllabusRef", source)
        self.assertIn("questionCount", source)
        self.assertIn("Practice this topic", source)
        self.assertIn("lesson.slugs.join(',')", source)
        self.assertIn("name: 'learn', hash:", source)
        self.assertIn("Dictionary", source)
        self.assertNotIn("records.length || 194", source)
        self.assertNotIn("tagCounts.get('selection-if') || 86", source)

    def test_legacy_site_has_no_exam_mode_and_a_populated_learn_page(self):
        from src.website.app import _page, make_server

        source = (REPO_ROOT / "src" / "website" / "app.py").read_text()
        self.assertNotIn('("Exam Mode", "/ide?mode=exam")', source)
        self.assertNotIn("Coming soon.", source)
        chrome = _page("Learn", "", active="Learn")
        self.assertNotIn("Exam Mode", chrome)

        with tempfile.TemporaryDirectory() as directory:
            records_path = Path(directory) / "records.json"
            records_path.write_text('{"records": []}')
            server = make_server(records_path, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = http.client.HTTPConnection(*server.server_address)
                connection.request("GET", "/learn")
                response = connection.getresponse()
                self.assertEqual(response.status, 302)
                self.assertEqual(response.getheader("Location"), "/static/index.html#/learn")
                response.read()
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_static_records_json_is_copied_into_vue_public_resources(self):
        source_path = REPO_ROOT / "pseudocode_writing_hits" / "pseudocode_question_records.json"
        public_path = (
            FRONTEND_ROOT / "public" / "resources" / "pseudocode_question_records.json"
        )
        static_path = STATIC_ROOT / "resources" / "pseudocode_question_records.json"

        self.assertTrue(public_path.is_file())
        self.assertTrue(static_path.is_file())
        source_payload = json.loads(source_path.read_text())
        public_payload = json.loads(public_path.read_text())
        static_payload = json.loads(static_path.read_text())
        self.assertEqual(public_payload["record_count"], len(source_payload["records"]))
        self.assertEqual(static_payload, public_payload)

        self.assertGreater(len(public_payload.get("records", [])), 0)
        self.assertEqual(
            public_payload["records"][0]["schema_version"],
            "pseudocode-question-record/v1",
        )
        self.assertNotIn("answer_text", public_payload["records"][0]["mark_scheme"])
        self.assertNotIn("marking_points", public_payload["records"][0]["mark_scheme"])
        self.assertIn("answer_text", source_payload["records"][0]["mark_scheme"])

        normalized_questions = [
            " ".join(record["question_text"].casefold().split())
            for record in public_payload["records"]
        ]
        self.assertEqual(len(normalized_questions), len(set(normalized_questions)))

    def test_static_question_layouts_are_available_for_positioned_rendering(self):
        public_path = FRONTEND_ROOT / "public" / "resources" / "question_layouts.json"
        static_path = STATIC_ROOT / "resources" / "question_layouts.json"
        self.assertTrue(public_path.is_file())
        self.assertTrue(static_path.is_file())

        payload = json.loads(public_path.read_text())
        records_payload = json.loads(
            (FRONTEND_ROOT / "public" / "resources" / "pseudocode_question_records.json").read_text()
        )
        self.assertEqual(payload["schema_version"], "static-question-layouts/v1")
        self.assertEqual(payload["layout_count"], records_payload["record_count"])
        first_layout = payload["layouts"]["1"]
        self.assertGreater(first_layout["question"]["blank_count"], 0)
        self.assertIn("tokens", first_layout["question"]["pages"][0])

    def test_editor_has_indentation_and_format_controls(self):
        editor_source = (FRONTEND_ROOT / "src" / "components" / "CodeEditor.vue").read_text()
        panel_source = (FRONTEND_ROOT / "src" / "components" / "EditorPanel.vue").read_text()
        parser_source = (FRONTEND_ROOT / "src" / "services" / "staticParser.js").read_text()
        self.assertIn("smartNewline", editor_source)
        self.assertIn("Shift-Tab", editor_source)
        self.assertIn("Format", panel_source)
        self.assertIn("formatPseudocode", parser_source)

    def test_run_uses_real_wasm_compiler_not_placeholder(self):
        view_source = (FRONTEND_ROOT / "src" / "views" / "IdeView.vue").read_text()
        wasm_service = (FRONTEND_ROOT / "src" / "services" / "wasmParser.js").read_text()
        # Run wires the editor to the wasm-compiled Rust compiler, not a
        # JavaScript re-implementation or a hardcoded placeholder.
        self.assertIn("wasmParser", view_source)
        self.assertIn("parsePseudocode", view_source)
        self.assertIn("cps_parse", wasm_service)
        self.assertIn("pseudocode_parser.wasm", wasm_service)
        self.assertNotIn("[static-site]", view_source)
        self.assertNotIn("browser-parser", view_source)
        # The compiled module must be present for the browser to fetch.
        self.assertTrue(
            (FRONTEND_ROOT / "public" / "wasm" / "pseudocode_parser.wasm").is_file()
        )

    def test_submit_button_wires_grading_service(self):
        view = (FRONTEND_ROOT / "src" / "views" / "IdeView.vue").read_text()
        panel = (FRONTEND_ROOT / "src" / "components" / "EditorPanel.vue").read_text()
        grading = (FRONTEND_ROOT / "src" / "services" / "grading.js").read_text()
        self.assertIn("gradeSubmission", view)
        self.assertIn("ResultsPanel", view)
        self.assertIn("'submit'", panel)
        self.assertIn("/api/grade", grading)
        self.assertIn("Authorization: `Bearer ${token}`", grading)
        self.assertIn("record_id: record.id", grading)

    def test_production_grading_is_authenticated_and_rate_limited(self):
        function_source = (REPO_ROOT / "functions" / "main.py").read_text()
        self.assertIn("verify_id_token", function_source)
        self.assertIn("_consume_account_quota", function_source)
        self.assertIn('status=429', function_source)
        self.assertIn('"Retry-After"', function_source)
        self.assertNotIn('request.get("record")', function_source)

    def test_public_landing_page_only_links_into_login(self):
        landing = (FRONTEND_ROOT / "src" / "views" / "LandingView.vue").read_text()
        self.assertIn('to="/login"', landing)
        self.assertIn('class="hero"', landing)
        self.assertNotIn('<footer', landing)

    def test_vue_pages_share_the_selected_light_and_dark_themes(self):
        index = (FRONTEND_ROOT / "index.html").read_text()
        main_js = (FRONTEND_ROOT / "src" / "main.js").read_text()
        styles = (FRONTEND_ROOT / "src" / "assets" / "main.css").read_text()
        landing = (FRONTEND_ROOT / "src" / "views" / "LandingView.vue").read_text()
        app = (FRONTEND_ROOT / "src" / "App.vue").read_text()

        self.assertIn("api.fontshare.com", index)
        self.assertIn("general-sans", index)
        self.assertNotIn("@fontsource-variable/lexend", main_js)
        self.assertNotIn("ibm-plex-sans", main_js)
        self.assertIn('--font-display: "General Sans"', styles)
        self.assertIn('--font-body: "General Sans"', styles)
        self.assertIn("[data-theme='dark']", styles)
        self.assertIn("#faf8f3", styles)
        self.assertIn("#0e1116", styles)
        self.assertIn("font-family: var(--font-body);", styles)
        self.assertIn(".topbar nav a {\n  color: var(--muted);\n  font-family: var(--font-display);", styles)
        self.assertIn(".lesson-index a {", styles)
        self.assertIn(".practice-link,\n.practice-unavailable {", styles)
        self.assertGreater(
            styles.index("button {\n  font-family: var(--font-display);"),
            styles.index("button,\ninput,\ntextarea {\n  font: inherit;"),
        )
        self.assertNotIn("#0d1110", landing)
        self.assertNotIn("#a6f4d2", landing)
        self.assertIn("ThemeToggle", landing)
        self.assertIn("ThemeToggle", app)

    def test_landing_and_learn_pages_have_no_eyebrow_text(self):
        landing = (FRONTEND_ROOT / "src" / "views" / "LandingView.vue").read_text()
        learn = (FRONTEND_ROOT / "src" / "views" / "LearnView.vue").read_text()
        styles = (FRONTEND_ROOT / "src" / "assets" / "main.css").read_text()

        for source in (landing, learn, styles):
            self.assertNotIn("eyebrow", source)
            self.assertNotIn("learn-kicker", source)
            self.assertNotIn("frequency-label", source)
            self.assertNotIn("lesson-label", source)

    def test_theme_preference_resolution(self):
        script = """
          import {
            DARK_THEME,
            LIGHT_THEME,
            preferredTheme,
          } from './src/website/frontend/src/services/theme.js'

          const actual = [
            preferredTheme(LIGHT_THEME, true),
            preferredTheme(DARK_THEME, false),
            preferredTheme(null, true),
            preferredTheme(null, false),
            preferredTheme('unknown', true),
          ]
          const expected = [LIGHT_THEME, DARK_THEME, DARK_THEME, LIGHT_THEME, DARK_THEME]
          if (JSON.stringify(actual) !== JSON.stringify(expected)) process.exit(1)
        """
        completed = subprocess.run(
            ["node", "--input-type=module", "--eval", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_auth_ready_does_not_wait_for_profile_database_write(self):
        source = (FRONTEND_ROOT / "src" / "services" / "auth.js").read_text()
        self.assertLess(source.index("resolve(user)"), source.index("await ensureUserRecord(user)"))

    def test_mark_scheme_hidden_in_question_panel_until_submit(self):
        question = (FRONTEND_ROOT / "src" / "components" / "QuestionPanel.vue").read_text()
        results = (FRONTEND_ROOT / "src" / "components" / "ResultsPanel.vue").read_text()
        # The always-visible question view must not expose the mark scheme.
        self.assertNotIn("marking_points", question)
        self.assertNotIn("answer_text", question)
        self.assertIn("Show context", question)
        # The mark scheme + grading live in the post-submit results panel.
        self.assertIn("marking_points", results)
        self.assertIn("AI Grading", results)

    def test_built_static_index_points_to_vite_assets(self):
        index = (STATIC_ROOT / "index.html").read_text()
        self.assertIn('<div id="app"></div>', index)
        self.assertIn("./assets/", index)
        self.assertTrue((STATIC_ROOT / "assets").is_dir())

    def test_legacy_python_app_direct_execution_does_not_raise_import_error(self):
        completed = subprocess.run(
            [sys.executable, "./src/website/app.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("attempted relative import", completed.stderr)


class GradeEndpointTests(unittest.TestCase):
    """The /api/grade entrypoint reused by the vite dev server and Firebase."""

    def test_grade_request_dry_run_without_key(self):
        import os
        from unittest import mock

        from src.website.grade_one import grade_request

        record = {
            "mark_scheme": {
                "max_marks": 3,
                "marking_points": [
                    {"id": "mp1", "text": "declare x", "marks": 1},
                    {"id": "mp2", "text": "output x", "marks": 1},
                ],
            }
        }
        request = {
            "record": record,
            "source": "OUTPUT 1",
            "parse": {"ok": True, "statements": [], "diagnostics": []},
        }
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENROUTER_API_KEY", None)
            result = grade_request(request)

        self.assertEqual(result["schema_version"], "grading-result/v1")
        self.assertTrue(result["ok"])
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["mark_scheme"], record["mark_scheme"])
        self.assertIsInstance(result["result"]["total_awarded"], int)
        self.assertLessEqual(result["result"]["total_awarded"], 3)

    def test_grade_request_rejects_missing_record(self):
        from src.website.grade_one import grade_request

        result = grade_request({"source": "OUTPUT 1"})
        self.assertFalse(result["ok"])
        self.assertIn("record", result["error"])

    def test_grade_request_resolves_trusted_record_by_id(self):
        import os
        from unittest import mock

        from src.website.grade_one import grade_request

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENROUTER_API_KEY", None)
            result = grade_request({"record_id": 1, "source": "OUTPUT 1", "parse": {}})

        self.assertTrue(result["ok"])
        self.assertTrue(result["mark_scheme"]["marking_points"])


if __name__ == "__main__":
    unittest.main()
