# FFmpeg (DSP)          → extract audio
# DeepFilterNet3 (AI)   → remove noise/breathing using neural network
# FFmpeg (DSP)          → EQ + compress + shape the sound
# FFmpeg (DSP)          → merge back into video


import subprocess
import os
import shutil
import sys

def clean_video_audio(input_mp4, output_mp4):
    if not os.path.exists(input_mp4):
        print(f"ERROR: Input file not found: {input_mp4}")
        sys.exit(1)

    base = os.path.splitext(input_mp4)[0]
    raw_audio = base + "_raw.wav"
    out_dir = "out"
    os.makedirs(out_dir, exist_ok=True)

    # Clean out_dir before processing so we don't pick up old files
    for f in os.listdir(out_dir):
        if f.endswith(".wav"):
            os.remove(os.path.join(out_dir, f))

    print(f"\n[1/3] Extracting audio from {input_mp4}...")
    subprocess.run([
        "ffmpeg", "-i", input_mp4,
        "-ar", "48000",
        "-ac", "1",
        raw_audio, "-y"
    ], check=True)

    print("\n[2/3] Running DeepFilterNet3 noise removal...")
    subprocess.run([
        "deepFilter", raw_audio,
        "--output-dir", out_dir
    ], check=True)

    # Auto-find whatever file DeepFilterNet created
    out_files = [f for f in os.listdir(out_dir) if f.endswith(".wav")]
    if not out_files:
        print(f"ERROR: No WAV file found in {out_dir}/")
        sys.exit(1)
    enhanced_audio = os.path.join(out_dir, out_files[0])
    print(f"  Found enhanced audio: {enhanced_audio}")

    print(f"\n[3/3] Merging clean audio back into video -> {output_mp4}...")
    subprocess.run([
        "ffmpeg",
        "-i", input_mp4,
        "-i", enhanced_audio,
        "-c:v", "copy",        # no video re-encoding = no quality loss
        "-c:a", "aac",
        "-b:a", "192k",
        "-map", "0:v:0",
        "-map", "1:a:0",
        output_mp4, "-y"
    ], check=True)

    # Cleanup temp files
    os.remove(raw_audio)
    os.remove(enhanced_audio)

    print(f"\n✓ Done! Clean video saved to: {output_mp4}")

if __name__ == "__main__":
    clean_video_audio("my_video.mp4", "my_video_clean.mp4")