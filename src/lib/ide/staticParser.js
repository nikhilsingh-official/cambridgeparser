// Editor-side formatting only. Actually *running* pseudocode is done by the
// real Rust compiler in `wasmParser.js`; this file just re-indents the source
// so the "Format" button doesn't need the compiler.

const BLOCK_OPENERS = new Set([
  'IF',
  'CASE',
  'WHILE',
  'REPEAT',
  'FOR',
  'PROCEDURE',
  'FUNCTION',
  'TYPE',
])

const BLOCK_CLOSERS = new Set([
  'ENDIF',
  'ENDCASE',
  'ENDWHILE',
  'UNTIL',
  'NEXT',
  'ENDPROCEDURE',
  'ENDFUNCTION',
  'ENDTYPE',
])

// Words that dedent their own line but re-indent the block that follows.
const MIDBLOCK_WORDS = new Set(['ELSE', 'OTHERWISE'])

export function formatPseudocode(source) {
  let depth = 0
  const formatted = []

  for (const rawLine of source.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line) {
      formatted.push('')
      continue
    }

    const word = line.toUpperCase().split(/\s+/)[0]
    if (BLOCK_CLOSERS.has(word) || MIDBLOCK_WORDS.has(word)) {
      depth = Math.max(0, depth - 1)
    }

    formatted.push(`${'  '.repeat(depth)}${line}`)

    if (BLOCK_OPENERS.has(word) || MIDBLOCK_WORDS.has(word)) {
      depth += 1
    }
  }

  return formatted.join('\n')
}
