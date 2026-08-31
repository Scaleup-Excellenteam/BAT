import unittest
from core.normalizer import normalize_text

class TestNormalizer(unittest.TestCase):
    def test_lowercase(self):
        self.assertEqual(normalize_text("Hello World"), "hello world")

    def test_punctuation_removal(self):
        self.assertEqual(
            normalize_text("To be or not to be, that is the question."),
            "to be or not to be that is the question"
        )
        self.assertEqual(normalize_text("be, that"), "be that")

    def test_consecutive_spaces_and_tabs(self):
        self.assertEqual(normalize_text("  this    is   a    demo  "), "this is a demo")
        self.assertEqual(normalize_text("alpha\t\tbeta\ngamma"), "alpha beta gamma")

    def test_empty_and_whitespace_only(self):
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text("     "), "")

if __name__ == "__main__":
    unittest.main()