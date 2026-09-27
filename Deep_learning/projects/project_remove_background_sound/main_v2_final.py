# FFmpeg            → extract audio
# DeepFilterNet3    → remove background hiss/noise
# Silero VAD (AI)   → detect speech vs non-speech frames
#                     silence out breathing gaps precisely
# Pedalboard        → EQ + compress for YouTube quality
# FFmpeg            → merge back into video

import subprocess
import os
import sys
import numpy as np
import soundfile as sf
import torch

def remove_breathing_with_vad(input_wav, output_wav):
    from silero_vad import load_silero_vad, get_speech_timestamps

    # ── TUNING ────────────────────────────────────────────────────
    # threshold      → 0.3 = catches more speech (less aggressive)
    #                  0.6 = stricter speech detection (more aggressive)
    # min_silence_ms → gaps shorter than this are NOT silenced
    #                  (avoids cutting mid-word pauses)
    # speech_pad_ms  → extend each speech segment by this much on each side
    #                  increase if words are getting clipped at edges
    # noise_floor    → volume of non-speech parts (0.0 = dead silent)
    #                  0.0001 = barely audible (recommended for YouTube)
    #                  0.001  = very faint
    #                  0.01   = audible background hum
    # ─────────────────────────────────────────────────────────────
    
    # threshold      = 0.4
    # min_silence_ms = 150    # lowered so short breathing gaps get caught
    # speech_pad_ms  = 80     # wider padding so word edges aren't clipped
    # fade_ms        = 30     # smooth fade to avoid clicks
    # noise_floor    = 0.0001 # barely audible — adjust this to taste


    threshold      = 0.65
    min_silence_ms = 80    # lowered so short breathing gaps get caught
    speech_pad_ms  = 30     # wider padding so word edges aren't clipped
    fade_ms        = 30     # smooth fade to avoid clicks
    noise_floor    = 0.00005 # barely audible — adjust this to taste



    print(f"  VAD settings: threshold={threshold}, min_silence={min_silence_ms}ms, pad={speech_pad_ms}ms")

    # Load audio
    audio_data, sr = sf.read(input_wav)
    if audio_data.ndim > 1:
        audio_data = audio_data[:, 0]

    import torchaudio
    wav_tensor = torch.FloatTensor(audio_data).unsqueeze(0)
    wav_16k = torchaudio.functional.resample(wav_tensor, sr, 16000) if sr != 16000 else wav_tensor

    # Load Silero VAD and get speech timestamps
    model = load_silero_vad()
    speech_timestamps = get_speech_timestamps(
        wav_16k.squeeze(),
        model,
        sampling_rate=16000,
        threshold=threshold,
        min_silence_duration_ms=min_silence_ms,
        speech_pad_ms=speech_pad_ms,
    )

    if not speech_timestamps:
        print("  WARNING: No speech detected! Saving original.")
        sf.write(output_wav, audio_data, sr)
        return 0

    # ── BUILD SPEECH MASK ─────────────────────────────────────────
    # True  = speech  → keep at full volume
    # False = non-speech → reduce to noise_floor (barely audible)
    scale = sr / 16000
    mask  = np.zeros(len(audio_data), dtype=bool)

    for seg in speech_timestamps:
        start = int(seg['start'] * scale)
        end   = int(seg['end']   * scale)
        # clamp to array bounds
        start = max(0, start)
        end   = min(len(audio_data), end)
        mask[start:end] = True

    # ── COUNT BREATHING GAPS ──────────────────────────────────────
    breathing_gaps = []
    for i in range(len(speech_timestamps) - 1):
        gap_start_ms = round(speech_timestamps[i]['end']     / 16000 * scale / sr * 1000, 1)
        gap_end_ms   = round(speech_timestamps[i+1]['start'] / 16000 * scale / sr * 1000, 1)
        dur_ms       = round((speech_timestamps[i+1]['start'] - speech_timestamps[i]['end']) / 16000 * 1000, 1)
        breathing_gaps.append({
            'index'      : i + 1,
            'start_sec'  : round(speech_timestamps[i]['end']     / 16000, 2),
            'end_sec'    : round(speech_timestamps[i+1]['start'] / 16000, 2),
            'duration_ms': dur_ms,
        })

    # Check for breathing before first word
    first_start = int(speech_timestamps[0]['start'] * scale)
    if first_start > int(0.05 * sr):
        breathing_gaps.insert(0, {
            'index'      : 0,
            'start_sec'  : 0.0,
            'end_sec'    : round(first_start / sr, 2),
            'duration_ms': round(first_start / sr * 1000, 1),
            'note'       : 'before first word',
        })

    # ── PRINT REPORT ─────────────────────────────────────────────
    print(f"\n  ── Breathing Correction Report ──────────────────────")
    print(f"  Speech segments found       : {len(speech_timestamps)}")
    print(f"  Breathing gaps suppressed   : {len(breathing_gaps)}")
    print(f"\n  {'#':<5} {'Start':>8} {'End':>8} {'Duration':>12} {'Note'}")
    print(f"  {'─'*5} {'─'*8} {'─'*8} {'─'*12} {'─'*20}")
    for gap in breathing_gaps:
        print(f"  {gap['index']:<5} {gap['start_sec']:>7.2f}s "
              f"{gap['end_sec']:>7.2f}s {gap['duration_ms']:>10.1f}ms  "
              f"{gap.get('note', '')}")

    total_ms = sum(g['duration_ms'] for g in breathing_gaps)
    print(f"\n  Total breathing suppressed  : {total_ms/1000:.2f}s")
    print(f"  Non-speech volume level     : {noise_floor} (noise floor)")
    print(f"  ─────────────────────────────────────────────────────\n")

    # ── APPLY: speech = full volume, non-speech = barely audible ──
    result     = audio_data.copy().astype(np.float64)
    non_speech = ~mask

    # Replace non-speech with extremely quiet random noise
    # This sounds more natural than dead silence on YouTube
    # Replace your current masking line with:
    # Modified on 2026-06-25- TODO Fix this...lil buggyyyyy    
    breath_gain = 0.05  # tweak this: 0.0 = silent, 0.1 = very faint
    result[~mask] *= breath_gain
    # Remove the np.random.normal line entirely
    
    # result[non_speech] = np.random.normal(0, noise_floor, np.sum(non_speech))

    # ── SMOOTH FADES at speech boundaries (avoid clicks) ──────────
    fade_samples = int(fade_ms * sr / 1000)
    fade_in      = np.linspace(0, 1, fade_samples)
    fade_out     = np.linspace(1, 0, fade_samples)

    transitions = np.where(np.diff(mask.astype(int)))[0]
    for t in transitions:
        if mask[t + 1]:  # speech starting — fade in
            end_idx = min(t + 1 + fade_samples, len(result))
            length  = end_idx - (t + 1)
            result[t+1 : end_idx] *= fade_in[:length]
        else:            # speech ending — fade out
            start_idx = max(t + 1 - fade_samples, 0)
            length    = (t + 1) - start_idx
            result[start_idx : t+1] *= fade_out[fade_samples - length:]

    # Normalize to prevent clipping
    max_val = np.max(np.abs(result))
    if max_val > 0:
        result = result / max_val * 0.95

    sf.write(output_wav, result.astype(np.float32), sr)
    print(f"  Audio saved → {output_wav}")

    return len(breathing_gaps)


