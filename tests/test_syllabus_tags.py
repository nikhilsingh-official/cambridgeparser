import json
import unittest
from pathlib import Path

from src.pipeline.pseudocode_tools import syllabus_tags
from src.pipeline.pseudocode_tools.question_tag_assignments import (
    _TAGS,
    tagged_segment_count,
    tags_for_segment,
)
from src.resources.paths import PSEUDOCODE_QUESTION_RECORDS_JSON


REPO_ROOT = Path(__file__).resolve().parents[1]
# The canonical records still live at the legacy root-level path in this
# checkout; fall back to it when the generated tree has not been built.
RECORDS_CANDIDATES = (
    PSEUDOCODE_QUESTION_RECORDS_JSON,
    REPO_ROOT / "pseudocode_writing_hits/pseudocode_question_records.json",
)


def load_records():
    for path in RECORDS_CANDIDATES:
        if path.is_file():
            return json.loads(path.read_text())["records"]
    return None


class SyllabusTagVocabularyTest(unittest.TestCase):
    def test_slugs_are_unique_and_kebab_case(self):
        slugs = [tag.slug for tag in syllabus_tags.TAGS_BY_SLUG.values()]
        self.assertEqual(len(slugs), len(set(slugs)))
        for slug in slugs:
            self.assertRegex(slug, r"^[a-z0-9]+(-[a-z0-9]+)*$")

    def test_every_tag_cites_a_syllabus_subsection(self):
        for tag in syllabus_tags.TAGS_BY_SLUG.values():
            self.assertRegex(tag.syllabus_ref, r"^\d+\.\d+( / \d+\.\d+)?$", tag.slug)
            self.assertTrue(tag.label.strip(), tag.slug)
            self.assertTrue(tag.description.strip(), tag.slug)

    def test_describe_expands_a_slug(self):
        payload = syllabus_tags.describe("bubble-sort")
        self.assertEqual(payload["slug"], "bubble-sort")
        self.assertEqual(payload["syllabus_ref"], "10.2 / 19.1")

    def test_validate_rejects_unknown_slug(self):
        with self.assertRaises(ValueError):
            syllabus_tags.validate_tags(["arrays-1d", "functions", "nope", "records"])

    def test_validate_rejects_duplicates(self):
        with self.assertRaises(ValueError):
            syllabus_tags.validate_tags(
                ["arrays-1d", "arrays-1d", "functions", "records"]
            )

    def test_validate_enforces_tag_count(self):
        with self.assertRaises(ValueError):
            syllabus_tags.validate_tags(["arrays-1d", "functions", "records"])
        with self.assertRaises(ValueError):
            syllabus_tags.validate_tags(
                [
                    "arrays-1d",
                    "functions",
                    "records",
                    "procedures",
                    "parameters",
                    "text-files",
                ]
            )


class QuestionTagAssignmentTest(unittest.TestCase):
    def test_every_assignment_is_valid(self):
        for key, slugs in _TAGS.items():
            syllabus_tags.validate_tags(list(slugs), context=f"segment {key}")

    def test_lookup_returns_tags_for_a_known_segment(self):
        # 9608_s16_qp_21 Q2(b): write pseudocode from a structured English
        # description that inputs values and sets an alarm flag.
        self.assertEqual(
            tags_for_segment("9608_s16_qp_21", "2", "(b)", None),
            [
                "structured-english",
                "input-output",
                "selection-if",
                "variables-constants",
                "operators-expressions",
            ],
        )

    def test_lookup_returns_empty_for_an_untagged_segment(self):
        self.assertEqual(tags_for_segment("9618_s99_qp_99", "1", None, None), [])

    def test_every_vocabulary_tag_is_used(self):
        used = {slug for slugs in _TAGS.values() for slug in slugs}
        unused = sorted(syllabus_tags.VALID_SLUGS - used)
        # A tag nobody uses is dead vocabulary; drop it or tag the question that
        # needs it. A-Level-only topics absent from the pseudocode-writing
        # corpus are listed here deliberately.
        expected_unused = sorted(
            [
                "abstraction",
                "adt-queue",
                "adt-linked-list",
                "binary-search",
                "binary-tree",
                "complexity",
                "declarative-programming",
                "dictionary",
                "encapsulation",
                "exception-handling",
                "file-organisation",
                "graphs",
                "hashing",
                "inheritance",
                "insertion-sort",
                "low-level-programming",
                "oop-classes",
                "polymorphism",
                "recursion",
                "state-transition",
                "testing",
                "user-defined-types",
                "file-processing",
            ]
        )
        self.assertEqual(unused, expected_unused)


class TaggedRecordsTest(unittest.TestCase):
    def setUp(self):
        self.records = load_records()
        if self.records is None:
            self.skipTest("canonical records file has not been generated")

    def test_every_record_carries_tags(self):
        untagged = [r["id"] for r in self.records if not r.get("syllabus_tags")]
        self.assertEqual(untagged, [])

    def test_assignments_cover_exactly_the_corpus(self):
        duplicate_source_count = sum(
            len((record.get("provenance") or {}).get("duplicate_sources") or [])
            for record in self.records
        )
        self.assertEqual(
            tagged_segment_count(), len(self.records) + duplicate_source_count
        )

    def test_record_tags_are_expanded_and_valid(self):
        for record in self.records:
            slugs = [tag["slug"] for tag in record["syllabus_tags"]]
            syllabus_tags.validate_tags(slugs, context=f"record {record['id']}")
            for tag in record["syllabus_tags"]:
                self.assertEqual(tag, syllabus_tags.describe(tag["slug"]))


if __name__ == "__main__":
    unittest.main()
