#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
MARKER_OUTPUT_DIR="${1:-$ROOT_DIR/resources/generated/marker_output}"
OCR_DIR="${2:-$ROOT_DIR/resources/ocr/surya_output}"
NORMALIZED_OUTPUT_DIR="${3:-$ROOT_DIR/resources/generated/normalized_marker_output}"

cd "$ROOT_DIR"
python3 -m src.pipeline.msplitter.normalize_marker_output \
  --all \
  --marker-output-dir "$MARKER_OUTPUT_DIR" \
  --ocr-dir "$OCR_DIR" \
  --normalized-output-dir "$NORMALIZED_OUTPUT_DIR"
