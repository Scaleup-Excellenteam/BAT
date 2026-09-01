# Gemini voice input on Windows

Gemini is now the default voice provider. It transcribes a short WAV recording,
labels the transcript as AI-generated, and lets you accept, correct, or cancel
it before BAT searches. Typed search continues to work without an API key.

This option uses the Gemini Developer API with an AI Studio API key. It does
not use `gcloud`, Application Default Credentials, or the Cloud Speech-to-Text
API. The original Cloud Speech provider remains available explicitly.

## 1. Apply the update to your existing voice branch

If you already applied `voice-feature.patch`, put `gemini-voice.patch` inside
`C:\Users\haosz\BAT`. In VS Code's PowerShell terminal:

```powershell
cd C:\Users\haosz\BAT
git apply --check .\gemini-voice.patch
if ($LASTEXITCODE -eq 0) { git apply .\gemini-voice.patch }
```

Successful `git apply` normally prints nothing. Apply this update once. If the
check reports a conflict, stop and inspect the error; it may mean your files
changed since the first voice patch. Do not reapply the original patch. These
commands do not commit or push anything.

If you extracted the complete updated ZIP into a separate folder, its files
already contain this change, so skip applying both patches there.

## 2. Install and check dependencies

Your existing `.venv` can be reused:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

For Gemini usage without development tests, installing only
`requirements-gemini.txt` is enough. Use Python 3.10 or newer. Test requests
use an in-memory HTTP transport or mocks; they do not send audio to Google.

## 3. Create your own Gemini API key

1. Open [Google AI Studio API keys](https://aistudio.google.com/apikey).
2. Sign in and create an API key in a project available to your account.
3. For this free-tier setup, check that the project's tier is **Free tier**.
   If asked to upgrade or add billing, stop and check project/model availability
   with your mentor instead of upgrading.
4. Copy the key locally. Do not send it in chat, screenshots, or Git commits.

Google currently lists free-tier audio input and text output for
`gemini-2.5-flash`. Availability and quotas depend on the model, project, and
region. A key belonging to a paid-tier project may incur charges; BAT cannot
detect or enforce your project's billing tier. Free-tier submissions may be
used to improve Google's products, so use nonprivate demo speech.

In the same PowerShell terminal where you will run BAT, paste these commands:

```powershell
$voiceKey = Read-Host "Paste your Gemini API key" -AsSecureString
$env:GEMINI_API_KEY = [System.Net.NetworkCredential]::new("", $voiceKey).Password
Remove-Variable voiceKey
```

The first command prompts for your key without displaying it or placing it
in the command history. The environment variable is available to BAT launched
from this terminal. Repeat this step after opening a new terminal. BAT reads
`GEMINI_API_KEY` explicitly, so another feature's `GOOGLE_API_KEY` does not
silently change which key voice input uses. No key is written into a file.

## 4. Prepare a short recording

Record yourself saying **"to be or not to be"**. Export the recording as mono,
16-bit PCM WAV, 8,000-48,000 Hz, at most 60 seconds and 10 MB. 16,000 Hz is a
suitable demo setting. This version accepts a file; `/voice` does not open the
microphone automatically.

Renaming an M4A or MP3 file to `.wav` will not convert it. If FFmpeg is already
installed, convert a recording with:

```powershell
ffmpeg -i "recording.m4a" -ac 1 -ar 16000 -c:a pcm_s16le "query.wav"
```

## 5. Run and review

```powershell
.\.venv\Scripts\python.exe main.py --data-dir examples/corpus --voice-provider gemini
```

At the BAT prompt, enter `/voice`, then paste the path to your WAV recording.
Or provide the path directly, for example:

```text
/voice "C:\Users\haosz\BAT\query.wav"
```

BAT shows `Transcription provider: Gemini (AI-generated)` and the recognized
text. Press Enter to search it, type corrected text to search instead, or enter
`/cancel`. Only confirmed text reaches the search engine. Cancellation or
failure preserves the current query. Use `#` to reset and Ctrl+C to exit.

Omit `--data-dir examples/corpus` when you want to search your existing
`Archive` folder. The sample archive includes a Hamlet sentence, making the
spoken phrase above useful for a first test.

English is the default language hint. `--voice-language he-IL` or
`--voice-language ar-IL` supplies another hint; Gemini is instructed to preserve
the spoken language. This feature does not translate or generate completions.
Use English speech for the English demo corpus until translation is connected.

## Provider and model selection

The default model is `gemini-2.5-flash`. If that model is unavailable in your
project, choose an accessible audio-input, text-output model that supports JSON
structured output, and verify its tier/quotas first. For example:

```powershell
.\.venv\Scripts\python.exe main.py --data-dir examples/corpus --voice-model gemini-2.5-flash-lite
```

There is no automatic fallback to another model, provider, or paid tier.
To use the original Cloud Speech-to-Text implementation:

```powershell
.\.venv\Scripts\python.exe main.py --voice-provider cloud-speech
```

That provider still needs the separate setup in [VOICE_SETUP.md](VOICE_SETUP.md).

## Troubleshooting

| Message | Next step |
| --- | --- |
| Set GEMINI_API_KEY | Repeat step 3 in the terminal that launches BAT. |
| Gemini dependencies are missing | Install `requirements-gemini.txt` using BAT's `.venv` Python. |
| Gemini denied access / rejected request | Check that your key is valid for the Gemini Developer API, its project access, and region availability in AI Studio. |
| Model is unavailable | Check the chosen model ID and access; use `--voice-model` if needed. |
| Quota exhausted or unavailable | Check AI Studio limits. Wait for a quota reset or use typed search. Creating another key does not reset project quotas. |
| No speech recognized | Record clearer speech, choose the right language hint, or type the query. |
| Invalid / incomplete transcript | Retry with a shorter, clearer recording. BAT rejects malformed or truncated responses before review. |
| Timeout / unavailable | Check connectivity or use typed input. Requests have a 20-second SDK timeout and no automatic retries. |
| Invalid WAV | Export actual mono PCM16 WAV; changing the filename extension is insufficient. |

SDK timeouts govern network operations, not a guaranteed total wall-clock
deadline. Client initialization and processing can add time. Live transcription
quality still needs testing with your own recordings; a model can mishear or
invent words, especially in silence/noise. Always review the transcript.

## Official documentation

- [Gemini audio input](https://ai.google.dev/gemini-api/docs/audio)
- [Gemini 2.5 Flash capabilities](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash)
- [API keys](https://ai.google.dev/gemini-api/docs/api-key)
- [Pricing and free-tier data use](https://ai.google.dev/gemini-api/docs/pricing)
- [Billing tiers](https://ai.google.dev/gemini-api/docs/billing)
- [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
