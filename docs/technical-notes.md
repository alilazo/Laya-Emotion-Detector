# Emotion Constellation

A standalone local showcase for independent linguistic emotion signals. This project has no CareForge application code or integration. The UI offers chats, three live conversation gauges, and a triangular map of saved chat histories.

## Run locally on Windows

Requires Node.js, `uv`, Python 3.11 or newer, and a running Ollama server with `lfm2.5-8b-a1b:32k` for chat and `qwen3.6-35b-a3b:ud-iq3-s` for emotion evidence checks. Follow the [README model setup](../README.md) to download and create these profiles. Check names with `ollama list`; set `OLLAMA_MODEL` or `EMOTION_VERIFIER_MODEL` in `.env` if yours differs. Ollama's OpenAI-compatible endpoint defaults to `http://127.0.0.1:11434/v1`. The first startup downloads the selected Laya checkpoint from Hugging Face; later runs use the local cache. Laya is approximately 421 million parameters. Use one backend worker to preserve message ordering.

```powershell
git clone https://github.com/alilazo/Laya-Emotion-Detector.git
cd Laya-Emotion-Detector
uv venv .venv-local
uv pip install --python .venv-local\Scripts\python.exe -r backend\requirements-dev.txt
cd frontend
npm install
npm run build
cd ..
.\run.ps1
```

Open the local URL printed by the server. It contains a newly generated access key, which the app saves for the current browser session. The server binds only to `127.0.0.1`. Set `LOCAL_ACCESS_TOKEN` if you want a stable key. Keep the URL private. API routes holding chats and analytics require the key.

Copy `.env.example` to `.env` to change checkpoint, device, thresholds, Ollama endpoint/model/timeout, or the access key. `run.ps1` loads that file when present. Ollama runs separately from this app; start its server before sending messages.

A fresh clone creates an empty SQLite database; local conversation data is not published. The optional seed command adds **12 illustrative chats** for demonstrating the map. They are marked “Illustrative,” are read only, and were not produced by Laya. To use a clean database, set `EMOTION_DB_PATH` to a new path before starting. To add the samples to another database, run:

```powershell
.\.venv-local\Scripts\python.exe -m backend.app.seed --database .\data\another.sqlite3
```

To use a CUDA-capable PyTorch install, install the appropriate PyTorch build into `.venv-local` and set `LAYA_DEVICE=cuda`. The environment built for this showcase uses CPU. `LAYA_CHECKPOINT=english` selects the other evaluated checkpoint. `LAYA_ENABLED=0` keeps chat usable but marks emotion inference unavailable.

## Architecture

Chat history has an X beside each conversation, with an inline confirmation. Deleting a chat also deletes its messages, emotion snapshots, and archived snapshots; the request waits for any active reply to finish. Compact history supports keyboard focus, Escape dismissal, and inline retry feedback. Subtle control and disclosure motion respects reduced-motion preferences.

