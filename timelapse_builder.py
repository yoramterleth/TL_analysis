

# %%
import re
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps


# %%
IMAGE_DIR   = Path(r"C:\Users\yter01\Documents\GIANT_project\RAW_DATA\TL\West_Lookout_Calving_07_30") # Path(r"L:\work\scientific_work_areas\land_instruments\RAW_DATA_BACKUP\TL CAMERAS\West_Lookout_Calving_7_30") # Path(r"D:\DATA GIANT\TL CAMERAS\WEST BEACH CANON")   
OUTPUT      = Path(r"L:\work\scientific_work_areas\land_instruments\TL_videos\calving_7_30.mp4")

START_TIME  = datetime(2026,7,30,16,45,00)         
END_TIME    = datetime(2026,8,16,20,15,00)

FPS         = 4
TARGET_WIDTH = 1920         # frames are resized to this width (aspect preserved); None = use first frame's size
EXTENSIONS  = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}

# Timestamp overlay
TS_FORMAT   = "%Y-%m-%d %H:%M:%S"
TS_MARGIN   = 20            # px from top-left corner
TS_SCALE    = 0.025         # fraction of frame height
TS_COLOR    = (255, 255, 255)
TS_BG       = (0, 0, 0, 140) 

# order of preference to look for image timestamp
TS_SOURCES  = ("exif", "filename", "mtime")
EXCLUDE_HOURS = (23, 4)

# brigthening options 
# Night brightening — boosts dark frames, leaves bright ones alone.
# Decision is based on each frame's own mean brightness, so no sunrise/clock table is needed.
NIGHT_BRIGHTEN   = True   # set False to disable
NIGHT_LUMA_DAY   = 100    # frames at/above this mean brightness (0–255) get no boost
NIGHT_LUMA_NIGHT = 40     # frames at/below this get the full boost; between = smooth ramp
NIGHT_GAMMA      = 0.4   # boost strength for a full-night frame (<1 brightens; lower = brighter)

# Decimation — thin out frames before building the video.
# DECIMATE_STEP = N keeps every Nth frame (1 = keep all).
# Or set MAX_FRAMES to a number and it auto-picks a step to land near that count.
DECIMATE_STEP = 1
MAX_FRAMES    = None

# %%
# Filename patterns tried in order: (regex, strptime format)
FILENAME_PATTERNS = [
    (r"(\d{4}[-_]?\d{2}[-_]?\d{2}[-_ T]\d{2}[-:]?\d{2}[-:]?\d{2})", None),  # generic, normalised below
]


def _from_exif(path):
    try:
        with Image.open(path) as im:
            exif = im.getexif()
            # 36867 = DateTimeOriginal, 36868 = DateTimeDigitized, 306 = DateTime
            for tag in (36867, 36868, 306):
                raw = exif.get(tag)
                if raw:
                    return datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
            # DateTimeOriginal sometimes lives in the Exif IFD only
            ifd = exif.get_ifd(0x8769)
            for tag in (36867, 36868):
                raw = ifd.get(tag)
                if raw:
                    return datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None


def _from_filename(path):
    for pattern, fmt in FILENAME_PATTERNS:
        m = re.search(pattern, path.name)
        if not m:
            continue
        s = re.sub(r"[-_:T ]", "", m.group(1))   # -> YYYYMMDDHHMMSS
        if len(s) == 14:
            try:
                return datetime.strptime(s, "%Y%m%d%H%M%S")
            except ValueError:
                continue
    return None


def _from_mtime(path):
    return datetime.fromtimestamp(path.stat().st_mtime)


def get_timestamp(path, sources=TS_SOURCES):
    fns = {"exif": _from_exif, "filename": _from_filename, "mtime": _from_mtime}
    for src in sources:
        ts = fns[src](path)
        if ts is not None:
            return ts, src
    return None, None

def keep_by_hour(ts):
    """False if ts falls inside EXCLUDE_HOURS. The window wraps past midnight
    when start > end, so (22, 5) means 'drop 22:00-04:59'."""
    if EXCLUDE_HOURS is None:
        return True
    start, end = EXCLUDE_HOURS
    hod = ts.hour + ts.minute / 60 + ts.second / 3600   # decimal hour-of-day
    excluded = (start <= hod < end) if start <= end else (hod >= start or hod < end)
    return not excluded

# %%
from math import ceil

def decimate(frames, step=DECIMATE_STEP, max_frames=MAX_FRAMES):
    """Thin a time-sorted frame list. If max_frames is set it wins, choosing the
    smallest step that lands at or under that count; otherwise keep every step-th frame.
    Always keeps the first frame."""
    n = len(frames)
    if max_frames and n > max_frames:
        step = ceil(n / max_frames)
    step = max(1, int(step))
    return frames[::step]

