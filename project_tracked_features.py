""" This script loops through the csv that were user produced for tracking. """

#%% 

import numpy as np
import pandas as pd
import rasterio
from pathlib import Path

# === CONFIGURATION ===
csv_dir = Path("./csv_tracking")        # Folder with input CSVs
output_dir = Path("./csv_projected")    # Folder for output CSVs
dem_path = Path("./VL_DEM_ibai_UTM.tif")

output_dir.mkdir(parents=True, exist_ok=True)

# === CAMERA SETUP ===
cam_x, cam_y, cam_z = 887045, 6540858, 1373  # UTM
pitch_deg, yaw_deg, roll_deg = 0, 135, 0
image_width, image_height = 1920, 1440

# Focal length & sensor size (Canon T3)
focal_mm = 34
sensor_width_mm = 22.3
sensor_height_mm = 14.9

# === INTRINSICS ===
fx = (focal_mm / sensor_width_mm) * image_width
fy = (focal_mm / sensor_height_mm) * image_height
cx = image_width / 2
cy = image_height / 2
pixel_size_x = sensor_width_mm / image_width
pixel_size_y = sensor_height_mm / image_height

# === Load DEM once ===
with rasterio.open(dem_path) as dem_ds:
    dem = dem_ds.read(1, masked=True)
    dem_bounds = dem_ds.bounds
    transform = dem_ds.transform

    def ray_to_world(x_pix, y_pix, base_yaw_deg, base_pitch_deg):
        x_mm = (x_pix - cx) * pixel_size_x
        y_mm = (y_pix - cy) * pixel_size_y
        offset_yaw_deg = np.degrees(np.arctan2(x_mm, focal_mm))
        offset_pitch_deg = np.degrees(np.arctan2(y_mm, focal_mm))
        yaw = base_yaw_deg + offset_yaw_deg
        pitch = base_pitch_deg + offset_pitch_deg
        yaw_rad = np.radians(yaw)
        pitch_rad = np.radians(pitch)
        dx = np.cos(pitch_rad) * np.sin(yaw_rad)
        dy = np.cos(pitch_rad) * np.cos(yaw_rad)
        dz = -np.sin(pitch_rad)
        return np.array([dx, dy, dz])

    def terrain_intersection(ray_origin, ray_dir, max_dist=5000, step=0.5):
        for t in np.arange(0, max_dist, step):
            pos = ray_origin + ray_dir * t
            utm_x, utm_y = pos[0], pos[1]
            if not (dem_bounds.left <= utm_x <= dem_bounds.right and
                    dem_bounds.bottom <= utm_y <= dem_bounds.top):
                continue
            row, col = dem_ds.index(utm_x, utm_y)
            if 0 <= row < dem.shape[0] and 0 <= col < dem.shape[1]:
                ground_z = dem[row, col]
                if pos[2] <= ground_z:
                    return utm_x, utm_y, ground_z
        return None

    # === Loop through all CSVs ===
    for csv_path in csv_dir.glob("*.csv"):
        df = pd.read_csv(csv_path)
        out_rows = []
        for _, row in df.iterrows():
            ray_origin = np.array([cam_x, cam_y, cam_z])
            ray_dir = ray_to_world(row['x'], row['y'], yaw_deg, pitch_deg)
            result = terrain_intersection(ray_origin, ray_dir)
            if result:
                out_rows.append({
                    'filename': row['filename'],
                    'timestamp': row['timestamp'],
                    'utm_x': result[0],
                    'utm_y': result[1],
                    'utm_z': result[2]
                })
        
        if out_rows:
            out_df = pd.DataFrame(out_rows)
            out_name = csv_path.stem + "_projected.csv"
            out_df.to_csv(output_dir / out_name, index=False)
