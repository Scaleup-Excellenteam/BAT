# Voice search setup

This page covers the optional **Cloud Speech-to-Text** provider. Gemini is now
the default; for Gemini API keys and free-tier setup, use
[GEMINI_VOICE_SETUP.md](GEMINI_VOICE_SETUP.md).

BAT can transcribe a short WAV recording with Google Cloud Speech-to-Text V1,
let you review or correct the transcript, then search the archive. Voice input
starts a new query after confirmation. Cancelling or a failed request keeps
your current query. Typed search remains available without Google packages.

## 1. Install the Python dependencies

Use Python 3.10 or newer. In a terminal opened in the BAT project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
```

Using the virtual environment's Python directly avoids PowerShell activation
policy issues. On macOS/Linux, use `.venv/bin/python` instead.

## 2. Set up Google Cloud access

Use a Google Cloud project approved by your mentors. Confirm the current
Speech-to-Text pricing and project quotas before using live transcription.
The assignment requires coordinating paid usage with your mentors. A Gemini
API key from a teammate is not the authentication used by this adapter.

Install the [Google Cloud CLI](https://docs.cloud.google.com/sdk/docs/install).
Replace `YOUR_PROJECT_ID` in these commands with the approved project ID:

```powershell
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable speech.googleapis.com
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

The project must have billing enabled and the signed-in account must have
permission to use Speech-to-Text and consume the project's quota. Ask your
mentor/project administrator to configure access if enabling the API or
setting the quota project is denied.

The Python SDK uses Application Default Credentials (ADC). The commands above
store credentials outside the repository. Do not paste tokens, credentials,
or access keys into source files or commit them. If your environment already
sets `GOOGLE_APPLICATION_CREDENTIALS`, that file takes precedence over local
ADC; ensure it points to the intended valid credentials.

Relevant official documentation:

- [Speech-to-Text V1 authentication](https://docs.cloud.google.com/speech-to-text/docs/v1/authentication)
- [Short audio recognition](https://docs.cloud.google.com/speech-to-text/docs/v1/sync-recognize)
- [Limits and quotas](https://docs.cloud.google.com/speech-to-text/docs/v1/quotas)
- [Pricing](https://cloud.google.com/speech-to-text/pricing)

## 3. Prepare a recording

This first version accepts files, not direct microphone capture. Record a
short phrase using your preferred recorder and export it as:

- WAV container with uncompressed, 16-bit PCM audio.
- One channel (mono).
- A sample rate between 8,000 and 48,000 Hz; 16,000 Hz is a suitable demo choice.
- At most 60 seconds and 10 MB.

Renaming `.m4a` or `.mp3` to `.wav` does not convert it. If FFmpeg is already
installed, this command converts a recording to the supported format:

```powershell
ffmpeg -i "recording.m4a" -ac 1 -ar 16000 -c:a pcm_s16le "query.wav"
```

Audio is sent to Google when you invoke voice input and select the file.
Use your own nonprivate demo speech. BAT does not save additional audio copies
or transcript logs; the original recording remains where you placed it.

## 4. Run the feature

For the included small text corpus:

```powershell
.\.venv\Scripts\python.exe main.py --data-dir examples/corpus --voice-provider cloud-speech
```

Omit `--data-dir` to use your existing `Archive` folder; keep
`--voice-provider cloud-speech` to select this provider.
The original large archive is not included in the project ZIP.

At the BAT prompt, enter:

```text
/voice
```

Paste the path to the WAV file. Windows paths with spaces and surrounding
quotes are supported. You can also provide the path in the command:

```text
/voice "C:\Users\Aws\Recordings\query.wav"
```

BAT displays the transcript and transcription time. Press Enter to search
that transcript, type a corrected query to search instead, or enter `/cancel`.
After a successful voice query, additional typed text extends that query,
just like the basic autocomplete session. Enter `#` to reset the session.

English (`en-US`) is the default speech language. A different supported
Speech-to-Text V1 language can be selected at startup:

```powershell
.\.venv\Scripts\python.exe main.py --voice-provider cloud-speech --voice-language he-IL
```

Check the [V1 supported language list](https://docs.cloud.google.com/speech-to-text/docs/v1/speech-to-text-supported-languages)
for the language/model combination you intend to use. This flag changes
recognition language only. This feature does not translate text. Until the
teammate's translation feature is connected, use English recordings for an
English archive.

## 5. Run tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The suite uses mocked Google clients and real SDK message types. It does not
make cloud requests, require credentials, or incur recognition charges.
See [VOICE_VALIDATION.md](VOICE_VALIDATION.md) for the live demonstration and
the distinction between offline test evidence and measured speech accuracy.

## Troubleshooting

| Message | Action |
| --- | --- |
| Voice dependencies are missing | Install `requirements-voice.txt` using the same Python that runs BAT. |
| Credentials are missing or expired | Complete the ADC commands above. |
| Google denied access | Check the enabled API, billing, and account permissions with your mentor. |
| Speech quota is exhausted | Check the project's quota; typed search remains available. |
| Transcription timed out / service unavailable | Check connectivity or use typed input. The recognition RPC has a 20-second timeout and no automatic retries. |
| Invalid WAV / unsupported format | Export actual mono, 16-bit PCM WAV audio. |
| No speech was recognized | Use a clearer recording and the correct language, or type the query. |

Transcription time is measured inside the adapter, including client creation
when needed and recognition. The RPC timeout is not a total application timer;
SDK imports and credential discovery/refresh may take additional time.
