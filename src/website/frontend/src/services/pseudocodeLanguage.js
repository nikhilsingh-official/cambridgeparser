import { StreamLanguage, syntaxHighlighting, HighlightStyle } from '@codemirror/language'
import { tags } from '@lezer/highlight'

const KEYWORDS = new Set([
  'DECLARE',
  'CONSTANT',
  'IF',
  'THEN',
  'ELSE',
  'ENDIF',
  'CASE',
  'OF',
  'OTHERWISE',
  'ENDCASE',
  'WHILE',
  'ENDWHILE',
  'REPEAT',
  'UNTIL',
  'FOR',
  'TO',
  'NEXT',
  'PROCEDURE',
  'ENDPROCEDURE',
  'FUNCTION',
  'RETURNS',
  'ENDFUNCTION',
  'RETURN',
  'CALL',
  'INPUT',
  'OUTPUT',
  'OPENFILE',
  'READFILE',
  'WRITEFILE',
  'CLOSEFILE',
  'READ',
  'WRITE',
  'APPEND',
  'TYPE',
  'ENDTYPE',
  'ENDCLASS',
  'SET',
  'ARRAY',
])
const TYPE_KEYWORDS = new Set(['INTEGER', 'REAL', 'STRING', 'CHAR', 'BOOLEAN'])
const ATOMS = new Set(['TRUE', 'FALSE'])
const WORD_OPERATORS = new Set(['MOD', 'DIV', 'AND', 'OR', 'NOT'])

export const cambridgePseudocode = StreamLanguage.define({
  token(stream) {
    if (stream.eatSpace()) return null

    if (stream.match('//')) {
      stream.skipToEnd()
      return 'comment'
    }

    const quote = stream.peek()
    if (quote === '"' || quote === "'") {
      stream.next()
      while (!stream.eol()) {
        if (stream.next() === quote) break
      }
      return 'string'
    }

    if (stream.match(/^[0-9]+(?:\.[0-9]+)?/)) return 'number'

    if (stream.match(/^[A-Za-z_][A-Za-z0-9_]*/)) {
      const word = stream.current().toUpperCase()
      if (ATOMS.has(word)) return 'atom'
      if (TYPE_KEYWORDS.has(word)) return 'typeName'
      if (WORD_OPERATORS.has(word)) return 'operator'
      if (KEYWORDS.has(word)) return 'keyword'
      return 'variableName'
    }

    if (stream.match(/^(<-|<=|>=|<>|[+\-*/^&=<>:(),[\]])/)) {
      return /[+\-*/^&=<>]/.test(stream.current()) ? 'operator' : null
    }

    stream.next()
    return null
  },
})

export const cambridgeHighlight = syntaxHighlighting(
  HighlightStyle.define([
    { tag: tags.keyword, color: 'var(--accent)', fontWeight: '700' },
    { tag: tags.operator, color: 'var(--warning)', fontWeight: '650' },
    { tag: tags.atom, color: 'var(--success)', fontWeight: '650' },
    { tag: tags.typeName, color: 'var(--secondary-color-lightened)', fontWeight: '650' },
    { tag: tags.string, color: 'var(--secondary-color)' },
    { tag: tags.number, color: 'var(--warning)' },
    { tag: tags.comment, color: 'var(--muted)', fontStyle: 'italic' },
  ]),
)
