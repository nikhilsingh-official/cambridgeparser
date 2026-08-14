#!/usr/bin/env bash
# Compile the Rust pseudocode parser to WebAssembly and copy the module into
# the Vue app's public assets so the browser runs the *real* compiler.
#
# Requires the wasm target once:  rustup target add wasm32-unknown-unknown
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
crate_dir="$repo_root/pseudocode-parser"
out_dir="$repo_root/src/website/frontend/public/wasm"
wasm="$crate_dir/target/wasm32-unknown-unknown/release/pseudocode_parser.wasm"

echo "Building pseudocode-parser wasm module..."
cargo build --release --lib --manifest-path "$crate_dir/Cargo.toml" \
  --target wasm32-unknown-unknown

mkdir -p "$out_dir"
cp "$wasm" "$out_dir/pseudocode_parser.wasm"
echo "Copied $(basename "$wasm") ($(wc -c < "$wasm") bytes) -> $out_dir"
