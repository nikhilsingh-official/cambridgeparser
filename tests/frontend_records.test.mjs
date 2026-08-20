import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  assembleFillSource,
  isFillBlankQuestion,
  overlayTokenText,
// path updated - the IDE's services moved to src/lib/ide/ when the two
// apps merged into one.
} from '../src/lib/ide/records.js'

test('overlay tokens copy with spaces within lines and newlines between them', () => {
  const tokens = [
    { text: 'A', x: 6, y: 6, w: 8, h: 20 },
    { text: 'procedure', x: 18, y: 6, w: 50, h: 20 },
    { text: 'OUTPUT', x: 30, y: 30, w: 55, h: 20 },
  ]

  assert.equal(overlayTokenText(tokens, 0), 'A ')
  assert.equal(overlayTokenText(tokens, 1), 'procedure\n      ')
  assert.equal(overlayTokenText(tokens, 2), 'OUTPUT\n')
})

const layoutWithBlank = {
  pages: [{ page_index: 1, width: 600, tokens: [{ kind: 'blank', x: 20, y: 20, w: 200 }] }],
}

// path updated for the merged app's single public/ directory.
const resourceRoot = new URL('../public/resources/', import.meta.url)
const records = JSON.parse(readFileSync(new URL('pseudocode_question_records.json', resourceRoot)))
const layouts = JSON.parse(readFileSync(new URL('question_layouts.json', resourceRoot)))
const record = (id) => records.records.find((candidate) => candidate.id === id)
const questionLayout = (id) => layouts.layouts[String(id)].question

test('overlay copy groups record 23 bullets with text by geometry', () => {
  const tokens = questionLayout(23).pages[0].tokens
  const bulletIndex = tokens.findIndex((token) => token.text === '•')

  assert.notEqual(bulletIndex, -1)
  assert.match(overlayTokenText(tokens, bulletIndex), /^• +$/)
})

test('context from an earlier sub-question does not enable fill mode', () => {
  const record = {
    question_text: 'Using pseudocode, write a pre-condition loop.',
    question_context_text: 'Copy and complete the table in part (a).',
  }

  assert.equal(isFillBlankQuestion(record, layoutWithBlank), false)
})

test('an explicit completion prompt enables fill mode when blanks were detected', () => {
  const record = {
    question_text: 'Complete the pseudocode for the function shown below.',
    question_context_text: '',
  }

  assert.equal(isFillBlankQuestion(record, layoutWithBlank), true)
})

test('fill mode stays off when extraction found no editable blanks', () => {
  const record = {
    question_text: 'Fill in the gaps to complete the pseudocode.',
    question_context_text: '',
  }

  assert.equal(isFillBlankQuestion(record, { pages: [] }), false)
})

test('completed blanks on separate pages retain distinct context', () => {
  const layout = {
    pages: [
      {
        page_index: 4,
        width: 600,
        tokens: [
          { kind: 'text', line: 1, x: 10, y: 20, text: 'OUTPUT' },
          { kind: 'blank', line: 1, x: 80, y: 20, w: 100 },
        ],
      },
      {
        page_index: 5,
        width: 600,
        tokens: [
          { kind: 'text', line: 1, x: 10, y: 20, text: 'RETURN' },
          { kind: 'blank', line: 1, x: 80, y: 20, w: 100 },
        ],
      },
    ],
  }
  const values = { '4:1': 'Name', '5:1': 'TRUE' }

  assert.equal(
    assembleFillSource(layout, values),
    'Blank 1 (OUTPUT [blank]): Name\nBlank 2 (RETURN [blank]): TRUE',
  )
})

test('real layouts distinguish inline gaps from full-width writing lines', () => {
  for (const id of [2, 28, 89, 170]) {
    assert.equal(isFillBlankQuestion(record(id), questionLayout(id)), true, `record ${id}`)
  }
  for (const id of [27, 95, 96]) {
    assert.equal(isFillBlankQuestion(record(id), questionLayout(id)), false, `record ${id}`)
  }
})

test('real gap-fill answer sheets preserve all answers without OCR reconstruction', () => {
  for (const id of [2, 89, 170, 177, 187]) {
    const layout = questionLayout(id)
    const values = Object.fromEntries(
      layout.pages.flatMap((page) => page.tokens.map((token, index) => (
        token.kind === 'blank' ? [`${page.page_index}:${index}`, 'ANSWER'] : null
      )).filter(Boolean)),
    )
    const source = assembleFillSource(layout, values)
    const expectedBlankCount = layout.pages
      .flatMap((page) => page.tokens)
      .filter((token) => token.kind === 'blank').length
    assert.equal(source.split('\n').length, expectedBlankCount, `record ${id}`)
    assert.match(source, /^Blank 1 \(.+\): ANSWER/)
    assert.doesNotMatch(source, /Complete the pseudocode|ĬÑ/)
  }
})

test('an entirely empty blank sheet does not invoke grading', () => {
  assert.equal(assembleFillSource(questionLayout(170), {}), '')
})
