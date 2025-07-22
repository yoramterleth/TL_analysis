
#%%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import rasterio
from pathlib import Path

# define csv path and dem
projected_dir = Path("./csv_projected")
velocity_dir = Path("./csv_velocities")
dem_path = Path("./VL_DEM_ibai_UTM.tif")

track_plot_path = Path("./figures_out/all_tracks_on_dem.png")
velocity_plot_path = Path("./figures_out/all_velocity_timeseries.png")

# load dem tif
with rasterio.open(dem_path) as dem_ds:
    dem = dem_ds.read(1, masked=True)
    bounds = dem_ds.bounds
    dem_extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]

#% make a plot showing the tracks of the clicked points on the dem.
fig1, ax1 = plt.subplots(figsize=(12, 10))
ax1.imshow(dem, extent=dem_extent, cmap='terrain', origin='upper')

for i, csv_path in enumerate(projected_dir.glob("*_projected.csv")):
    df = pd.read_csv(csv_path)
    label = csv_path.stem.replace("_projected", "")
    ax1.plot(df['utm_x'], df['utm_y'], marker='o', markersize=4, linewidth=1.5, label=label)

ax1.set_title("All Projected Tracks on DEM")
ax1.set_xlabel("Easting (m)")
ax1.set_ylabel("Northing (m)")
ax1.set_aspect('equal')
ax1.legend(loc='upper right')
ax1.grid(True)
plt.tight_layout()
plt.savefig(track_plot_path, dpi=300)


#%%
# plot the ice velocities
fig2, ax2 = plt.subplots(figsize=(12, 6))

all_series = []  # to store each track's series for averaging

for csv_path in velocity_dir.glob("*_velocities.csv"):
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    label = csv_path.stem.replace("_velocities", "")
    ax2.plot(df['timestamp'], df['line_speed_mpy'], marker='', linestyle='-', label=label)

    series = df[['timestamp', 'line_speed_mpy']].dropna()
    series = series.set_index('timestamp')
    all_series.append(series)

# calculate average of each time step
combined_df = pd.concat(all_series, axis=1, join='outer')
combined_df.columns = [f"track_{i}" for i in range(len(all_series))]
combined_df['mean_speed'] = combined_df.mean(axis=1)

# plot figure 
ax2.plot(combined_df.index, combined_df['mean_speed'], color='black',
         linewidth=2.5, label='Average Speed (all tracks)')

ax2.set_title("Velocity Time Series (All Tracks + Mean)")
ax2.set_xlabel("Time")
ax2.set_ylabel("Speed (m/yr)")
ax2.grid(True)
ax2.legend(loc='best', fontsize=8)
plt.tight_layout()
plt.savefig(velocity_plot_path, dpi=300)