- **Backend:** FastAPI in `backend/app`, SQLite in `data/showcase.sqlite3`, versioned schema in `db.py` (`PRAGMA user_version=3`). A new database is created automatically. The schema does not modify other projects or databases.
- **Emotion scoring:** `EmotionModel` loads one resident Laya checkpoint at startup and performs an optional warm-up. One `agent.predict(state, EMOTION_QUESTIONS)` call scores anxiety, sadness, and fear together. A separate local Ollama evidence check looks at the current user message first and assigns an independent 0–4 supported level for each emotion. Laya's raw scores remain in snapshots; unsupported emotions become zero, and positive Laya scores are bounded by the supported level. This `emotion-v2-evidence` pipeline keeps the raw and corrected values for audit. A missing or invalid evidence response marks scoring unavailable rather than using inflated raw scores.
- **Chat:** `OllamaChatModel` calls `POST /v1/chat/completions` with the configured `lfm2.5-8b-a1b:32k` model and recent user/assistant turns. It keeps at most 24 recent messages and 48,000 history characters. The backend consumes the model's stream, then returns the completed reply to the UI. Structured reasoning or leading `<think>…</think>` blocks are saved separately and shown in a collapsed Thinking disclosure above the answer. Thinking time measures the observed interval from the first reasoning output to the first answer output; total response time is also saved separately. Existing tagged replies are parsed on read, with no invented historical timing. Assistant reasoning is excluded from subsequent chat context. An optimistic bubble and composing indicator appear while the request runs. Only a completed, nonempty answer becomes an assistant message. If Ollama fails, the user message and any Laya snapshot remain saved, and the UI reports the error.
- **Ordering:** A per-chat asynchronous lock covers Laya inference, Ollama generation, and persistence. Run one backend worker. Assistant messages are never scored. Laya's recent role-tagged context is bounded to approximately 650 estimated tokens, with the current user message preserved first and both ends retained when it is long. Previous gauges never enter Laya state.
- **Scores:** Corrected raw intensity is multiplied by 25 for the 0–100 instant signal. The first successful message sets its conversation gauge to the instant value. A newly expressed strong signal also rises immediately from zero. Other increases use alpha .55 (or .70 for a large high spike); decreases use .12. Emotions update independently.
- **Persistence:** Each successfully analyzed user message has one active snapshot with Laya raw, corrected instant, before and after gauge values, checkpoint, prompt version, probability distributions, evidence metadata, and timestamp. Chat `current` is the latest gauge; `peak` is the maximum after-gauge; `average` is the arithmetic mean of after-gauges. Recalculation archives earlier snapshots in `emotion_snapshot_history` and writes a SQLite backup before replacing active snapshots. On model failure, the message is marked `unavailable`, no snapshot is fabricated, and the current gauge remains unchanged.
- **Analytics:** The summary API loads chat summaries only. The selected chat timeline is fetched separately. For display mode Final, Peak, or Average, position weights divide each independent signal by their sum. A neutral node uses the triangle center. Node size uses `sqrt((A²+S²+F²)/3)` with a 6–18 px radius. Fill uses the dominant signal. Mixed means at least two signals are ≥60. Low signal means all three are <25; the neutral center rule uses <10. Thresholds are visualization rules, never medical cutoffs.
- **Filters:** Final/Peak/Average, date presets or custom range, minimum score sliders, high-signal presets, mixed, low, dominant emotion, and title search. Header statistics follow the date range. Constellation filters affect nodes only. Hover/focus, click, zoom, pan, reset, and a selected-chat timeline are available.
- **Frontend:** React, TypeScript, custom SVG, and CSS in `frontend/src`. The frontend build is served by FastAPI at the same origin.

## Evaluation

`backend/evaluation/emotion_cases.json` contains 50 deterministic **illustrative, non-clinical** cases covering neutral text, each emotion, mixtures, negation, attribution, quoted speech, context leakage, ambiguous wording, and long text. Compare checkpoints with the configured local evidence model:

```powershell
.\.venv-local\Scripts\python.exe backend\evaluation\evaluate_models.py --checkpoint both --device cpu
```

The initial run on this machine (50 cases, CPU) produced:

| Checkpoint | Anxiety MAE | Sadness MAE | Fear MAE | Macro MAE | Neutral false-positive rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| typed-decisions | 1.514 | 1.735 | 1.631 | 1.627 | 1.00 |
| english | 1.457 | 1.619 | 1.693 | 1.589 | 1.00 |
| typed-decisions + Qwen evidence check | 0.416 | 0.161 | 0.217 | 0.265 | 0.00 |

The original raw Laya scores failed all neutral cases at the evaluator's ≥1 raw-score false-positive rule. The corrected scores passed those cases in this run. The dataset is small, authored, and non-clinical; it is a regression aid, not a validated benchmark. **These emotion scores are not suitable for health decisions.**

To recalculate live chats after a scoring version changes, stop the server and run:

```powershell
.\.venv-local\Scripts\python.exe backend\evaluation\rescore_chats.py
```

This creates a SQLite backup in `data/`, archives earlier snapshot rows, and updates live chat gauges and timelines in one transaction. Illustrative sample chats are left as authored. Re-running it with the same scoring version makes no further changes.

## Checks

```powershell
.\.venv-local\Scripts\python.exe -m ruff check backend
.\.venv-local\Scripts\python.exe -m ruff format --check backend
.\.venv-local\Scripts\python.exe -m pytest -q
cd frontend
npm run build
npm run lint
npm test
```

The app is a local single-user showcase. Live chats use Ollama for assistant replies; the 12 illustrative sample chats remain read only and use authored example replies. It does not provide multi-user accounts, clinical interpretation, or longitudinal calibration. Laya download requires network on first use; inference remains local after download. A CPU-only run may take longer per message than the model's published GPU timing. Chat replies are currently non-streaming, and a missing Ollama reply is reported without fabricating assistant text.
