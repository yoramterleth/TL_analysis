# %% [markdown]
# # Video compressor
# Re-encodes a video to H.264 to shrink it for sharing.
# Two modes:
#   - "target_size": two-pass encode that lands near a chosen MB size (for upload/email caps)
#   - "crf":         single-pass quality-based encode (best quality per byte, size not guaranteed)
#
# Requires ffmpeg + ffprobe on PATH. Check with `ffmpeg -version` in a terminal.
# On Windows: install from https://www.gyan.dev/ffmpeg/builds/ and add the bin folder to PATH.

# %%
import os
import re
import sys
import shutil
import subprocess
from pathlib import Path

# %% [markdown]
# ## Configuration

# %%
INPUT   = Path(r".\WEST_BEACH_CANON.mp4")
OUTPUT  = None            # None -> alongside input as *_compressed.mp4

MODE    = "target_size"   # "target_size" or "crf"

# --- target_size mode ---
TARGET_SIZE_MB = 50      # aim for this output size. Email ~20-25, Slack ~1GB, WeTransfer huge.
SIZE_HEADROOM  = 0.95     # aim for 95% of target so muxing overhead doesn't push it over

# --- crf mode ---
CRF = 26                  # 18=near-lossless/big, 23=high, 26=smaller, 30-32=aggressive

# --- shared knobs ---
PRESET      = "slow"      # slower = better compression per byte: ultrafast..veryslow
SCALE_WIDTH = None        # e.g. 1280 to downscale (huge size lever, keeps aspect). None = keep size
FPS         = None        # e.g. 15 to drop frame rate. None = keep as-is
KEEP_AUDIO  = True        # timelapses usually have none anyway

# %% [markdown]
# ## Helpers

# %%
NULL_DEVICE = "NUL" if os.name == "nt" else "/dev/null"
PASS_LOG    = "ffmpeg2pass"   # temp log prefix for two-pass


def _require(tool):
    if shutil.which(tool) is None:
        sys.exit(f"'{tool}' not found on PATH. Install ffmpeg and reopen your terminal/kernel.")


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        sys.exit(f"Could not read duration from {path}:\n{out.stderr}")


def has_audio(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    return "audio" in out.stdout


def build_filters():
    vf = []
    if SCALE_WIDTH:
        vf.append(f"scale={int(SCALE_WIDTH)}:-2")   # -2 keeps aspect, forces even height
    if FPS:
        vf.append(f"fps={FPS}")
    return ["-vf", ",".join(vf)] if vf else []


def audio_args(path):
    if KEEP_AUDIO and has_audio(path):
        return ["-c:a", "aac", "-b:a", "128k"]
    return ["-an"]


def run(cmd):
    print("  $", " ".join(str(c) for c in cmd))
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        # ffmpeg prints progress + errors to stderr; show the tail so failures are legible
        sys.exit("ffmpeg failed:\n" + "\n".join(p.stderr.strip().splitlines()[-15:]))


def cleanup_pass_logs():
    for f in Path(".").glob(PASS_LOG + "*"):
        try:
            f.unlink()
        except OSError:
            pass

# %% [markdown]
# ## Encode

# %%
_require("ffmpeg")
_require("ffprobe")

inp = INPUT
if not inp.exists():
    sys.exit(f"Input not found: {inp}")

out = Path(OUTPUT) if OUTPUT else inp.with_name(inp.stem + "_compressed.mp4")
vf  = build_filters()
aud = audio_args(inp)
size_in = inp.stat().st_size

print(f"Input : {inp.name}  ({size_in/1e6:.0f} MB)")
print(f"Output: {out.name}")
print(f"Mode  : {MODE}  |  preset={PRESET}"
      + (f"  scale->{SCALE_WIDTH}px" if SCALE_WIDTH else "")
      + (f"  fps->{FPS}" if FPS else ""))

if MODE == "crf":
    run(["ffmpeg", "-y", "-i", str(inp),
         "-c:v", "libx264", "-crf", str(CRF), "-preset", PRESET,
         "-pix_fmt", "yuv420p", *vf, *aud,
         "-movflags", "+faststart", str(out)])

elif MODE == "target_size":
    dur = probe_duration(inp)
    target_bits = TARGET_SIZE_MB * 8 * 1_000_000 * SIZE_HEADROOM
    audio_bps   = 128_000 if (KEEP_AUDIO and has_audio(inp)) else 0
    v_kbps = int((target_bits / dur - audio_bps) / 1000)
    if v_kbps < 50:
        sys.exit(f"Target {TARGET_SIZE_MB} MB is too small for a {dur:.0f}s clip "
                 f"(needs ~{v_kbps} kbps video). Raise the target or downscale with SCALE_WIDTH.")
    print(f"Duration {dur:.0f}s -> video bitrate {v_kbps} kbps for ~{TARGET_SIZE_MB} MB")

    # Pass 1: analysis only, no output file, no audio
    print("Pass 1/2 ...")
    run(["ffmpeg", "-y", "-i", str(inp),
         "-c:v", "libx264", "-b:v", f"{v_kbps}k", "-pass", "1",
         "-passlogfile", PASS_LOG, "-preset", PRESET, "-pix_fmt", "yuv420p",
         *vf, "-an", "-f", "null", NULL_DEVICE])
    # Pass 2: real encode
    print("Pass 2/2 ...")
    run(["ffmpeg", "-y", "-i", str(inp),
         "-c:v", "libx264", "-b:v", f"{v_kbps}k", "-pass", "2",
         "-passlogfile", PASS_LOG, "-preset", PRESET, "-pix_fmt", "yuv420p",
         *vf, *aud, "-movflags", "+faststart", str(out)])
    cleanup_pass_logs()

else:
    sys.exit(f"Unknown MODE: {MODE!r}")

size_out = out.stat().st_size
print(f"\nDone. {size_in/1e6:.0f} MB -> {size_out/1e6:.0f} MB "
      f"({100*(1-size_out/size_in):.0f}% smaller)")
print(f"Wrote {out.resolve()}")