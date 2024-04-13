
""" Yoram terleth - based on code by Jukes """
#%% select images and timestam them


import os
from PIL import Image,ImageFile
import matplotlib.pyplot as plt
import datetime
import shutil

ImageFile.LOAD_TRUNCATED_IMAGES = True
# %%
# set the station_name and path to folder
camera_name = 'TL_perm'
dir_name = 'servicerun_729'
imgpath = 'D:/JIRP/JIRP_TL/'+ camera_name + '/' + dir_name + '/' # path to image folder
print(camera_name)
os.listdir(imgpath)



#%% make time array 

# force own timestamps ?
override_timestamps = False

# set timestamp array 
img1_time = datetime.datetime(2023,7,16,16,8,12)
imgend_time = datetime.datetime(2023,7,29,20,1,1)
img_interval = datetime.timedelta(minutes=5)

# mini function to make date range
def time_range_list(img1_time, imgend_time,img_interval):
    img_time = img1_time
    while img_time <= imgend_time:
        yield img_time
        img_time += img_interval

img_time_gen = time_range_list(img1_time,imgend_time,img_interval)

# convert to list for easier subscripting
img_time_list = list(img_time_gen)

# initiate timestamp index: 
tmstp_idx = 0 

# %%


for file in os.listdir(imgpath):
        if file.startswith('IMG') and file.endswith('JPG'):
            # grab fileize
            sizeMB = os.path.getsize(imgpath+file)/10e5 # file size in MB

            # the dark images (nighttime) will be smaller than 1 MB, skip those
            if sizeMB > 2:            
                # open image and grab time stamp
                img = Image.open(imgpath+file)
       
                if override_timestamps:
                     img_datetime = img_time_list[tmstp_idx]
                else:
                     exif_data = img._getexif()
                     img_datetime = exif_data[306]
                     
                

#                 print(img_datetime)

                # convert from Central Time to AK time
                if override_timestamps:
                    img_CT = datetime.datetime.strptime(str(img_datetime),'%Y-%m-%d %H:%M:%S')
                    img_AKDT = img_CT
                else:
                    img_CT = datetime.datetime.strptime(str(img_datetime),'%Y:%m:%d %H:%M:%S')
                    img_AKDT = img_CT - datetime.timedelta(hours=8) # AK daylight time - we use AKDT instead of UTC
                img_AK_filename = str(img_AKDT)
                char_remove = [' ',':','-']
                for char in char_remove:
                    img_AK_filename = img_AK_filename.replace(char,'')
                    
                # show image
                plt.imshow(img)
                plt.text(150, 200, img_AKDT, color='dimgrey',fontsize=12) # add timestamp
                plt.axis('off'); plt.tight_layout()

                # save to new folder
                if not os.path.exists(imgpath+'timelapse_jpg'):
                    os.mkdir(imgpath+'timelapse_jpg')
                if not os.path.exists(imgpath+'timelapse_jpg/'+img_AK_filename+'.jpg'):
                    plt.savefig(imgpath+'timelapse_jpg/'+img_AK_filename+'.jpg', dpi=300)
                    
                plt.show()

            # update the idx for the timestamping 
            tmstp_idx += 1 
            print(tmstp_idx)

# %%
