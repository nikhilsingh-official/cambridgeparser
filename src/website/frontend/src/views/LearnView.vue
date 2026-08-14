<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { loadQuestionRecords } from '@/services/records'

const records = ref([])

const lessons = [
  {
    id: 'control-flow',
    group: 'Foundations',
    title: 'Selection & iteration',
    syllabusRef: '9.2 · 11.2',
    slugs: ['selection-if', 'selection-case', 'count-controlled-loop', 'pre-condition-loop', 'post-condition-loop', 'nested-loops'],
    summary: 'Turn a sequence of steps into decisions and loops—the grammar behind almost every exam algorithm.',
    idea: 'Choose FOR when the repeat count is known, WHILE when the condition is checked first, and REPEAT when the body must run at least once.',
    code: `FOR Index ← 1 TO Length
  IF Values[Index] > Highest THEN
    Highest ← Values[Index]
  ENDIF
NEXT Index`,
    pitfalls: ['Using REPEAT when zero iterations must be possible', 'Forgetting to update a WHILE-loop control value', 'Writing separate IFs when conditions are mutually exclusive'],
  },
  {
    id: 'modules',
    group: 'Foundations',
    title: 'Functions & procedures',
    syllabusRef: '9.1 · 11.3',
    slugs: ['functions', 'procedures', 'parameters', 'decomposition'],
    summary: 'Decompose a problem into named modules with small, explicit interfaces.',
    idea: 'A function returns a value and belongs in an expression. A procedure performs a task. Pass only the data the module needs and use BYREF only when the caller’s value must change.',
    code: `FUNCTION IsValid(Value : INTEGER) RETURNS BOOLEAN
  RETURN Value >= 1 AND Value <= 100
ENDFUNCTION

PROCEDURE ShowResult(Value : INTEGER)
  OUTPUT Value
ENDPROCEDURE`,
    pitfalls: ['Calling a function with CALL', 'Missing a RETURN on one branch', 'Changing global data when a parameter would make the dependency clear'],
  },
  {
    id: 'design-refinement',
    group: 'Foundations',
    title: 'Decomposition & stepwise refinement',
    syllabusRef: '9.1 · 9.2 · 12.2',
    slugs: ['decomposition', 'stepwise-refinement', 'structured-english', 'flowchart', 'structure-chart'],
    summary: 'Move from a large scenario to small modules and precise steps before committing to code.',
    idea: 'Decompose by responsibility, define the data passed between modules, then refine each task until every step can be expressed using sequence, selection, or iteration.',
    code: `ProcessOrder
  GetValidOrder
    REPEAT input order UNTIL valid
  CalculateTotal
    total each line item
    apply discount
  DisplayReceipt
    output itemised result`,
    pitfalls: ['Splitting by arbitrary line count instead of responsibility', 'Refining one branch while leaving another vague', 'Sharing globals instead of defining module interfaces'],
  },
  {
    id: 'arrays',
    group: 'Data structures',
    title: 'Arrays & array processing',
    syllabusRef: '10.2',
    slugs: ['arrays-1d', 'arrays-2d', 'array-processing', 'nested-loops'],
    summary: 'Store same-type values under one identifier, then traverse them safely and systematically.',
    idea: 'Use one loop per dimension. Initialise totals, counters, minima, or maxima before traversal, and respect the declared lower and upper bounds.',
    code: `DECLARE Scores : ARRAY[1:30] OF INTEGER
Total ← 0
FOR Index ← 1 TO 30
  Total ← Total + Scores[Index]
NEXT Index`,
    pitfalls: ['Starting at index 0 when the array begins at 1', 'Using the wrong dimension in a nested loop', 'Initialising a maximum to 0 when values may be negative'],
  },
  {
    id: 'strings-validation',
    group: 'Data structures',
    title: 'Strings & validation',
    syllabusRef: '6.2 · 11.1',
    slugs: ['string-handling', 'validation', 'built-in-functions'],
    summary: 'Extract, compare, clean, and validate character data with the supplied string functions.',
    idea: 'Validate each rule separately—length, range, format, or presence—then combine Boolean results. Cambridge supplies non-standard library functions in the question or insert.',
    code: `Valid ← LENGTH(Code) = 5
FOR Index ← 1 TO LENGTH(Code)
  NextChar ← MID(Code, Index, 1)
  Valid ← Valid AND NextChar >= "0" AND NextChar <= "9"
NEXT Index`,
    pitfalls: ['Off-by-one substring positions', 'Confusing a CHAR with a one-character STRING', 'Stopping after the first rule when every rule must pass'],
  },
  {
    id: 'files-records',
    group: 'Data structures',
    title: 'Records & text files',
    syllabusRef: '10.1 · 10.3',
    slugs: ['records', 'text-files'],
    summary: 'Group unlike fields into records and persist line-based data with an explicit file lifecycle.',
    idea: 'A record models one entity; a file stores entities beyond one run. Open in the correct mode, process until EOF when reading, and always close the file.',
    code: `TYPE Student
  DECLARE Name : STRING
  DECLARE Mark : INTEGER
ENDTYPE

DECLARE ThisStudent : Student
ThisStudent.Name ← "Ada"
ThisStudent.Mark ← 87

OPENFILE "Students.txt" FOR APPEND
WRITEFILE "Students.txt", ThisStudent.Name & "," & NUM_TO_STR(ThisStudent.Mark)
CLOSEFILE "Students.txt"`,
    pitfalls: ['Reading after EOF', 'Opening with WRITE when existing data must survive', 'Forgetting which delimiter separates fields in a line'],
  },
  {
    id: 'linear-search',
    group: 'Algorithms',
    title: 'Linear search',
    syllabusRef: '10.2 · 19.1',
    slugs: ['linear-search'],
    summary: 'Inspect items in order until the target is found or the data is exhausted.',
    idea: 'Linear search works on unsorted data and takes O(n) time in the worst case. A Boolean flag or sentinel result makes the “not found” path explicit.',
    code: `Position ← -1
Index ← 1
WHILE Index <= Length AND Position = -1
  IF Data[Index] = Target THEN
    Position ← Index
  ENDIF
  Index ← Index + 1
ENDWHILE`,
    pitfalls: ['Continuing after a match when only one result is needed', 'Never handling the not-found result', 'Using binary search on unsorted data'],
  },
  {
    id: 'bubble-sort',
    group: 'Algorithms',
    title: 'Bubble sort',
    syllabusRef: '10.2 · 19.1',
    slugs: ['bubble-sort'],
    summary: 'Compare adjacent values and swap inverted pairs until a complete pass makes no swaps.',
    idea: 'After each pass, the largest unsorted item has moved to the boundary. The basic algorithm is O(n²); a swap flag and shrinking boundary avoid unnecessary comparisons.',
    code: `Boundary ← Length - 1
REPEAT
  NoSwaps ← TRUE
  FOR Index ← 1 TO Boundary
    IF Data[Index] > Data[Index + 1] THEN
      Temp ← Data[Index]
      Data[Index] ← Data[Index + 1]
      Data[Index + 1] ← Temp
      NoSwaps ← FALSE
    ENDIF
  NEXT Index
  Boundary ← Boundary - 1
UNTIL NoSwaps`,
    pitfalls: ['Comparing the final item with an out-of-range next item', 'Swapping only one of the two values', 'Resetting the swap flag inside the inner loop'],
  },
  {
    id: 'adts',
    group: 'Data structures',
    title: 'Stacks, queues & linked lists',
    syllabusRef: '10.4 · 19.1',
    slugs: ['adt-stack', 'adt-queue', 'adt-linked-list'],
    summary: 'Choose an abstract data type by the operations and access order the problem needs.',
    idea: 'Stacks are LIFO, queues are FIFO, and linked lists connect nodes through pointers. A Dictionary stores key–value pairs for direct lookup. At A Level, know the operations each structure exposes and how arrays can implement them.',
    code: `// Stack push
IF StackPointer < MaxSize THEN
  StackPointer ← StackPointer + 1
  Stack[StackPointer] ← NewItem
ENDIF

// Circular queue advance
RearPointer ← (RearPointer MOD MaxSize) + 1`,
    pitfalls: ['Moving a pointer before checking overflow or underflow', 'Treating a queue like a stack', 'Losing the next pointer while deleting a linked-list node'],
  },
  {
    id: 'advanced-search-sort',
    group: 'Algorithms',
    title: 'Binary search & insertion sort',
    syllabusRef: '19.1',
    slugs: ['binary-search', 'insertion-sort'],
    summary: 'Extend the core search/sort toolkit for ordered data and A Level problems.',
    idea: 'Binary search needs sorted data and repeatedly halves the search interval for O(log n) time. Insertion sort grows a sorted prefix by shifting larger values right.',
    code: `// Binary search
Low ← 1
High ← Length
WHILE Low <= High AND Position = -1
  Mid ← (Low + High) DIV 2
  IF Data[Mid] = Target THEN
    Position ← Mid
  ELSE
    IF Data[Mid] < Target THEN Low ← Mid + 1
    ELSE High ← Mid - 1
    ENDIF
  ENDIF
ENDWHILE

// Insertion sort
FOR Index ← 2 TO Length
  Item ← Data[Index]
  Position ← Index - 1
  WHILE Position >= 1 AND Data[Position] > Item
    Data[Position + 1] ← Data[Position]
    Position ← Position - 1
  ENDWHILE
  Data[Position + 1] ← Item
NEXT Index`,
    pitfalls: ['Applying binary search before sorting', 'Failing to move Low or High past Mid', 'Overwriting the insertion value before shifting is complete'],
  },
  {
    id: 'recursion-trees',
    group: 'Algorithms',
    title: 'Recursion & binary trees',
    syllabusRef: '19.1 · 19.2',
    slugs: ['recursion', 'binary-tree'],
    summary: 'Solve a problem through smaller instances and navigate hierarchical data one branch at a time.',
    idea: 'Every recursive algorithm needs a reachable base case and progress toward it. Binary-search-tree traversal uses the same shape: compare, then recurse or move left/right.',
    code: `FUNCTION Factorial(Value : INTEGER) RETURNS INTEGER
  IF Value <= 1 THEN
    RETURN 1
  ENDIF
  RETURN Value * Factorial(Value - 1)
ENDFUNCTION

// Binary-search-tree lookup
Current ← RootPointer
Found ← FALSE
WHILE Current <> -1 AND NOT Found
  IF Tree[Current].Data = Target THEN
    Found ← TRUE
  ELSE
    IF Target < Tree[Current].Data THEN
      Current ← Tree[Current].LeftPointer
    ELSE
      Current ← Tree[Current].RightPointer
    ENDIF
  ENDIF
ENDWHILE`,
    pitfalls: ['No reachable base case', 'Recursive calls that do not shrink the problem', 'Discarding the return value from the recursive call'],
  },
  {
    id: 'testing-complexity',
    group: 'Algorithms',
    title: 'Testing, tracing & complexity',
    syllabusRef: '12.3 · 19.1',
    slugs: ['testing', 'error-correction', 'complexity'],
    summary: 'Prove an algorithm behaves at its boundaries, then compare how its cost grows with the input.',
    idea: 'Trace variable changes before running code. Test normal, abnormal, and boundary values. When two algorithms solve the same task, compare both time and space—such as O(n) linear search versus O(log n) binary search.',
    code: `Test 1 · normal    Target present in middle
Test 2 · boundary  Target at first/last index
Test 3 · abnormal  Empty or invalid input
Test 4 · negative  Target absent

Linear search  O(n)
Binary search  O(log n)
Bubble sort    O(n²)`,
    pitfalls: ['Testing only the happy path', 'Confusing a syntax error with a logic error', 'Comparing Big O without stating the input size being measured'],
  },
]

