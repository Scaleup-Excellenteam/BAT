# BAT Autocomplete Project 
# 🔍 BAT - Fast Autocomplete Search Engine

An efficient sentence autocomplete system in Python capable of finding substring matches across large text corpora with error tolerance (up to 1 edit: substitution, insertion, or deletion).

## Voice input (Part B)

Use `/voice` to transcribe a WAV recording with Gemini, review or edit the
AI-generated transcript, and search the existing archive. Google Cloud
Speech-to-Text is also available with `--voice-provider cloud-speech`.
No cloud packages or credentials are needed for basic typed search.

```bash
python main.py --data-dir examples/corpus
```

Use `python main.py` for your own `Archive` directory. Voice transcription
with Gemini requires `requirements-gemini.txt` and a `GEMINI_API_KEY` from
Google AI Studio. Use a free-tier project for free-tier testing; model access
and quotas apply. It accepts mono, 16-bit PCM WAV recordings
of at most 60 seconds and 10 MB.

- [Gemini Windows setup and incremental patch instructions](docs/GEMINI_VOICE_SETUP.md)
- [Optional Cloud Speech-to-Text setup](docs/VOICE_SETUP.md)
- [Feature design and teammate integration](docs/VOICE_DESIGN.md)
- [Tests and live demonstration](docs/VOICE_VALIDATION.md)

```text
/voice "C:\Users\Aws\Recordings\query.wav"
```

After the transcript appears, press Enter to search, type corrected text, or
enter `/cancel`. Confirming starts a new query; cancelling or a failure keeps
the current query. Additional typed input extends the confirmed query.

To run all automated tests (Python 3.10+):

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Verified locally: 114 tests and 8 subtests passed with Python 3.12,
google-genai 1.75.0, google-cloud-speech 2.40.0, and pytest 9.1.1. Tests exercise
both providers with real SDK types and mocked network responses; they do not
require keys or billing. Live recognition requires access to the chosen
service and has not been measured here.

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
- **Punctuation:** ASCII punctuation is replaced with spaces.
- **Whitespace collapse:** Multiple consecutive whitespaces are collapsed into a single space.
- *Note:* Returned output retains original casing and punctuation and the file location; leading/trailing whitespace is trimmed when reading lines.

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
- Query `"2o be"` $\rightarrow$ Score: **3** ($(2 \times 4) - 5$, substituted at pos 1)
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
```

Voice input adds `services/speech.py`, `cli/voice.py`, two voice test modules,
optional dependency files, a small `examples/corpus` directory, and the three
documents linked above. Scoring regression tests now cover the actual handoff
from search candidates to ranked results.
