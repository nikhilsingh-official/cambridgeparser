//! Library entry point for the Cambridge pseudocode parser.
//!
//! The same parse pipeline backs three consumers:
//!   * the native `pseudocode-parser` CLI (`main.rs`),
//!   * the golden tests, and
//!   * the browser, via the raw wasm C-ABI in [`wasm_api`].
//!
//! `parse_to_json` is the single source of truth for the result JSON so the
//! website runs the *real* compiler rather than a JavaScript re-implementation.

#![allow(non_snake_case)]
#![allow(dead_code)]

pub mod errortype;
#[path = "Inter/mod.rs"]
pub mod Inter;
#[path = "Lexer/mod.rs"]
pub mod Lexer;
#[path = "Parser/mod.rs"]
pub mod Parser;
pub mod json_out;

use crate::Lexer::lexer::tokenize;
use crate::Parser::parser::Parser as PseudocodeParser;

/// Parse `source` and return the result JSON (`ok`, `statements`,
/// `diagnostics`, `stdout`). Parse failures are reported inside the JSON, not
/// as an `Err`, so every input yields a printable result.
pub fn parse_to_json(source: &str) -> String {
    let tokens = match tokenize(source) {
        Ok(tokens) => tokens,
        Err(error) => return json_out::result_json(false, &[], &[error]),
    };

    let mut parser = PseudocodeParser::new(tokens, source.to_string());
    match parser.parse_statements() {
        Ok(statements) => json_out::result_json(true, &statements, &[]),
        Err(error) => json_out::result_json(false, &[], &[error]),
    }
}

/// Raw wasm C-ABI so the browser can call the real parser without
/// `wasm-bindgen`. The JS glue in `wasmParser.js` mirrors this contract.
#[cfg(target_arch = "wasm32")]
pub mod wasm_api {
    use super::parse_to_json;
    use std::alloc::{alloc, dealloc, Layout};

    /// Allocate `len` bytes in wasm linear memory and return the pointer.
    /// The caller must release it with [`cps_free`] using the same `len`.
    #[no_mangle]
    pub extern "C" fn cps_alloc(len: usize) -> *mut u8 {
        if len == 0 {
            return std::ptr::null_mut();
        }
        let layout = Layout::from_size_align(len, 1).expect("valid layout");
        // SAFETY: layout has non-zero size.
        unsafe { alloc(layout) }
    }

    /// Free a buffer previously returned by [`cps_alloc`] or [`cps_parse`].
    #[no_mangle]
    pub extern "C" fn cps_free(ptr: *mut u8, len: usize) {
        if ptr.is_null() || len == 0 {
            return;
        }
        let layout = Layout::from_size_align(len, 1).expect("valid layout");
        // SAFETY: `ptr`/`len` came from `cps_alloc` with the same layout.
        unsafe { dealloc(ptr, layout) }
    }

    /// Parse the UTF-8 source at `ptr`/`len` and return a freshly allocated
    /// buffer laid out as `[u32 little-endian json length][json bytes]`.
    ///
    /// The input buffer is borrowed, not consumed: the caller still owns it and
    /// must free it. The returned buffer must be freed with
    /// `cps_free(out, 4 + json_length)`.
    #[no_mangle]
    pub extern "C" fn cps_parse(ptr: *const u8, len: usize) -> *mut u8 {
        // `from_raw_parts` is UB on a null pointer even for len 0, so an empty
        // buffer (JS passes a null pointer for zero-length source) maps to "".
        let source = if ptr.is_null() || len == 0 {
            ""
        } else {
            // SAFETY: JS writes valid UTF-8 (TextEncoder) into `[ptr, ptr+len)`.
            unsafe { std::str::from_utf8_unchecked(std::slice::from_raw_parts(ptr, len)) }
        };

        let bytes = parse_to_json(source).into_bytes();
        let total = 4 + bytes.len();
        let out = cps_alloc(total);
        // SAFETY: `out` points to `total` writable bytes just allocated.
        unsafe {
            let header = (bytes.len() as u32).to_le_bytes();
            std::ptr::copy_nonoverlapping(header.as_ptr(), out, 4);
            std::ptr::copy_nonoverlapping(bytes.as_ptr(), out.add(4), bytes.len());
        }
        out
    }
}