const groups = ['Foundations', 'Data structures', 'Algorithms']

const tagCounts = computed(() => {
  const counts = new Map()
  for (const record of records.value) {
    for (const tag of record.syllabus_tags || []) {
      counts.set(tag.slug, (counts.get(tag.slug) || 0) + 1)
    }
  }
  return counts
})

const selectionCount = computed(() => tagCounts.value.get('selection-if') || 0)
const selectionPercent = computed(() => (
  records.value.length ? Math.round((selectionCount.value / records.value.length) * 100) : 0
))

function questionCount(lesson) {
  return records.value.filter((record) => {
    const slugs = new Set((record.syllabus_tags || []).map((tag) => tag.slug))
    return lesson.slugs.some((slug) => slugs.has(slug))
  }).length
}

function practiceRoute(lesson) {
  return {
    name: 'problems',
    query: { tags: lesson.slugs.join(','), match: 'any' },
  }
}

onMounted(async () => {
  try {
    records.value = (await loadQuestionRecords()).records || []
  } catch {
    // Lessons remain fully usable offline; only corpus frequency badges disappear.
    records.value = []
  }
})
</script>

<template>
  <main class="learn-page" data-page="learn">
    <header class="learn-hero">
      <div>
        <h1>Learn the patterns.<br><span>Then recognise them.</span></h1>
        <p class="learn-intro">
          A focused field guide to the structures and methods that recur across the
          question corpus—plus the A Level ideas they lead into.
        </p>
      </div>
      <div v-if="records.length" class="frequency-card">
        <p class="frequency-note">Most frequent in this set</p>
        <strong>IF selection</strong>
        <span>{{ selectionCount }} of {{ records.length }} questions</span>
        <div class="frequency-bar"><i :style="{ width: `${selectionPercent}%` }"></i></div>
      </div>
      <div v-else class="frequency-card">
        <p class="frequency-note">Corpus snapshot</p>
        <strong>Lessons work offline</strong>
        <span>Matching-question counts appear when the corpus loads.</span>
      </div>
    </header>

    <nav class="lesson-index" aria-label="Lesson index">
      <RouterLink
        v-for="lesson in lessons"
        :key="lesson.id"
        :to="{ name: 'learn', hash: `#${lesson.id}` }"
      >
        {{ lesson.title }}
      </RouterLink>
    </nav>

    <section v-for="group in groups" :key="group" class="lesson-section">
      <div class="section-heading">
        <span>{{ String(groups.indexOf(group) + 1).padStart(2, '0') }}</span>
        <h2>{{ group }}</h2>
      </div>

      <div class="lesson-list">
        <details
          v-for="(lesson, index) in lessons.filter((item) => item.group === group)"
          :id="lesson.id"
          :key="lesson.id"
          class="lesson-card"
          :open="group === 'Foundations' && index === 0"
        >
          <summary>
            <div class="lesson-number">{{ String(lessons.indexOf(lesson) + 1).padStart(2, '0') }}</div>
            <div class="lesson-heading-copy">
              <div class="lesson-meta">
                <span>Syllabus {{ lesson.syllabusRef }}</span>
                <span v-if="questionCount(lesson)">{{ questionCount(lesson) }} matching questions</span>
                <span v-else>Core syllabus topic</span>
              </div>
              <h3>{{ lesson.title }}</h3>
              <p>{{ lesson.summary }}</p>
            </div>
            <span class="lesson-toggle" aria-hidden="true"></span>
          </summary>

          <div class="lesson-body">
            <div class="lesson-explanation">
              <h4>Key idea</h4>
              <p>{{ lesson.idea }}</p>
              <h4>Watch for</h4>
              <ul>
                <li v-for="pitfall in lesson.pitfalls" :key="pitfall">{{ pitfall }}</li>
              </ul>
              <RouterLink
                v-if="questionCount(lesson)"
                class="practice-link"
                :to="practiceRoute(lesson)"
              >
                Practice this topic <span aria-hidden="true">→</span>
              </RouterLink>
              <span v-else class="practice-unavailable">Syllabus extension · practice coming soon</span>
            </div>
            <pre class="lesson-code"><code>{{ lesson.code }}</code></pre>
          </div>
        </details>
      </div>
    </section>
  </main>
</template>
