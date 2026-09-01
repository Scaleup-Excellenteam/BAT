# Validation and demonstration

## Automated checks

Run `python -m pytest -q` after installing `requirements-dev.txt`. All network
calls in the tests are mocked. Gemini tests run the real SDK over an in-memory
HTTP transport to check request serialization and error handling. Test WAV files contain synthetic silence and
are generated in temporary directories; they are never uploaded.

The tests cover:

- Existing index, normalization, exact/fuzzy retrieval, and integration checks.
- Part A reference scores through the real search/ranking pipeline.
- Google SDK request serialization, true WAV sample rate, language selection,
  segment joining, RPC timeout, and disabled retries.
- Invalid formats, oversized files, excessive duration, missing/unreadable
  files, truncated audio, and empty recordings.
- No transcript, malformed responses, missing credentials/dependencies,
  permission errors, exhausted quota, timeout, and service failure.
- Transcript acceptance, correction, cancellation, and interruption.
- Gemini inline WAV encoding, JSON schema, language hint, API key header,
  model choice, request timeout, and no retries on quota/server failures.
- Missing Gemini key/dependency, blocked or truncated model output, invalid
  JSON, wrong transcript types, blank output, and model-unavailable responses.
- Explicit Gemini key selection without ADC fallback; AI-generated labeling
  and cold-start typed search with no installed third-party packages.
- Identical archive results and scores for the same confirmed typed/voice text.
- Retaining the current query after cancellation or failure, and starting a
  new query after voice confirmation.

These are implementation checks. They do not establish live transcription
accuracy, cloud permissions, or a measured improvement in user input time.

## Live demonstration on your PC

Complete [Gemini setup](GEMINI_VOICE_SETUP.md), or the optional Cloud Speech
setup in [VOICE_SETUP.md](VOICE_SETUP.md), and use the included
`examples/corpus` archive. Record your own nonprivate examples as mono PCM WAV.
The scenarios below are a plan for live validation, not claimed API outputs.

| Scenario | Action | Expected behavior |
| --- | --- | --- |
| Clear speech | Say "to be or not to be" and accept the transcript. | Search the confirmed text and show the Hamlet source line. |
| Correction | Say "to pe", then enter "to be" at the review prompt. | Search the corrected query; its exact-match score is 10. |
| Cancel | Start with typed `to `, invoke voice, cancel, then type `be`. | The resulting query is `to be`. |
| Silence | Submit a recording containing no speech. | Explain that no speech was recognized if Google returns no transcript. If Gemini invents text, record this as a failed recognition and cancel. |
| Invalid file | Select a text file renamed to `.wav`. | Reject locally before making a service call. |
| Service problem | Demonstrate an error with the mocked test, without intentionally spending quota. | Explain the error and allow typed search. |

Use at least five clear recordings and a few noisy/accented examples. Keep a
reference transcript for each and record the displayed transcription time.
For accuracy, record the number of examples whose transcript can be accepted
without correction. This yields a simple acceptance rate:

`accepted_without_edit / total_recordings`

Report that rate alongside median transcription time. Count a timeout or empty
transcript as unsuccessful rather than silently excluding it. Also compare
typing the same final query: archive results, file locations, and scores should
be identical. Do not expect identical recognition wording on every run.

| Recording | Reference text | Actual transcript | Accepted without edit? | Time (seconds) |
| --- | --- | --- | --- | --- |
| 1 | Fill after recording | Not measured | Not measured | Not measured |
| 2 | Fill after recording | Not measured | Not measured | Not measured |
| 3 | Fill after recording | Not measured | Not measured | Not measured |
| 4 | Fill after recording | Not measured | Not measured | Not measured |
| 5 | Fill after recording | Not measured | Not measured | Not measured |

## Using the changes with your team

The ZIP is an updated snapshot of the supplied BAT source, not a checkout of
your teammates' latest branches. Test it in a separate folder first. Merge the
voice changes into your working branch and review overlaps in `cli/main.py`
with the translation/completion teammates. A new download does not update your
GitHub repository automatically. Do not replace a newer team checkout blindly.
