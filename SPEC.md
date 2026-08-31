# 📋 System Architecture & Specification Document (BAT Project)

## 1. System Overview
The project is a high-performance **Sentence Autocomplete Engine** in Python capable of indexing large collections of text files and returning the top 5 sentence completions for user queries in real-time. The engine supports exact substring matching as well as error-tolerant matching with at most one edit (substitution, insertion, or deletion).

---

## 2. Core Execution Phases

### Phase 1: Offline Initialization & Indexing
- **Input:** A root directory path containing an archive of `.txt` files arranged in arbitrary folder depths.
- **Processing:**
  - Recursively traverse all `.txt` files.
  - Read every non-empty line as an independent sentence.
  - Normalize each sentence[cite: 1].
  - Store sentence records (original text, normalized text, file path, line offset)[cite: 1].
  - Build an in-memory Inverted Index / K-mer map mapping substrings to `sentence_id` sets for fast candidate retrieval[cite: 1].

### Phase 2: Online Serving & Query Processing
- **Input:** Interactive user query strings via CLI[cite: 1].
- **Matching Rules:**
  - Substring matching anywhere in the sentence (start, middle, or end)[cite: 1].
  - At most **1 edit** allowed per match:
    1. **Exact Match:** No edit[cite: 1].
    2. **Substitution:** One character replaced[cite: 1].
    3. **Insertion:** Missing character added to query[cite: 1].
    4. **Deletion:** Extra character removed from query[cite: 1].
- **Output:** Top 5 `AutoCompleteData` objects sorted by descending score[cite: 1]. Ties are resolved lexicographically by the completed sentence[cite: 1].
- **Session Control:** The user can continue typing to narrow down suggestions; entering `#` resets the search session[cite: 1].

---

## 3. Text Normalization Rules
Applied consistently to both corpus sentences and search queries[cite: 1]:
1. **Case:** Convert to lowercase[cite: 1].
2. **Punctuation:** Strip all punctuation marks[cite: 1].
3. **Whitespace:** Collapse consecutive whitespace characters into a single space, and strip leading/trailing spaces[cite: 1].
4. **Verbatim Preservation:** Output returned to the user must preserve the **original casing, punctuation, and structure**[cite: 1].

---

## 4. Scoring & Penalty Rules

$$\text{Score} = (2 \times \text{matching\_chars}) - \text{penalty}$$
[cite: 1]

- Only matching characters earn $+2$ points each (inserted, deleted, or substituted characters earn 0)[cite: 1].
- Penalty lookup based on the 1-based character position in the normalized query[cite: 1]:

| Character Position ($k$) | Substitution Penalty | Insertion / Deletion Penalty |
| :---: | :---: | :---: |
| **1** | -5 | -10[cite: 1] |
| **2** | -4 | -8[cite: 1] |
| **3** | -3 | -6[cite: 1] |
| **4** | -2 | -4[cite: 1] |
| **5+** | -1 | -2[cite: 1] |

---

## 5. Shared Interfaces & Data Structures

### `core/models.py`
```python
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
    