def parse_bound(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Could not parse datetime: {value!r}")

# function for brightening 
def night_gain(im):
    """Brighten dark (night) frames without touching bright (day) frames.
    Uses the frame's mean luminance to scale a gamma lift smoothly, so there's
    no hard jump between a 'day' frame and a 'night' frame."""
    if not NIGHT_BRIGHTEN:
        return im
    luma = float(np.asarray(im.convert("L")).mean())
    span = max(1e-6, NIGHT_LUMA_DAY - NIGHT_LUMA_NIGHT)
    t = min(1.0, max(0.0, (NIGHT_LUMA_DAY - luma) / span))   # 0 = day, 1 = night
    if t == 0.0:
        return im
    gamma = 1.0 + t * (NIGHT_GAMMA - 1.0)
    lut = (((np.arange(256) / 255.0) ** gamma) * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(lut[np.asarray(im)])

## run 

files = sorted(p for p in IMAGE_DIR.rglob("*") if p.suffix in EXTENSIONS)
print(f"Found {len(files)} image files in {IMAGE_DIR} (including subfolders)")

#  Decimate by file order BEFORE reading timestamps — the EXIF loop below is the slow part.
n_all = len(files)
files = decimate(files)
if len(files) != n_all:
    print(f"Decimated {n_all} -> {len(files)} files before reading timestamps")

stamped = []
no_ts = []
for p in files:
    ts, src = get_timestamp(p)
    (stamped if ts else no_ts).append((p, ts, src))

if no_ts:
    print(f"WARNING: {len(no_ts)} files had no usable timestamp and were skipped, e.g. {no_ts[0][0].name}")

t0, t1 = parse_bound(START_TIME), parse_bound(END_TIME)
frames = [(p, ts, src) for p, ts, src in stamped
          if (t0 is None or ts >= t0) and (t1 is None or ts <= t1) and keep_by_hour(ts)]
          
frames.sort(key=lambda x: x[1])

if not frames:
    raise SystemExit("No frames left after filtering — check IMAGE_DIR and the time bounds.")


srcs = {src for _, _, src in frames}
print(f"{len(frames)} frames selected (timestamp source: {', '.join(sorted(srcs))})")
print(f"Range: {frames[0][1]}  ->  {frames[-1][1]}")
print(f"Duration at {FPS} fps: {len(frames) / FPS:.1f} s")



# %%
def load_font(px):
    candidates = []

    # Prefer matplotlib's bundled DejaVu Sans — ships with matplotlib, so it
    # works regardless of what fonts (if any) the OS/environment provides.
    try:
        import matplotlib
        mpl_data = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        candidates += [
            str(mpl_data / "DejaVuSans-Bold.ttf"),
            str(mpl_data / "DejaVuSans.ttf"),
        ]
    except ImportError:
        pass

    # OS fonts as a secondary option, in case they're available too.
    candidates += [
        "arial.ttf",
        "Arial.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
    ]

    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, px)
        except Exception as e:
            print(f"  font attempt failed: {candidate!r} -> {type(e).__name__}: {e}")

    print("WARNING: no TrueType font found — falling back to tiny default bitmap font")
    return ImageFont.load_default()


def render_frame(path, ts, size, font):
    """Returns a BGR numpy array ready for cv2.VideoWriter."""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        if im.size != size:
            im = im.resize(size, Image.LANCZOS)
        im = night_gain(im)

        text = ts.strftime(TS_FORMAT)
        if TS_BG is not None:
            overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(overlay)
            box = d.textbbox((TS_MARGIN, TS_MARGIN), text, font=font)
            pad = max(4, font.size // 4)
            d.rectangle([box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad], fill=TS_BG)
            im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")

        d = ImageDraw.Draw(im)
        d.text((TS_MARGIN, TS_MARGIN), text, font=font, fill=TS_COLOR)

    return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)


# Work out the output size from the first frame
with Image.open(frames[0][0]) as _im:
    w, h = ImageOps.exif_transpose(_im).size
if TARGET_WIDTH:
    h = int(round(h * TARGET_WIDTH / w))
    w = TARGET_WIDTH
w -= w % 2   # H.264/mp4 encoders want even dimensions
h -= h % 2
SIZE = (w, h)
font_px = max(12, int(round(h * TS_SCALE)))
FONT = load_font(font_px)
print(f"Output size: {SIZE}, font size: {FONT.size if hasattr(FONT, 'size') else 'default'}")



# %%
preview = render_frame(*frames[0][:2], SIZE, FONT)
Image.fromarray(cv2.cvtColor(preview, cv2.COLOR_BGR2RGB))

# %%
writer = cv2.VideoWriter(str(OUTPUT), cv2.VideoWriter_fourcc(*"mp4v"), FPS, SIZE)
if not writer.isOpened():
    raise RuntimeError("VideoWriter failed to open — try a different codec or output extension.")

try:
    for i, (p, ts, _) in enumerate(frames, 1):
        writer.write(render_frame(p, ts, SIZE, FONT))
        if i % 25 == 0 or i == len(frames):
            print(f"\r{i}/{len(frames)} frames", end="")
finally:
    writer.release()

print(f"\nWrote {OUTPUT.resolve()}  ({OUTPUT.stat().st_size / 1e6:.1f} MB)")