def apply_pedalboard_eq(input_wav, output_wav):
    from pedalboard import (
        Pedalboard, HighpassFilter, LowpassFilter,
        LowShelfFilter, PeakFilter, HighShelfFilter,
        Compressor, Gain
    )

    from pedalboard.io import AudioFile

    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=80),
        LowpassFilter(cutoff_frequency_hz=14000),
        LowShelfFilter(cutoff_frequency_hz=180, gain_db=4.0),
        PeakFilter(cutoff_frequency_hz=3000, gain_db=3.0, q=1.0),
        HighShelfFilter(cutoff_frequency_hz=8000, gain_db=-3.0),
        Compressor(threshold_db=-20, ratio=3, attack_ms=5.0, release_ms=50.0),
        Gain(gain_db=2),
    ])

    with AudioFile(input_wav) as f:
        audio = f.read(f.frames)
        sr    = f.samplerate

    effected = board(audio, sr)

    with AudioFile(output_wav, 'w', sr, effected.shape[0]) as f:
        f.write(effected)
    print(f"  EQ applied → {output_wav}")


def clean_video_audio(input_mp4, output_mp4):
    if not os.path.exists(input_mp4):
        print(f"ERROR: Input file not found: {input_mp4}")
        sys.exit(1)

    base        = os.path.splitext(input_mp4)[0]
    raw_audio   = base + "_raw.wav"
    vad_audio   = base + "_vad.wav"
    eq_audio    = base + "_eq.wav"
    out_dir     = "out"
    os.makedirs(out_dir, exist_ok=True)

    for f in os.listdir(out_dir):
        if f.endswith(".wav"):
            os.remove(os.path.join(out_dir, f))

    # STEP 1: Extract audio
    print(f"\n[1/5] Extracting audio from {input_mp4}...")
    subprocess.run([
        "ffmpeg", "-i", input_mp4,
        "-ar", "48000", "-ac", "1",
        raw_audio, "-y"
    ], check=True)

    # STEP 2: DeepFilterNet3 — background noise/hiss removal
    print("\n[2/5] DeepFilterNet3 — removing background noise/hiss...")
    subprocess.run([
        "deepFilter", raw_audio,
        "--output-dir", out_dir,
        "--pf",
    ], check=True)

    out_files = [f for f in os.listdir(out_dir) if f.endswith(".wav")]
    if not out_files:
        print("ERROR: No WAV found in out/")
        sys.exit(1)
    enhanced_audio = os.path.join(out_dir, out_files[0])
    print(f"  DeepFilterNet output: {enhanced_audio}")

    # STEP 3: Silero VAD — breathing/silence removal
    print("\n[3/5] Silero VAD — detecting and removing breathing sounds...")
    breathing_count = remove_breathing_with_vad(enhanced_audio, vad_audio)
    
    # STEP 4: Pedalboard EQ
    print("\n[4/5] Pedalboard — EQ + compression...")
    apply_pedalboard_eq(vad_audio, eq_audio)

    # Safety fallback
    final_audio = eq_audio
    if not os.path.exists(eq_audio) or os.path.getsize(eq_audio) < 1000:
        print("WARNING: EQ failed, using VAD audio directly.")
        final_audio = vad_audio

    # STEP 5: Merge back into video
    print(f"\n[5/5] Merging into {output_mp4}...")
    subprocess.run([
        "ffmpeg",
        "-i", input_mp4,
        "-i", final_audio,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "320k",
        "-map", "0:v:0",
        "-map", "1:a:0",
        output_mp4, "-y"
    ], check=True)

    for tmp in [raw_audio, enhanced_audio, vad_audio, eq_audio]:
        if os.path.exists(tmp):
            os.remove(tmp)

    print(f"\n✓ Done! Saved to: {output_mp4}")
    print(f"  Breathing corrections : {breathing_count}")
    print(f"  Pipeline: DeepFilterNet3 → Silero VAD → Pedalboard EQ → AAC 320k")
    
    
if __name__ == "__main__":
    # clean_video_audio("my_video.mp4", "my_video_clean.mp4")

    # Check if the user forgot to provide a filename
    if len(sys.argv) < 2:
        print("Error: Please provide an input video file.")
        print("Usage: python script.py my_video.mp4")
        sys.exit(1)
        
    # Get the input filename from the command line argument
    user_input = sys.argv[1]
    
    # Separate the filename from its extension (e.g., 'my_video' and '.mp4')
    file_name, file_extension = os.path.splitext(user_input)
    
    # Automatically create the output name with '_clean' appended
    output_name = f"{file_name}_clean{file_extension}"
    
    # Run your cleaning function
    clean_video_audio(user_input, output_name)
