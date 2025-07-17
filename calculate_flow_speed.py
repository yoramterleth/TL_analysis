""" This script calculates speeds in the flow direction based on the projected displacements."""
#%%

import pandas as pd
import numpy as np
from pathlib import Path

# === CONFIGURATION ===
input_dir = Path("./csv_projected")      # Where projected CSVs are located
output_dir = Path("./csv_velocities")    # Where to save velocity CSVs
output_dir.mkdir(parents=True, exist_ok=True)

# === Reference Line (UTM) ===
x0, y0 = 887712.188, 6540636.079
x1, y1 = 886806.161, 6540336.018
line_vec = np.array([x1 - x0, y1 - y0])
line_unit = line_vec / np.linalg.norm(line_vec)

# === Process Each CSV ===
for csv_path in input_dir.glob("*_projected.csv"):
    df = pd.read_csv(csv_path)
    df = df.sort_values("timestamp")
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    displacements = []
    speeds = []

    for i in range(1, len(df)):
        # Position delta
        p1 = df.iloc[i - 1][['utm_x', 'utm_y']].values
        p2 = df.iloc[i][['utm_x', 'utm_y']].values
        delta = p2 - p1

        # Time delta
        dt = (df.iloc[i]['timestamp'] - df.iloc[i - 1]['timestamp']).total_seconds()

        # Project onto reference line
        proj_disp = np.dot(delta, line_unit)
        proj_speed = proj_disp / dt if dt > 0 else np.nan
        proj_speed_mpy = proj_speed * (31_536_000) # 86_400  # m/day

        displacements.append(proj_disp)
        speeds.append(proj_speed_mpy)

    df['line_displacement_m'] = [np.nan] + displacements
    df['line_speed_mpy'] = [np.nan] + speeds

    # Save with _velocities suffix
    out_name = csv_path.stem.replace("_projected", "") + "_velocities.csv"
    df.to_csv(output_dir / out_name, index=False)
