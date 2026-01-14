Here’s a solid, “ship-able” implementation plan for **EN → PT live subtitles for OBS**, with a **toggle** and **whisper.cpp**.

## Goal

* User speaks into **mic**
* When **Translate Mode = ON**, show **Portuguese subtitles** in OBS
* When **OFF**, show nothing (or clear last subtitle)

---

## Architecture

### Processes / components

1. **App (your orchestrator)**

   * audio capture (mic)
   * VAD + chunker (decide when to transcribe / finalize)
   * calls `whisper.cpp` (CLI) for speech→text (English)
   * calls translator (EN→PT) for final text
   * hosts Overlay HTTP + WebSocket server
   * handles toggle (hotkey / control page button)

2. **whisper.cpp binary** (bundled)

   * input: short WAV chunk
   * output: transcript (JSON or plain text)

3. **Translator**

   * v1: cloud translation API (best quality, simplest), OR
   * offline translation (harder but fully local)

4. **OBS overlay**

   * Browser Source pointing to `http://127.0.0.1:<port>/overlay`
   * JS connects to WebSocket and renders subtitles

---

## Implementation plan (phased)

### Phase 0 — repo skeleton (clean separation)

```
app/
  core/
    config.py
    events.py          # subtitle event schema
    mode.py            # translate mode state machine
    segmenter.py       # VAD + chunking + finalization
  adapters/
    audio_mic.py       # mic capture
    whisper_runner.py  # subprocess wrapper
    translator.py      # cloud/offline interface
  server/
    overlay_server.py  # http + websocket
  ui/
    overlay.html
    overlay.js
    overlay.css
    control.html       # optional: start/stop toggle button
bin/
  whisper-macos
  whisper-windows.exe
models/
  ggml-small.en.bin
```

### Phase 1 — local transcription only (no translation yet)

**Target:** captions in English show in OBS overlay.

* Capture mic audio at e.g. **16kHz mono PCM**
* VAD: detect speech start/stop
* On speech end (silence > ~300–500ms), write the segment to a temp WAV
* Run:

  * `whisper` / `whisper.exe`
  * model = `small.en` (recommended)
  * force English language
  * output = JSON (easier to parse + timestamps)
* Emit a `final` subtitle event to overlay

**Acceptance criteria**

* Latency feels OK (phrase appears within ~0.5–2s after you finish talking)
* No flicker in overlay

### Phase 2 — add translation (EN → PT)

**Target:** overlay shows Portuguese.

* Keep whisper output in English
* Only translate **final segments** (avoid flicker)
* Add simple text hygiene:

  * trim whitespace
  * drop extremely short junk (“uh”, “hmm”) optionally
  * merge segments if they’re too short and close together

**Translator interface**

* `translate(text_en) -> text_pt`

**Acceptance criteria**

* Portuguese text looks reasonable
* No “rapid changing” subtitles

### Phase 3 — implement Toggle Mode (the core feature)

You want the behavior:

* Toggle OFF → do not show subtitles (clear overlay)
* Toggle ON → translate + show subtitles

Implementation detail:

* `mode.enabled: bool`
* Gate the pipeline:

  * if `enabled == False`:

    * either skip whisper calls entirely (best CPU savings), OR
    * run whisper but drop outputs (simpler if you don’t want to stop capture)
  * on transition OFF:

    * broadcast `{type:"clear"}` to overlay immediately

Control options (pick one for v1):

* **Control page**: `http://127.0.0.1:<port>/control` with a big ON/OFF button (super reliable)
* **Global hotkey**: `Ctrl+Alt+T` toggles mode (nice UX, slightly more OS-specific)

### Phase 4 — overlay polish (streamer quality)

Overlay logic:

* Maintain a rolling buffer of the last **1–2 lines**
* Fade out after **4–8 seconds**
* Big font, shadow, safe margins
* Optional “(EN→PT)” small indicator when enabled

### Phase 5 — packaging for end users (Windows)

* Bundle:

  * `YourApp.exe` (PyInstaller)
  * `bin/whisper-windows.exe`
  * `models/ggml-small.en.bin`
  * overlay assets
* First-run UX:

  * App shows:

    * status: “listening”
    * mode: ON/OFF
    * selected mic device
    * OBS Browser Source URL (copy button)

---

## Key engineering choices (so it doesn’t become a mess)

### 1) Use “final-only translation”

* whisper partials are unstable; translation amplifies instability
* translate only on VAD-finalized segments

### 2) Prefer sentence/phrase captions, not word-by-word

* chunking by silence is the simplest stable heuristic for streaming

### 3) Keep OS-specific code tiny

* mic capture + hotkey are the only parts that should diverge per OS

---

## Suggested default parameters (good starting point)

* Sample rate: **16 kHz**, mono
* Segment max length: **8–12s** (force finalize if someone keeps talking)
* Silence threshold: **300–500ms** to finalize
* Chunk overlap: optional, **200ms** (helps avoid cut words)
* Whisper model: **`small.en`**
* Subtitle TTL: **6s**

---

<!-- ## What you should decide now (but you can change later)

1. Translation: **cloud (simple/best)** vs **offline (harder/fully local)**
2. Toggle control: **control page** vs **global hotkey** (or both)

If you say “cloud translation is OK” + “hotkey toggle”, I’ll give you a concrete v1 spec with:

* exact CLI args for `whisper.cpp`
* event JSON schema (`partial`, `final`, `clear`)
* OBS overlay HTML/JS structure
* packaging checklist for Windows PyInstaller (including where to place `bin/` and `models/`) -->
