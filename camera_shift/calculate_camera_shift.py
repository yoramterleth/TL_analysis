import cv2 as cv
import numpy as np
from matplotlib import pyplot as plt

# number of sift features we want to have
MIN_MATCH_COUNT = 10
DISTANCE_RATIO_LOWE = 0.3

class CameraShiftCalculator():
    """ Class that is used to calculate the camera shifts (yawn angle) between two images.
    """
    def __init__(self, refer_img: np.ndarray, shift_img: np.ndarray):
        """ Initialize the class by providing two images

        Args:
            refer_img (np.ndarray): Reference image with known yawn angle
            shift_img (np.ndarray): Shifted image for which we want to know the new yawn angle
        """
        self.refer_img = refer_img 
        self.shift_img = shift_img
        
        # TODO consider turning into gray scale images for better sifting

    def show_images(self):
        """ Shows reference and shifted image
        """
        plt.imshow(self.refer_img)
        plt.imshow(self.shift_img)

    # If this is not working well, I need to do this manually instead
    def get_sift_features(self, min_match_count: int = 10, distance_ratio_lowe: float = 0.3) -> dict:
        """ Retrieve SIFT features and store only good features.

        Returns: dict:
                good_matches: All the matches
                reference_points: Source points of reference image
                shifted_points: Destination points of shifted image
                reference_kp: Keypoints of the reference image 
                shifted_kp: Keypoints of the shifted image

        Args:
            min_match_count (int): Minimum number of good features that must be found.
            distance_ratio_lowe (float): Ratio between the best match and second best match.
                The smaller the more conservative in finding good matches. Consider setting to 0.5 or lower.
        
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

        return {
            "good_matches": good_matches,
            "reference_points": pts_ref,
            "shifted_points": pts_shi,
            "reference_kp": kp_ref,
            "shifted_kp": kp_shi,
        }
    
    def find_homography(self, good_matches: list, reference_points: np.ndarray, shifted_points: np.ndarray, reference_kp: tuple, shifted_kp: tuple):
        """ Find the homography and visualize the matched keypoints and the overlap.
        """
        # find homography
        M, mask = cv.findHomography(reference_points, shifted_points)
        matchesMask = mask.ravel().tolist()

        # find perspective transformations
        h,w,c = self.refer_img.shape
        pts = np.float32([ [0,0],[0,h-1],[w-1,h-1],[w-1,0] ]).reshape(-1,1,2)
        dst = cv.perspectiveTransform(pts,M)

        # drawing the box
        self.shifted_img = cv.polylines(self.shift_img,[np.int32(dst)],True,255,3, cv.LINE_AA)

        # draw matched points
        draw_params = dict(matchColor = (0,255,0), # draw matches in green color
                   singlePointColor = None,
                   matchesMask = matchesMask, # draw only inliers
                   flags = 2)
        matched_img = cv.drawMatches(self.refer_img, reference_kp, self.shift_img, shifted_kp, good_matches, None,**draw_params)
        
        plt.imshow(matched_img)
        plt.show()


if __name__ == "__main__":

    refer_img = cv.imread("data/reference_pic.png")
    shift_img = cv.imread("data/shifted_pic.png")

    calc = CameraShiftCalculator(refer_img, shift_img)

    # look at our original pics
    #calc.show_images()

    # find sift features and find best matches
    sift_dict = calc.get_sift_features(
        min_match_count=MIN_MATCH_COUNT,
        distance_ratio_lowe=DISTANCE_RATIO_LOWE,
    )

    # find homography and visualize our matched sift features
    calc.find_homography(**sift_dict)