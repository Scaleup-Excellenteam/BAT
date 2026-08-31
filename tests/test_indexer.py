import os
import shutil
import tempfile
import unittest
from core.indexer import DataManager


class TestIndexer(unittest.TestCase):
    def setUp(self):
        # יצירת תיקייה זמנית עם קובצי טקסט לבדיקה
        self.test_dir = tempfile.mkdtemp()
        
        # קובץ 1
        file1_path = os.path.join(self.test_dir, "file1.txt")
        with open(file1_path, "w", encoding="utf-8") as f:
            f.write("To be or not to be, that is the question.\n")
            f.write("Alpha: this is a demo.\n")

        # קובץ 2 בתוך תת-תיקייה
        sub_dir = os.path.join(self.test_dir, "subdir")
        os.makedirs(sub_dir)
        file2_path = os.path.join(sub_dir, "file2.txt")
        with open(file2_path, "w", encoding="utf-8") as f:
            f.write("Beta: this is a demo.\n")

        self.data_manager = DataManager(kmer_size=4)
        self.data_manager.load_data(self.test_dir)

    def tearDown(self):
        # מחיקת התיקייה הזמנית בסיום
        shutil.rmtree(self.test_dir)

    def test_sentences_loaded_count(self):
        self.assertEqual(len(self.data_manager.sentences), 3)

    def test_sentence_attributes(self):
        first_sentence = self.data_manager.get_sentence(0)
        self.assertIsNotNone(first_sentence)
        self.assertEqual(first_sentence.original_text, "To be or not to be, that is the question.")
        self.assertEqual(first_sentence.normalized_text, "to be or not to be that is the question")
        self.assertEqual(first_sentence.offset, 1)

    def test_candidate_retrieval(self):
        # "this" מופיע גם במשפט 1 וגם במשפט 2
        candidates = self.data_manager.get_candidate_ids("this")
        self.assertIn(1, candidates)
        self.assertIn(2, candidates)
        self.assertNotIn(0, candidates)

    def test_candidate_retrieval_short_query(self):
        # שאילתה קצרה מ-4 תווים (למשל "to")
        candidates = self.data_manager.get_candidate_ids("to")
        self.assertIn(0, candidates)


if __name__ == "__main__":
    unittest.main()