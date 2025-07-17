
#%%
import os
import shutil
from pathlib import Path
from collections import defaultdict

# === CONFIGURATION ===
# === CONFIGURATION ===
input_folder = Path("./timelapse_corrected_times")  # Change this
output_folder = Path("./filtered_for_tracking")    # ← CHANGE THIS
image_extensions = ('.png')

# === CREATE OUTPUT FOLDER ===
output_folder.mkdir(parents=True, exist_ok=True)

# === GROUP FILES BY DATE ===
files_by_date = defaultdict(list)

for file in input_folder.iterdir():
    if file.suffix.lower() not in image_extensions or not file.is_file():
        continue

    name = file.stem
    try:
        # Assumes filename starts with YYYYMMDD
        date_str = name[:8]
        if len(date_str) == 8 and date_str.isdigit():
            files_by_date[date_str].append(file)
    except Exception as e:
        print(f"Skipping {file.name}: {e}")

# === COPY LARGEST FILE PER DAY ===
for date, files in files_by_date.items():
    largest = max(files, key=lambda f: f.stat().st_size)
    destination = output_folder / largest.name
    shutil.copy2(largest, destination)
    print(f"Copied: {largest.name} ({largest.stat().st_size/1024:.1f} KB)")

print("✅ Done.")

# %%
