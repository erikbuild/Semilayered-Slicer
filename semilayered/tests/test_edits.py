# ABOUTME: Tests for explicit edits: exact replacements that refuse to guess when upstream's text has changed.
# ABOUTME: Covers applying, failing loudly on a mismatch, and leaving an already-applied edit alone.
import unittest

from semilayered.rebrand.edits import Edit, EditMismatch, Substitution, apply_edit, substitute


class ApplyEditTest(unittest.TestCase):
    def test_replaces_the_expected_number_of_occurrences(self):
        self.assertEqual(apply_edit("a x b x c", Edit("f.cpp", "x", "y", count=2)), "a y b y c")

    def test_missing_text_fails_naming_the_entry(self):
        with self.assertRaises(EditMismatch) as caught:
            apply_edit("abc", Edit("f.cpp", "x", "y", reason="why"))
        message = str(caught.exception)
        self.assertIn("f.cpp", message)
        self.assertIn("why", message)
        self.assertIn("found 0", message)

    def test_text_occurring_more_often_than_expected_fails(self):
        with self.assertRaises(EditMismatch) as caught:
            apply_edit("x x", Edit("f.cpp", "x", "y"))
        self.assertIn("found 2", str(caught.exception))

    def test_already_applied_edit_is_left_alone(self):
        self.assertEqual(apply_edit("a y b", Edit("f.cpp", "x", "y")), "a y b")

    def test_insertion_is_not_applied_twice(self):
        edit = Edit("f.cpp", "void f()\n{", "void f()\n{\n    return;")
        once = apply_edit("void f()\n{\n}", edit)
        self.assertEqual(once, "void f()\n{\n    return;\n}")
        self.assertEqual(apply_edit(once, edit), once)

    def test_half_applied_edit_fails(self):
        with self.assertRaises(EditMismatch):
            apply_edit("x y", Edit("f.cpp", "x", "y", count=2))

    def test_old_text_beside_text_that_already_reads_as_edited_fails(self):
        with self.assertRaises(EditMismatch):
            apply_edit("x y", Edit("f.cpp", "x", "y"))

    def test_edit_whose_new_text_is_part_of_the_old_is_rejected(self):
        with self.assertRaises(ValueError):
            Edit("f.cpp", "keep and drop", "keep")

    def test_edit_to_nothing_is_rejected(self):
        with self.assertRaises(ValueError):
            Edit("f.cpp", "drop", "")


class SubstituteTest(unittest.TestCase):
    def test_replaces_every_occurrence_and_counts_them(self):
        self.assertEqual(substitute("a b a", Substitution("a", "c")), ("c b c", 2))

    def test_text_without_the_old_form_is_unchanged(self):
        self.assertEqual(substitute("b b", Substitution("a", "c")), ("b b", 0))

    def test_substitution_that_would_grow_on_every_run_is_rejected(self):
        with self.assertRaises(ValueError):
            Substitution("a", "aa")


if __name__ == "__main__":
    unittest.main()
