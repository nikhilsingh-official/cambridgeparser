#!/usr/bin/env python3
"""Vendor the grading pipeline into the Cloud Function before deploy.

Run automatically by the ``functions.predeploy`` hook in ``firebase.json`` (and
runnable by hand before ``firebase emulators:start``). The Firebase build only
uploads the ``functions/`` directory, so the grading modules the function needs
are copied in from the repository's single source of truth,
``src/pipeline/grading``. The copy is generated -- it is gitignored and safe to
delete and regenerate.

Only stdlib-only modules are copied; the grading path used by the function never
invokes the native Rust parser (the browser sends its wasm parse instead).
"""

from __future__ import annotations

import shutil
from pathlib import Path

FUNCTIONS_DIR = Path(__file__).resolve().parent
REPO_ROOT = FUNCTIONS_DIR.parent
SRC = REPO_ROOT / "src" / "pipeline" / "grading"
DEST = FUNCTIONS_DIR / "grading"
MODULES = ("__init__.py", "ast_adapter.py", "openrouter_client.py")
RECORDS_SRC = REPO_ROOT / "pseudocode_writing_hits" / "pseudocode_question_records.json"


def main() -> int:
    if not SRC.is_dir():
        raise SystemExit(f"grading source not found: {SRC}")
    DEST.mkdir(exist_ok=True)
    for name in MODULES:
        src_file = SRC / name
        if not src_file.exists():
            raise SystemExit(f"missing grading module: {src_file}")
        shutil.copy2(src_file, DEST / name)
    if not RECORDS_SRC.is_file():
        raise SystemExit(f"question records not found: {RECORDS_SRC}")
    shutil.copy2(RECORDS_SRC, FUNCTIONS_DIR / "question_records.json")
    print(f"synced {len(MODULES)} grading modules and trusted question records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
