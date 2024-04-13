
#%% convert images that were annotated to a mp4 video 

#%%
import cv2
import os, sys
from PIL import Image
import glob

#%% 
camera_name = 'tls_left'
dir_name = '100CANON_29_07_2023/timelapse'
imgFolder = 'D:/JIRP/JIRP_TL/'+ camera_name + '/' + dir_name  # path to image folder
vidName = "TL_left.mp4"

#Specify size of the video if different from image size: 848x480, 1280x720
W = 1800
H = 1200

resize = True 

#Define number of frames (images) per second. .
nfs = 120

#Specify toggle variable to scale the images
n = 1

#%%
#images = [img for img in os.listdir(imagFolder) if img.endswith(".png")]
#glob.glob(Pathname) fetches all file with extension PNG in that folder
images = glob.glob(os.path.join(imgFolder, "*.png"))
#images.sort()
for test in images:
    print(test)

#%%
width, height = Image.open(images[0]).size
size = (width, height)
codec = cv2.VideoWriter_fourcc(*'mp4v') #DIVX, DIVD
if (resize  and n > 0):
    video = cv2.VideoWriter(vidName, codec, nfs, (W, H))
else:
    video = cv2.VideoWriter(vidName, codec, nfs, size)

#Do not open images in 'Image' as well as 'CV2', else following error occurs
#<built-in function imread> returned NULL without setting an error
for img in images:
    #In case images are of different size, resize them to user specified values
    if (resize and n > 0):
        newImg = cv2.imread(img)
        newImg = cv2.resize(newImg, (W, H))
        video.write(newImg)
    else:
        video.write(img)

video.release()
cv2.destroyAllWindows()