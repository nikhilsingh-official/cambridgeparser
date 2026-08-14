// Loads the real Rust pseudocode compiler, compiled to WebAssembly, and runs
// it entirely in the browser. The result is byte-for-byte identical to the
// native `pseudocode-parser` CLI, so the terminal shows genuine compiler
// output instead of a JavaScript re-implementation.
//
// The wasm module exposes a tiny raw C-ABI (see `pseudocode-parser/src/lib.rs`):
//   cps_alloc(len)        -> ptr           allocate `len` bytes
//   cps_free(ptr, len)                     free a buffer
//   cps_parse(ptr, len)   -> ptr           parse UTF-8 source; returns a buffer
//                                          laid out as [u32 LE json length][json]

const WASM_URL = `${import.meta.env.BASE_URL}wasm/pseudocode_parser.wasm`

let instancePromise = null

function loadInstance() {
  if (!instancePromise) {
    instancePromise = (async () => {
      const response = await fetch(WASM_URL)
      if (!response.ok) {
        throw new Error(`Cannot load compiler module (${response.status})`)
      }
      // Prefer streaming compilation, but fall back to a byte buffer when the
      // dev server serves the wasm without an `application/wasm` MIME type.
      try {
        const { instance } = await WebAssembly.instantiateStreaming(response.clone(), {})
        return instance
      } catch {
        const bytes = await response.arrayBuffer()
        const { instance } = await WebAssembly.instantiate(bytes, {})
        return instance
      }
    })()
  }
  return instancePromise
}

/**
 * Compile a pseudocode source string with the real Rust compiler.
 * Returns the parsed result JSON: `{ ok, ast_version, statements, diagnostics, stdout }`.
 */
export async function parsePseudocode(source) {
  const instance = await loadInstance()
  const { cps_alloc, cps_free, cps_parse, memory } = instance.exports

  const bytes = new TextEncoder().encode(source)
  const inPtr = cps_alloc(bytes.length)
  if (bytes.length) {
    new Uint8Array(memory.buffer, inPtr, bytes.length).set(bytes)
  }

  const outPtr = cps_parse(inPtr, bytes.length)
  // Read the length header, then the JSON body. Views are created after the
  // call so they observe the current (possibly grown) memory buffer.
  const jsonLength = new DataView(memory.buffer).getUint32(outPtr, true)
  const json = new TextDecoder().decode(
    new Uint8Array(memory.buffer, outPtr + 4, jsonLength),
  )

  cps_free(inPtr, bytes.length)
  cps_free(outPtr, 4 + jsonLength)

  return JSON.parse(json)
}
