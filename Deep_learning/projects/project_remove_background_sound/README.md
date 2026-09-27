# 🎙️ AI Audio Cleaner for YouTube Videos

Automatically removes breathing sounds, background hiss, and noise from MP4 files using a multi-stage AI pipeline.

---

## Pipeline

```
FFmpeg → DeepFilterNet3 (AI) → Silero VAD (AI) → Pedalboard EQ → FFmpeg
```

| Stage | Tool | Purpose |
|---|---|---|
| 1 | FFmpeg | Extract audio from MP4 |
| 2 | DeepFilterNet3 | Remove background hiss and noise |
| 3 | Silero VAD | Detect speech, suppress breathing gaps |
| 4 | Pedalboard | EQ + compression for YouTube quality |
| 5 | FFmpeg | Merge clean audio back into video |

---

## Requirements

- Python 3.11
- FFmpeg (added to system PATH)

---

## Installation

```bash
pip install deepfilternet
pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cpu
pip install soundfile
pip install silero-vad
pip install pedalboard
pip install numpy
```

Install FFmpeg (Windows):
```bash
winget install Gyan.FFmpeg
```

---

## Usage

Place your video in the project folder and run:

```bash
python main.py
```

Input and output filenames are set at the bottom of `main.py`:

```python
clean_video_audio("my_video.mp4", "my_video_clean.mp4")
```

---

## Key Tuning Parameters

### Breathing removal (`remove_breathing_with_vad`)

| Parameter | Default | Effect |
|---|---|---|
| `threshold` | `0.65` | Higher = stricter speech detection, more breathing removed |
| `min_silence_ms` | `80` | Lower = catches shorter breath gaps |
| `speech_pad_ms` | `30` | Lower = tighter boundary around words |
| `breath_gain` | `0.05` | `0.0` = silent, `0.1` = faint — how loud suppressed breaths are |

### Voice EQ (`apply_pedalboard_eq`)

| Parameter | Default | Effect |
|---|---|---|
| `LowShelfFilter gain_db` | `+4` | Higher = deeper/warmer voice |
| `PeakFilter gain_db` | `+3` | Higher = more voice clarity |
| `HighShelfFilter gain_db` | `-3` | Lower = less sibilance and hiss |
| `Compressor ratio` | `3` | Higher = more even volume |

---

## Output

- Video stream is copied as-is (no quality loss)
- Audio exported as AAC 320kbps
- Console prints a breathing correction report showing every gap removed

---

## Notes

- Runs fully on CPU — no GPU required
- A 5-minute video takes roughly 1–3 minutes to process
- Run the script twice on the same file for a second pass of breathing removal
- For best results, also position your mic slightly off-axis from your mouth