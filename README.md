# BAT Autocomplete Project 
# 🔍 BAT - Fast Autocomplete Search Engine

An efficient sentence autocomplete system in Python capable of finding substring matches across large text corpora with error tolerance (up to 1 edit: substitution, insertion, or deletion).

---

## 📌 Project Overview & System Workflow
The project operates in two distinct phases:
1. **Offline Phase (Initialization & Indexing):** 
   - Recursively traverses an archive of text files.
   - Reads, cleans, normalizes sentences, and builds high-performance lookup indexes in memory.
2. **Online Phase (Interactive Querying):** 
   - Accepts real-time user query strings via CLI.
   - Evaluates exact and 1-edit fuzzy matches across sentences.
   - Computes score penalties according to strict rules.
   - Returns the top 5 completions ordered by highest score (and lexicographically on ties).
   - Allows query expansion until `#` is typed to reset.

---

## ⚙️ Text Normalization Rules
Before indexing or searching, every sentence and search query undergoes normalization:
- **Case insensitive:** Lowercased (`A-Z` $\rightarrow$ `a-z`).
- **Punctuation removal:** All punctuation marks are stripped.
- **Whitespace collapse:** Multiple consecutive whitespaces are collapsed into a single space.
- *Note:* Returned output retains the **original verbatim sentence** and file location.

---

## 🧮 Scoring & Penalty Specifications

$$\text{Score} = (2 \times \text{matching\_chars}) - \text{penalty}$$

- Only correctly matched characters contribute $+2$ each.
- Penalties depend on the 1-based index ($k$) in the normalized query:

| Character Position ($k$) | Substitution Penalty | Insertion / Deletion Penalty |
| :---: | :---: | :---: |
| **1** | -5 | -10 |
| **2** | -4 | -8 |
| **3** | -3 | -6 |
| **4** | -2 | -4 |
| **5+** | -1 | -2 |

### Reference Examples (Sentence: `"To be or not to be, that is the question."`)
- Query `"To be"` $\rightarrow$ Score: **10** ($2 \times 5 - 0$)
- Query `"or Not"` $\rightarrow$ Score: **12** ($2 \times 6 - 0$)
- Query `"20 be"` $\rightarrow$ Score: **3** ($(2 \times 4) - 5$, substituted at pos 1)
- Query `"to pe"` $\rightarrow$ Score: **6** ($(2 \times 4) - 2$, substituted at pos 4)
- Query `"or knot"` $\rightarrow$ Score: **8** ($(2 \times 6) - 4$, extra 'k' at pos 4 deleted)
- Query `"or nt"` $\rightarrow$ Score: **8** ($(2 \times 5) - 2$, missing 'o' at pos 5 inserted)

---

## 🏗️ Architecture & Project Structure

```text
BAT/
├── core/
│   ├── __init__.py
│   ├── models.py          # Data definitions (AutoCompleteData, SentenceRecord)
│   ├── normalizer.py      # Normalization logic
│   ├── indexer.py         # Offline file loading and N-gram inverted indexing
│   ├── generator.py       # 1-edit variations generation (sub, del, ins)
│   ├── scoring.py         # Scoring and penalty evaluator
│   └── search_engine.py   # Online query coordinator (combines exact + fuzzy)
├── cli/
│   ├── __init__.py
│   └── main.py            # CLI user interface & interactive loop
├── tests/
│   ├── test_normalizer.py
│   ├── test_scoring.py
│   └── test_search.py
└── README.md



