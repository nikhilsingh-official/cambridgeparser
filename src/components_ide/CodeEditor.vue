<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { basicSetup } from 'codemirror'
import { indentLess, indentMore } from '@codemirror/commands'
import { EditorState, Prec } from '@codemirror/state'
import { EditorView, keymap } from '@codemirror/view'
import { cambridgeHighlight, cambridgePseudocode } from '@/lib/ide/pseudocodeLanguage'

const INDENT_AFTER = /^(IF\b.*\bTHEN|ELSE\b|CASE\b.*\bOF|OTHERWISE\b|WHILE\b|REPEAT\b|FOR\b|PROCEDURE\b|FUNCTION\b|TYPE\b)/i
const OUTDENT_LINE = /^(ENDIF|ENDCASE|ENDWHILE|UNTIL|NEXT|ENDPROCEDURE|ENDFUNCTION|ENDTYPE|ELSE|OTHERWISE)\b/i

const props = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue'])
const mount = ref(null)
let view = null

function smartNewline({ state, dispatch }) {
  const head = state.selection.main.head
  const line = state.doc.lineAt(head)
  const beforeCursor = line.text.slice(0, head - line.from)
  const currentIndent = (line.text.match(/^\s*/) || [''])[0]
  let nextIndent = currentIndent
  if (INDENT_AFTER.test(beforeCursor.trim())) {
    nextIndent += '  '
  }
  if (OUTDENT_LINE.test(beforeCursor.trim())) {
    nextIndent = nextIndent.slice(0, Math.max(0, nextIndent.length - 2))
  }
  dispatch(state.update(state.replaceSelection(`\n${nextIndent}`), { scrollIntoView: true }))
  return true
}

onMounted(() => {
  view = new EditorView({
    parent: mount.value,
    state: EditorState.create({
      doc: props.modelValue,
      extensions: [
        basicSetup,
        cambridgePseudocode,
        cambridgeHighlight,
        EditorView.lineWrapping,
        Prec.high(keymap.of([
          { key: 'Enter', run: smartNewline },
          { key: 'Tab', run: indentMore },
          { key: 'Shift-Tab', run: indentLess },
        ])),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            emit('update:modelValue', update.state.doc.toString())
          }
        }),
      ],
    }),
  })
})

watch(
  () => props.modelValue,
  (value) => {
    if (!view) return
    const current = view.state.doc.toString()
    if (value !== current) {
      view.dispatch({ changes: { from: 0, to: current.length, insert: value } })
    }
  },
)

onBeforeUnmount(() => {
  view?.destroy()
})
</script>

<template>
  <div ref="mount" id="editor-mount" data-codemirror-mount aria-label="Pseudocode editor" />
</template>
