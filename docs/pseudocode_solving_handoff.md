# Pseudocode Solving Handoff

Date: 2026-07-23
Workspace: `/home/nikhils/Programming/Pseudocode Solving`

## Current User Intent

The user wants `src.website` to be a real static Vue website, built with the familiar `npm create vue` / Vite project layout, Vue Router, and Vue 3 Composition API (`<script setup>`), not a Python/Flask-style web app.

The website should:

- Read generated parser/question JSON directly from website resources.
- Preserve the old question reconstruction behavior from the previous website:
  - reconstruct question text from positioned word/character boxes;
  - turn repeated dot/underscore answer runs into inputs for fill-in-the-blank questions;
  - remove repeated dot runs for normal pseudocode-writing questions.
- Have an IDE-like layout:
  - top nav;
  - scrollable question sidebar;
  - question panel;
  - CodeMirror editor;
  - single terminal.
- Parse user-entered pseudocode and show output/diagnostics/AST in the terminal.
- Improve editor indentation/formatting beyond syntax highlighting.

## Important Context

The repo is dirty and already had a large uncommitted migration before the latest work. Do not assume all dirty files are from the last agent. `git status --short` currently includes many unrelated modified files outside `src/website`, plus deleted `src/pipeline/webapp/*`, and untracked `src/website/`, `src/resources/`, `resources/`, `package.json`, and `package-lock.json`.

Do not run destructive git commands. Do not revert unrelated modified files.

The previous Python direct-run error was:

```text
ImportError: attempted relative import with no known parent package
```

That was addressed by adding fallback absolute imports in `src/website/app.py`, but the user’s desired website is now the Vue app under `src/website/frontend/`, not the Python server.

## Current Implementation State

Vue/Vite app layout exists under:

- `src/website/frontend/index.html`
- `src/website/frontend/vite.config.js`
- `src/website/frontend/jsconfig.json`
- `src/website/frontend/src/main.js`
- `src/website/frontend/src/App.vue`
- `src/website/frontend/src/router/index.js`
- `src/website/frontend/src/views/IdeView.vue`
- `src/website/frontend/src/views/ProblemsView.vue`
- `src/website/frontend/src/views/ExamView.vue`
- `src/website/frontend/src/views/LearnView.vue`
- `src/website/frontend/src/components/CodeEditor.vue`
- `src/website/frontend/src/components/EditorPanel.vue`
- `src/website/frontend/src/components/PositionedQuestion.vue`
- `src/website/frontend/src/components/ProblemExplorer.vue`
- `src/website/frontend/src/components/QuestionPanel.vue`
- `src/website/frontend/src/components/TerminalPanel.vue`
- `src/website/frontend/src/services/pseudocodeLanguage.js`
- `src/website/frontend/src/services/records.js`
- `src/website/frontend/src/services/staticParser.js`
- `src/website/frontend/src/assets/main.css`

The Vue Router uses hash history in `src/website/frontend/src/router/index.js` for static-host friendliness.

All Vue SFCs are intended to use `<script setup>`. Tests check this for core views/components.

## Static Resources

Static resources are generated/copied by:

- `src/website/build_static_resources.py`

It reads:

- `pseudocode_writing_hits/pseudocode_question_records.json`
- legacy `qp_output/`
- legacy `normalize/normalized_marker_output/`

It writes:

- `src/website/frontend/public/resources/pseudocode_question_records.json`
- `src/website/frontend/public/resources/question_layouts.json`

The latest generated sizes observed:

- `src/website/frontend/public/resources/pseudocode_question_records.json`: 2,483,333 bytes
- `src/website/frontend/public/resources/question_layouts.json`: 1,819,516 bytes
- `src/website/static/resources/pseudocode_question_records.json`: 2,483,333 bytes
- `src/website/static/resources/question_layouts.json`: 1,819,516 bytes

`question_layouts.json` has:

- `schema_version`: `static-question-layouts/v1`
- `record_count`: 194
- `layout_count`: 194

## NPM Commands

`package.json` currently has:

