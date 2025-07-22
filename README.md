# TL_analysis
This is a code repository with various scripts for processing timelapse imagery. A series of scirpts makes a timelapse video and lceans up images, while another series of scripts is dedicated to manual featyures tracking, conversion of the image coordinates to real world locations, and speed calculation. 
* process_images_png.py old be used to filter images by file size, as dark images are usually smaller. Also changes the resolution of the images and adds a timestamps and white border.
* filter_to_one_per_day.py retains only one image per calendar day, which reduces the workload when tracking.
* feature_tracking.py is user interactive and is best run as a notebook (I do this through the vs code run cells functionality). User has to click the same feature in concecutive images. One csv is saved per track, user needs to make sure to record track name in the script 
