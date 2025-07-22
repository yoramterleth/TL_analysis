"""
This the script that is used to record the velocity based on the timelpase images. 
The goal is to choose a feature, and click on it in each subsequent image until you lose track of it. 
The pixel coordinates that you click are automatically recorded to a csv file. One csv is saved per track, 
the script will prompt for a new track name for each script. Make sure to input the correct track name (see track naming convention below). 
This script best run as a notebook. I do this through the vscode run cells functionality, but you can also use an actual Jupyter notebook. 
If that is the case, simply ciopy past this script into a cell and then run it.
"""

#%%
# use this if you are running this in a notebook. 
%matplotlib widget

#%%
import os
import csv
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.image import imread
import ipywidgets as widgets
from IPython.display import display

# It would be annoying to have to go from the very beginning each time. Here you can set a start-date. 
##############################################################
# Set a cutoff datetime to start after #######################
start_after = datetime(2025, 5, 1, 0, 0, 0) ##################
##############################################################

# here set the correct filepaths
image_folder = Path("./filtered_for_tracking")  # to the images dowloaded from google drive
output_folder = Path("./csv_tracking/")  # to the location of the output csvs



##### End of user input #########################################################################################
# Prompt user for track name
track_name = input("Enter a track name: ").strip()

output_folder.mkdir(parents=True, exist_ok=True)
csv_path = output_folder / f"{track_name}.csv"

image_files = sorted([f for f in image_folder.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])

# Write CSV header if needed
if not csv_path.exists():
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['filename', 'timestamp', 'x', 'y'])



# Find index of first image after the cutoff
index = 0
for i, img_file in enumerate(image_files):
    try:
        ts = datetime.strptime(img_file.stem, '%Y%m%d%H%M%S')
        if ts > start_after:
            index = i
            break
    except ValueError:
        continue  # Skip files with unexpected names

fig, ax = None, None

def record_click_and_advance(x, y):
    global index
    if index < len(image_files):
        filename = image_files[index].name
        timestamp = datetime.strptime(filename.split('.')[0], '%Y%m%d%H%M%S')
        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([filename, timestamp, int(x), int(y)])
        index += 1
        show_image()

# def onclick(event):
#     if event.xdata is not None and event.ydata is not None:
#         record_click_and_advance(event.xdata, event.ydata)

def onclick(event):
    global index
    if event.button == 3:  # Right-click to skip
        index += 1
        show_image()
    elif event.xdata is not None and event.ydata is not None:
        record_click_and_advance(event.xdata, event.ydata)


def onkey(event):
    global index
    if event.key == 'k':  # ← Use 'k' instead of 's' to skip
        index += 1
        show_image()

def skip_clicked(b):
    global index
    index += 1
    show_image()

def show_image():
    global fig, ax, index
    if index >= len(image_files):
        ax.clear()
        ax.set_title("✅ Done reviewing all images.")
        fig.canvas.draw()
        return

    img = imread(image_files[index])
    ax.clear()
    ax.imshow(img)
    ax.set_title(f"{image_files[index].name} — Click to record or right click to skip")
    fig.canvas.draw()

# init figure
if fig is None or ax is None:
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.canvas.mpl_connect('button_press_event', onclick)
    fig.canvas.mpl_connect('key_press_event', onkey)  # ← Keyboard support

skip_button = widgets.Button(description="Skip")
skip_button.on_click(skip_clicked)

display(skip_button)
show_image()

# %%