```json
{
  "scripts": {
    "build:website:resources": "python -m src.website.build_static_resources",
    "dev:website": "npm run build:website:resources && vite --config src/website/frontend/vite.config.js",
    "build:website": "npm run build:website:resources && vite build --config src/website/frontend/vite.config.js",
    "preview:website": "vite preview --config src/website/frontend/vite.config.js"
  }
}
```

Dependencies include Vue 3, Vue Router, Vite, CodeMirror packages, and `@vitejs/plugin-vue`.

## What Was Verified Last

These commands passed in the previous session:

- `npm run build:website`
- `python -m py_compile $(find src tests -path '*/__pycache__/*' -prune -o -name '*.py' -print)`
- `python -m unittest discover -s tests -p 'test_*.py'`
  - 167 tests passed
- `python -m unittest src.pipeline.msplitter.tests.test_markers`

A Vite dev server was previously started at:

- `http://127.0.0.1:5173/`

Check whether it is still running before starting another one.

## Known Gaps / Likely Next Work

The browser parser in `src/website/frontend/src/services/staticParser.js` is intentionally lightweight. It currently:

- builds a basic AST for common lines;
- reports unmatched block terminators;
- prints simple `OUTPUT` literal values;
- prints symbolic output for expressions like `<x + 1>`.

It is not equivalent to the Rust parser/compiler. If the user expects exact parser/compiler behavior, the next agent should either:

- compile the Rust parser to WebAssembly and call it from Vue, or
- explicitly explain that exact Rust parser execution cannot happen in a fully static browser app unless the parser is shipped to the browser.

The question reconstruction renderer in `PositionedQuestion.vue` uses the static layout tokens and currently:

- renders positioned text;
- renders blanks as inputs when `isFillBlankQuestion(record)` returns true;
- hides blank tokens for normal writing questions.

Potential follow-up:

- visually inspect several records in browser, especially fill-in-the-blank versus writing prompts;
- tune `isFillBlankQuestion()` heuristics in `src/website/frontend/src/services/records.js`;
- make positioned pages scale responsively if they overflow horizontally too much;
- support figures/table crops if the static site needs them. Current static layout JSON has figure metadata, but the Vue renderer does not yet render figure images because cropped PNG resources are not generated/copied into `public/resources`.

The sidebar CSS was adjusted in `src/website/frontend/src/assets/main.css`:

- `.ide-shell` has `height: calc(100vh - 3rem)` and `overflow: hidden`;
- `.explorer` has `max-height: calc(100vh - 3rem)` and `overflow: hidden`;
- `.problem-list` scrolls independently.

The CodeMirror editor was improved in `CodeEditor.vue` and `staticParser.js`:

- smart Enter indentation;
- Tab / Shift-Tab indentation;
- `Format` button via `formatPseudocode()`.

Potential follow-up:

- test actual editor behavior in Playwright/browser;
- add indentation unit coverage if JS test infrastructure is introduced;
- consider a real Lezer parser/highlighter later.

## Test File Changes

`tests/test_webapp.py` was changed from Python HTTP-server tests to static Vue website checks. It now verifies:

- scaffold-like Vue file layout;
- hash router routes;
- Composition API `<script setup>`;
- copied static records JSON;
- generated static layouts JSON;
- editor indentation/format controls;
- browser parser wiring;
- built static index assets;
- legacy Python direct execution does not hit the original relative import error.

## Suggested Skills

- `implement`: for continuing the Vue/frontend implementation.
- `diagnosing-bugs`: if the next session starts from a browser/runtime issue, layout breakage, parser mismatch, or editor behavior bug.
- `code-review`: once the frontend changes are stable, review the dirty diff carefully before any commit because the worktree contains unrelated pre-existing changes.
- `prototype`: useful if the user wants to quickly compare alternate question viewer/editor/terminal layouts before hardening them.

## Cautions

- Do not commit automatically unless the user explicitly asks and you first isolate only the intended files. The worktree was already dirty and mixed.
- Avoid modifying legacy generated data outside the static resource generation flow.
- Do not restore the Python webapp as the primary website; the user explicitly asked for Vue components, Vue Router, and static JSON.
- Keep generated static site output under `src/website/static/`; keep source under `src/website/frontend/`.
