from dataclasses import dataclass
from typing import List

@dataclass
class AutoCompleteData:
    completed_sentence: str
    source_text: str
    offset: int
    score: int

@dataclass
class SentenceRecord:
    sentence_id: int
    original_text: str
    normalized_text: str
    source_path: str
    offset: int