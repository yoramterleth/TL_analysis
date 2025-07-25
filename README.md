# TL_analysis

## Overview
This is a code repository with various scripts for processing timelapse imagery. A series of scirpts makes a timelapse video and lceans up images, while another series of scripts is dedicated to manual featyures tracking, conversion of the image coordinates to real world locations, and speed calculation. 
* process_images_png.py old be used to filter images by file size, as dark images are usually smaller. Also changes the resolution of the images and adds a timestamps and white border.
* filter_to_one_per_day.py retains only one image per calendar day, which reduces the workload when tracking.
  
* **feature_tracking.py** is the script that is used to record the velocity based on the timelpase images. The goal is to choose a feature, and click on it in each subsequent image until you lose track of it. The pixel coordinates that you click are automatically recorded to a csv file. One csv is saved per track, the script will prompt for a new track name for each script. Make sure to input the correct track name (see track naming convention below). This script best run as a notebook (I do this through the vs code run cells functionality).

* project_tracked_features.py converts the pixel coordinates to terrain coordinates. It takes the .csv file produced with the feature tracking script and produces a new csv tha will be used in the pseed calculation.
* calculate_flow_speed.py Uses the projected coordinates csv to calculate ice velocities for each track.
* plot_figures.py can be used to visualise the results. It pulls data from the csv files produced when running project_tracked_features and calculate_flow_speed.

  **Be mindful that it is easy to overwrite csv files in all these scripts! Double check that it is okay to do so when running anything.**

## Needed for feature tracking
The only script that is necessary for feature tracking is feature_tracking.py (and the packages within). To compute and plot the velocities you tracked, you can use project_tracked_features.py, calculate_flow_speed.py, and  plot_figures.py. This does also require the dem .tif.

## Track csv file naming convention:

We have split up the icefall into an upper section and a lower section as follows:

![icefall boundary](icefall_boundaries_ft.png)
Roughly above the blue line is upper icefall, below the blue line is lower icefall. 
  
When prompted to enter a name for your track, use ***u*** for upper icefall, or ***l*** for lower icefall, then the first letter of your name, then an incremental number. For example, the 3rd track Yoram records of the lower icefall would be ***ly3.csv***. Notew that points get recorded to the csv as soon as you click them. Entering the same track number again will not overwrite a csv, but add extra rows to it - this will mess with the speed calculation, so please try to avoid this. 

**Thanks for your work!**
