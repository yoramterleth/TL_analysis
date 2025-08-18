import math
from scipy.spatial.transform import Rotation
import cv2 as cv
import numpy as np
from matplotlib import pyplot as plt

# number of sift features we want to have
MIN_MATCH_COUNT = 10
DISTANCE_RATIO_LOWE = 0.3

# camera params
FOCAL_MM = 34
SENSOR_X_MM = 22.3
SENSOR_Y_MM = 14.9

class CameraShiftCalculator():
    """ Class that is used to calculate the camera shifts (yawn angle) between two images.
    """
    def __init__(
            self, 
            refer_img: np.ndarray, 
            shift_img: np.ndarray,
            focal_mm: float, 
            sensor_x_mm: float, 
            sensor_y_mm: float,

        ):
        """ Initialize the class by providing two images

        Args:
            refer_img : Reference image with known yawn angle
            shift_img: Shifted image for which we want to know the new yawn angle
            focal_mm: focal length of camera in mm
            sensor_x_mm: pixel size of sensor along x-axis (width)
            sensor_y_mm: pixel size of sensor along y-axis (height)
        """
        # attributes set from the beginning
        self.refer_img = refer_img 
        self.shift_img = shift_img
        self.focal_mm = focal_mm                # taken from project_tracked_features
        self.sensor_x_mm = sensor_x_mm          # pixel size on sensor, along x-axis
        self.sensor_y_mm = sensor_y_mm          # pixel size on sensor, along y-axis
        self.cx = self.refer_img.shape[1] / 2   # half of width to get img center
        self.cy = self.refer_img.shape[0] / 2   # half of height to get img center
        self.fx = (self.focal_mm / self.sensor_x_mm) * self.refer_img.shape[1]
        self.fy = (self.focal_mm / self.sensor_y_mm) * self.refer_img.shape[0]

        # attributes set during usage
        self._H = None 
        self._mask = None
        self._good_matches = None
        self._reference_points = None
        self._shifted_points = None 
        self._reference_kp = None 
        self._shifted_kp = None

        # the angles that can be returned in the end
        self.roll_deg = None
        self.pitch_deg = None 
        self.yaw_deg = None 

    def show_images(self):
        """ Shows reference and shifted image
        """
        plt.imshow(self.refer_img)
        plt.imshow(self.shift_img)

    # If this is not working well, I need to do this manually instead
    def get_sift_features(self, min_match_count: int = 10, distance_ratio_lowe: float = 0.3) -> dict:
        """ Retrieve SIFT features and store only good features.

        Args:
            min_match_count: Minimum number of good features that must be found.
            distance_ratio_lowe: Ratio between the best match and second best match.
                The smaller the more conservative in finding good matches. Consider setting to 0.5 or lower.

                Sets:
                self.good_matches: All the matches
                self.reference_points: Source points of reference image
                self.shifted_points: Destination points of shifted image
                self.reference_kp: Keypoints of the reference image 
                self.shifted_kp: Keypoints of the shifted image
        
        Raises:
            RuntimeError if not enough good matches were found
        """
        # initiate sift detector
        sift = cv.SIFT_create()

        # find keypoints and descriptors with SIFT
        kp_ref, des_ref = sift.detectAndCompute(self.refer_img, None)
        kp_shi, des_shi = sift.detectAndCompute(self.shift_img, None)

        # choose algorithm here
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
        search_params = dict(checks = 50)
        
        flann = cv.FlannBasedMatcher(index_params, search_params)
        
        matches = flann.knnMatch(des_ref,des_shi,k=2)

        # store all the good matches as per Lowe's ratio test.
        good_matches = []
        for m, n in matches:
            if m.distance < distance_ratio_lowe*n.distance:
                good_matches.append(m)

        # RuntimeError is a bit rough here, but let's keep it for now since it is very unlikely
        if not len(good_matches) > min_match_count:
            raise RuntimeError(f"Only {len(good_matches)} matches were found, but {min_match_count} are required. Consider setting the distance ratio for the Lowe test higher.")
        
        # else we can extract locations and matched keypoints and return those
        pts_ref = np.float32([ kp_ref[m.queryIdx].pt for m in good_matches ]).reshape(-1,1,2)
        pts_shi = np.float32([ kp_shi[m.trainIdx].pt for m in good_matches ]).reshape(-1,1,2)

        # set attributes for class
        self._good_matches = good_matches 
        self._reference_points = pts_ref 
        self._shifted_points = pts_shi 
        self._reference_kp = kp_ref 
        self._shifted_kp = kp_shi
    
    def find_homography(self):
        """ Find the homography 
        Sets:
                np.ndarray: The homography
                np.ndarray: The mask
        """
        self._H, self._mask = cv.findHomography(self._reference_points, self._shifted_points)
    
    def draw_matched_features(self):
        """ Find the homography and visualize the matched keypoints and the overlap.

        """
        # find homography
        matchesMask = self._mask.ravel().tolist()

        # find perspective transformations
        h,w,c = self.refer_img.shape
        pts = np.float32([ [0,0],[0,h-1],[w-1,h-1],[w-1,0] ]).reshape(-1,1,2)
        dst = cv.perspectiveTransform(pts,self._H)

        # drawing the box
        self.shifted_img = cv.polylines(self.shift_img,[np.int32(dst)],True,255,3, cv.LINE_AA)

        # draw matched points
        draw_params = dict(
            matchColor = (0,255,0), # draw matches in green color
            singlePointColor = None,
            matchesMask = matchesMask, # draw only inliers
            flags = 2,
            )
        matched_img = cv.drawMatches(self.refer_img, self._reference_kp, self.shift_img, self._shifted_kp, self._good_matches, None,**draw_params)
        
        plt.imshow(matched_img)
        plt.show()

    def calc_rotation_matrix(self):
        """ Calculates the angles between reference and shifted image
        """
        ## Trial 1

        # # perform singular value decomposition
        # U, _, Vt = np.linalg.svd(self._H) # U: left singular vectors; _: singular vectors (unused), Vt: right singular vectors transposed
        
        # # rotation matrix is the vector cross product of U and Vt
        # R = U @ Vt 

        # # get angles from rotation matrix
        # # see e.g. here: https://web.archive.org/web/20220428033032/http://planning.cs.uiuc.edu/node103.html
        # yaw = math.atan2(R[1][0], R[0][0]) 
        # pitch = - math.asin(R[2][0])# OR: atan2 (-R20 / sqrt(R21**2 + R22**2))
        # roll = math.atan2(R[2][1], R[2][2])

        # # convert to degrees and assign to class attributes
        # self.yaw_deg = math.degrees(yaw)
        # self.pitch_deg = math.degrees(pitch)
        # self.roll_deg = math.degrees(roll)

        # print(self.yaw_deg)
        # print(self.pitch_deg)
        # print(self.roll_deg)
        # exit(0)

        ## Trial 2

        # arrange camera intrinsic parameters as camera matrix
        K = np.array([[self.fx, 0, self.cx], [0, self.fy, self.cy], [0, 0, 1]])

        # decompose homography matrix (I tried singular value decomposition before, not sure what cv2 is doing under the hood)
        _, rotations, translations, normals = cv.decomposeHomographyMat(self._H, K)

        # extract one solution (missing step here: deriving the best solution??), as there are several ones
        R = rotations[0]

        # use scipy to get the Euler angles (exact same results like using atan2 and converting to degrees afterwards)
        self.roll_deg, self.pitch_deg, self.yaw_deg = Rotation.from_matrix(R).as_euler("xyz", degrees=True)


    def get_angles(self) -> tuple:
        """ Returns how the image has been shifted
        Returns:
            tuple:
                float: roll angle
                float: pitch angle
                float: yaw angle
        """
        return self.roll_deg, self.pitch_deg, self.yaw_deg

if __name__ == "__main__":

    refer_img = cv.imread("data/reference_pic.png")
    shift_img = cv.imread("data/shifted_pic.png")

    calc = CameraShiftCalculator(
        refer_img, 
        shift_img,
        FOCAL_MM,
        SENSOR_X_MM,
        SENSOR_Y_MM,
    )

    # visualize our original pics
    #calc.show_images()

    # find sift features and find best matches
    sift_dict = calc.get_sift_features(
        min_match_count=MIN_MATCH_COUNT,
        distance_ratio_lowe=DISTANCE_RATIO_LOWE,
    )

    # find homography 
    calc.find_homography()

    # visualize our matched sift features
    #calc.draw_matched_features()

    # find yaw angle via rotation map
    calc.calc_rotation_matrix()
    roll, pitch, yaw = calc.get_angles()
    print("The image has shifted with the following angles:")
    print("     Roll Deg:", roll)
    print("     Pitch Deg:", pitch)
    print("     Yaw Deg:", yaw)