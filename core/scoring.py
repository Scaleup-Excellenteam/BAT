"""Scoring and candidate ranking for auto-complete queries."""

from typing import Callable, Iterable, List, Optional
from core.models import AutoCompleteData, SentenceRecord

# טבלאות קנסות
SUBSTITUTION_PENALTIES = {1: 5, 2: 4, 3: 3, 4: 2}
INSERT_DELETE_PENALTIES = {1: 10, 2: 8, 3: 6, 4: 4}


def get_penalty(error_type: Optional[str], error_index: Optional[int]) -> int:
    """מחזיר את ערך הקנס בהתאם לסוג השגיאה ולמיקומה (1-based index)."""
    if not error_type or error_index is None:
        return 0

    err = error_type.upper()
    if err == "SUBSTITUTION":
        return SUBSTITUTION_PENALTIES.get(error_index, 1)
    if err in ("INSERTION", "DELETION"):
        return INSERT_DELETE_PENALTIES.get(error_index, 2)
    return 0


def calculate_score(query_len: int, error_type: Optional[str], error_index: Optional[int]) -> int:
    """מחשב ציון לפי הנוסחה: (matching_chars * 2) - penalty."""
    if not error_type:
        return query_len * 2
    
    matching_chars = max(0, query_len - 1)
    penalty = get_penalty(error_type, error_index)
    return (matching_chars * 2) - penalty


def rank_candidates(
    normalized_query: str,
    matches: Iterable,
    get_sentence: Callable,
    top_k: int = 5,
) -> List[AutoCompleteData]:
    """מדרג מועמדים, מסנן כפילויות ומחזיר את k התוצאות הטובות ביותר."""
    best_results = {}
    query_len = len(normalized_query)

    for match in matches:
        # בדיקה אם המאצ' מחזיק כבר את הרשומה או מזהה
        item = getattr(match, "sentence", None)
        if item is None:
            item = getattr(match, "sentence_id", None)

        # אם קיבלנו כבר SentenceRecord ישירות
        if isinstance(item, SentenceRecord):
            record = item
        elif isinstance(item, int):
            record = get_sentence(item)
        else:
            continue

        if not record:
            continue

        error_type = getattr(match, "error_type", None)
        error_index = getattr(match, "error_index", None)

        score = calculate_score(query_len, error_type, error_index)

        # סינון כפילויות ושמירת הציון הגבוה ביותר
        if (
            record.original_text not in best_results
            or score > best_results[record.original_text].score
        ):
            best_results[record.original_text] = AutoCompleteData(
                completed_sentence=record.original_text,
                source_text=record.source_path,
                offset=record.offset,
                score=score,
            )

    # מיון לפי ציון יורד ובמקרה שוויון לפי סדר אלפביתי
    sorted_items = sorted(
        best_results.values(),
        key=lambda x: (-x.score, x.completed_sentence),
    )

    return sorted_items[:top_k]