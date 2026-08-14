import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = REPO_ROOT / "src" / "website" / "frontend"
SRC = FRONTEND_ROOT / "src"
RECORDS = FRONTEND_ROOT / "public" / "resources" / "pseudocode_question_records.json"

NODE = shutil.which("node")


class TagUiWiringTests(unittest.TestCase):
    """Source-level wiring checks, matching the style of test_webapp."""

    def test_tag_components_exist(self):
        expected = [
            SRC / "services" / "tags.js",
            SRC / "components" / "TagChips.vue",
            SRC / "components" / "FilterPanel.vue",
        ]
        missing = [str(path) for path in expected if not path.is_file()]
        self.assertEqual(missing, [])

    def test_filter_panel_is_shared_by_both_list_surfaces(self):
        problems = (SRC / "views" / "ProblemsView.vue").read_text()
        explorer = (SRC / "components" / "ProblemExplorer.vue").read_text()
        for source in (problems, explorer):
            self.assertIn("FilterPanel", source)
            self.assertIn("filterRecords", source)
        self.assertIn('variant="page"', problems)
        self.assertIn('variant="compact"', explorer)
        # The bespoke per-view search predicates are gone; both go through the
        # shared service so search behaviour cannot drift between the two.
        self.assertNotIn("toLowerCase().includes", explorer)
        self.assertNotIn("toLowerCase().includes", problems)

    def test_problems_view_keeps_filter_state_in_the_url(self):
        problems = (SRC / "views" / "ProblemsView.vue").read_text()
        self.assertIn("useRoute", problems)
        self.assertIn("router.replace", problems)
        self.assertIn("tagsFromQueryParam", problems)
        self.assertIn("tagsToQueryParam", problems)

    def test_question_panel_hides_tags_behind_a_toggle(self):
        panel = (SRC / "components" / "QuestionPanel.vue").read_text()
        # Tags name the technique under assessment, so they stay opt-in next to
        # the context toggle rather than sitting open on an unattempted problem.
        self.assertIn("showTags", panel)
        self.assertIn("TagChips", panel)
        self.assertIn('v-if="showTags"', panel)
        # ...and this panel still must not leak the mark scheme.
        self.assertNotIn("marking_points", panel)
        self.assertNotIn("answer_text", panel)

    def test_chip_and_filter_styles_are_defined(self):
        css = (SRC / "assets" / "main.css").read_text()
        for selector in (".tag-chip", ".tag-chips", ".filter-panel", ".facet-group"):
            self.assertIn(selector, css)
        # Chips are buttons/links inside a global `button { min-height: 2rem }`
        # rule; without the reset they render as full-height controls.
        chip_block = css.split(".tag-chip {", 1)[1].split("}", 1)[0]
        self.assertIn("min-height: auto", chip_block)


@unittest.skipUnless(NODE, "node is required to exercise the tag filter module")
class TagFilterBehaviourTests(unittest.TestCase):
    """Run the real filter module against the real corpus under node."""

    @classmethod
    def setUpClass(cls):
        if not RECORDS.is_file():
            raise unittest.SkipTest("records resource has not been generated")
        harness = """
import { readFileSync } from 'node:fs'
const mod = await import(process.argv[2])
const records = JSON.parse(readFileSync(process.argv[3], 'utf8')).records
const {
  buildTagIndex, groupTagsBySection, filterRecords, facetCounts,
  parseQuery, tagsFromQueryParam, tagsToQueryParam, MATCH_ALL, MATCH_ANY,
} = mod
const index = buildTagIndex(records)
console.log(JSON.stringify({
  total: records.length,
  distinctTags: index.length,
  everyRecordTagged: records.every((r) => (r.syllabus_tags || []).length >= 4),
  sections: groupTagsBySection(index).map((g) => g.section),
  sectionsHaveLabels: groupTagsBySection(index).every((g) => Boolean(g.label)),
  noFilter: filterRecords(records, {}).length,
  anyMode: filterRecords(records, { tags: ['bubble-sort', 'adt-stack'], mode: MATCH_ANY }).length,
  allMode: filterRecords(records, { tags: ['bubble-sort', 'adt-stack'], mode: MATCH_ALL }).length,
  allCombo: filterRecords(records, { tags: ['text-files', 'records'], mode: MATCH_ALL }).map((r) => r.id),
  twoTerms: filterRecords(records, { query: 'bubble sort' }).length,
  phrase: parseQuery('"bubble sort" array'),
  terms: parseQuery('file   record'),
  searchAndTag: filterRecords(records, { query: '9618', tags: ['bubble-sort'] }).length,
  tagOnlySearch: filterRecords(records, { query: 'nonexistentzzz' }).length,
  facetTextFiles: facetCounts(records, '').get('text-files'),
  facetUnderQuery: facetCounts(records, 'recursionzzz').size,
  urlRound: tagsFromQueryParam(tagsToQueryParam(['a', 'b'])),
  urlEmpty: tagsToQueryParam([]) === undefined,
}))
"""
        cls._tmp = tempfile.TemporaryDirectory()
        script = Path(cls._tmp.name) / "harness.mjs"
        script.write_text(harness)
        completed = subprocess.run(
            [NODE, str(script), (SRC / "services" / "tags.js").as_uri(), str(RECORDS)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if completed.returncode != 0:
            raise AssertionError(f"tag harness failed: {completed.stderr}")
        cls.out = json.loads(completed.stdout)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_corpus_is_fully_tagged(self):
        self.assertEqual(self.out["total"], 176)
        self.assertTrue(self.out["everyRecordTagged"])
        self.assertEqual(self.out["distinctTags"], 32)

    def test_facets_group_into_labelled_syllabus_sections(self):
        # Sections come from the record payload, so the frontend needs no
        # syllabus knowledge; they must arrive in numeric order.
        self.assertEqual(self.out["sections"], ["6", "9", "10", "11", "12"])
        self.assertTrue(self.out["sectionsHaveLabels"])

    def test_empty_filter_returns_every_record(self):
        self.assertEqual(self.out["noFilter"], 176)

    def test_any_mode_is_a_union_and_all_mode_an_intersection(self):
        self.assertEqual(self.out["anyMode"], 7)
        # No question is both a bubble sort and a stack question.
        self.assertEqual(self.out["allMode"], 0)
        self.assertEqual(self.out["allCombo"], [175, 181])

    def test_search_requires_every_term_and_honours_quotes(self):
        self.assertEqual(self.out["terms"], ["file", "record"])
        self.assertEqual(self.out["phrase"], ["bubble sort", "array"])

    def test_search_matches_tag_labels(self):
        # "bubble sort" appears as a tag label; questions carrying it are found
        # even where the phrase is not in the question text.
        self.assertEqual(self.out["twoTerms"], 4)
        self.assertEqual(self.out["tagOnlySearch"], 0)

    def test_search_and_tags_narrow_together(self):
        self.assertEqual(self.out["searchAndTag"], 2)

    def test_facet_counts_follow_the_search(self):
        self.assertEqual(self.out["facetTextFiles"], 31)
        # A search matching nothing leaves every facet at zero.
        self.assertEqual(self.out["facetUnderQuery"], 0)

    def test_url_encoding_round_trips(self):
        self.assertEqual(self.out["urlRound"], ["a", "b"])
        self.assertTrue(self.out["urlEmpty"])


if __name__ == "__main__":
    unittest.main()
