"""Corpus indexer using k-mers inverted index with fast disk caching."""

import os
import pickle
from typing import Dict, List, Optional, Set

from core.models import SentenceRecord
from core.normalizer import normalize_text

CACHE_FILE_NAME = "lexical_index.pkl"


class DataManager:
    def __init__(self, kmer_size: int = 4, cache_file: str = CACHE_FILE_NAME):
        # רשימה מרכזית של כל המשפטים. האינדקס ברשימה הוא ה-sentence_id
        self.sentences: List[SentenceRecord] = []
        
        # Inverted Index: ממפה תת-מחרוזת באורך kmer_size לקבוצה של sentence_ids
        self.index: Dict[str, Set[int]] = {}
        
        self.kmer_size = kmer_size
        self.cache_file = cache_file

    def load_data(self, root_dir: str) -> None:
        """
        טוען את האינדקס מקובץ Cache קיים (במידה וקיים).
        אם אינו קיים, סורק את התיקייה, בונה את האינדקס ושומר לקובץ Cache.
        """
        if not os.path.exists(root_dir) and not os.path.exists(self.cache_file):
            raise FileNotFoundError(f"Directory '{root_dir}' does not exist.")

        # ניסיון טעינה מהירה מתוך ה-Cache
        if os.path.exists(self.cache_file):
            if self._load_from_cache():
                print(f"[DataManager] Loaded {len(self.sentences):,} sentences instantly from cache '{self.cache_file}'.")
                return

        print(f"[DataManager] Building index from '{root_dir}'...")
        sentence_counter = 0

        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                if filename.endswith(".txt"):
                    file_path = os.path.join(dirpath, filename)
                    
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_number, line in enumerate(f, start=1):
                            original_line = line.strip()
                            
                            # דילוג על שורות ריקות
                            if not original_line:
                                continue
                            
                            norm_line = normalize_text(original_line)
                            if not norm_line:
                                continue

                            record = SentenceRecord(
                                sentence_id=sentence_counter,
                                original_text=original_line,
                                normalized_text=norm_line,
                                source_path=file_path,
                                offset=line_number,
                            )
                            self.sentences.append(record)
                            
                            # אינדוקס המשפט
                            self._index_sentence(sentence_counter, norm_line)
                            sentence_counter += 1

        # שמירה לקובץ Cache להרצות הבאות
        self._save_to_cache()

    def _index_sentence(self, sentence_id: int, normalized_text: str) -> None:
        """
        מפרק את הטקסט המנורמל לכל תתי-המחרוזות באורך kmer_size ומוסיף לאינדקס.
        """
        text_len = len(normalized_text)
        
        # אם המשפט קצר מ-kmer_size, מאנדקסים את המשפט המלא
        if text_len < self.kmer_size:
            if normalized_text not in self.index:
                self.index[normalized_text] = set()
            self.index[normalized_text].add(sentence_id)
            return

        for i in range(text_len - self.kmer_size + 1):
            sub = normalized_text[i : i + self.kmer_size]
            if sub not in self.index:
                self.index[sub] = set()
            self.index[sub].add(sentence_id)

    def _save_to_cache(self) -> None:
        """שומר את מבני הנתונים לקובץ בינארי בדיסק."""
        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump(
                    {
                        "sentences": self.sentences,
                        "index": self.index,
                        "kmer_size": self.kmer_size,
                    },
                    f,
                    protocol=pickle.HIGHEST_PROTOCOL,
                )
            print(f"[DataManager] Successfully saved index cache ({len(self.sentences):,} sentences).")
        except Exception as err:
            print(f"[DataManager Warning] Failed to save cache: {err}")

    def _load_from_cache(self) -> bool:
        """טוען את מבני הנתונים ישירות מהקובץ."""
        try:
            with open(self.cache_file, "rb") as f:
                data = pickle.load(f)
                self.sentences = data.get("sentences", [])
                self.index = data.get("index", {})
                self.kmer_size = data.get("kmer_size", self.kmer_size)
                return True
        except Exception:
            return False

    def get_candidate_ids(self, query: str) -> Set[int]:
        """
        מחזיר קבוצה של sentence_ids שעשויים להכיל את השאילתה.
        """
        if not query:
            return set()

        # אם השאילתה קצרה מ-kmer_size, נחפש מפתחות שמכילים את השאילתה
        if len(query) < self.kmer_size:
            candidates: Set[int] = set()
            for key, ids in self.index.items():
                if query in key:
                    candidates.update(ids)
            return candidates

        # אם השאילתה שווה או ארוכה מ-kmer_size, שולפים לפי 4 התווים הראשונים
        first_kmer = query[: self.kmer_size]
        return self.index.get(first_kmer, set()).copy()

    def get_sentence(self, sentence_id: int) -> Optional[SentenceRecord]:
        """
        שליפת פרטי משפט לפי מזהה ב-O(1).
        """
        if 0 <= sentence_id < len(self.sentences):
            return self.sentences[sentence_id]
        return None