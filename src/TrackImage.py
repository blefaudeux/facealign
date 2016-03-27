# -*- coding: utf-8 -*-
"""
@author: benjamin lefaudeux

Find the inter frame motion, try to make it robust to mismatches
"""

import cv2 as cv
import numpy as np
import traceback
from config import *
import os


class TrackImage:
    def __init__(self, ref_image_path, new_image_path):
        self.new_path = new_image_path
        self.n_max_corners = 400
        self.corners_q_level = 4
        self.ref_image = cv.imread(ref_image_path)
        self.new_image = cv.imread(new_image_path)
        self.new_image_aligned = None

    def compensate_interframe_motion(self, method='shi_tomasi'):
        # Testing different methods here to align the frames

        if method == 'shi_tomasi':
            transform, success = self.__motion_estimation_shi_tomasi(self.ref_image, self.new_image)

        elif method == 'orb':
            transform, success = self.__motion_estimation_orb(self.ref_image, self.new_image)

        elif method == 'sift':
            #    acc_frame_aligned = self.__compensate_SIFT( ref_frame, new_frame)
            print "Cannot use SIFT right now..."
            transform, success = None, False

        else:
            ValueError('Wrong argument for motion compensation')

        if success:
            self.new_image_aligned = cv.warpPerspective(self.new_image, transform, self.ref_image.shape[:-1])
            return self.new_image_aligned, True

        return None, False

    def __motion_estimation_orb(self, ref_frame, new_frame, min_matches=20, min_match_ratio=0.3):
        # Create an ORB detector
        detector = cv.FastFeatureDetector(16, True)
        extractor = cv.DescriptorExtractor_create('ORB')

        # find the keypoints and descriptors
        kp1 = detector.detect(new_frame)
        k1, des1 = extractor.compute(new_frame, kp1)

        kp2 = detector.detect(ref_frame)
        k2, des2 = extractor.compute(ref_frame, kp2)

        # Match using bruteforce
        matcher = cv.DescriptorMatcher_create('BruteForce-Hamming')
        matches = matcher.match(des1, des2)

        # keep only the reasonable matches
        dist = [m.distance for m in matches]        # store all the good matches as per Lowe's ratio test.
        thres_dist = (sum(dist) / len(dist)) * 0.5  # threshold: half the mean
        good_matches = [m for m in matches if m.distance < thres_dist]

        # compute the transformation from the brute force matches
        if len(good_matches) > min_matches:
            print "Enough matchs for compensation - %d/%d" % (len(good_matches), min_matches)
            self.corners = np.float32([k1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            self.corners_next = np.float32([k2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

            transform, mask = cv.findHomography(self.corners, self.corners_next, cv.RANSAC, 5.0)

            # # Check that the transform indeed explains the corners shifts ?
            # mask_match = [m for m in mask if m == 1]
            # match_ratio = len(mask_match) / float(len(mask))
            #
            # if match_ratio < min_match_ratio:
            #     print "Track lost - %d" % match_ratio
            #     return None, False

            # Align the previous accumulated frame
            return transform, True

        else:
            print "Not enough matches are found - %d/%d" % (len(good_matches), min_matches)
            return None, False

    def __motion_estimation_shi_tomasi(self, ref_frame, new_frame, min_matches=20):
        # detect corners
        grey_frame = cv.cvtColor(ref_frame, cv.COLOR_BGR2GRAY)
        corners = cv.goodFeaturesToTrack(grey_frame, self.n_max_corners, .01, 50)    # Better with Fast ?
        corners_next, status, _ = cv.calcOpticalFlowPyrLK(ref_frame, new_frame, corners)    # Track points

        corners_next_back, status_back, _ = cv.calcOpticalFlowPyrLK(new_frame, ref_frame, corners_next)     # Track back

        # - sort out to keep reliable points :
        corners, corners_next = self.__sort_corners(corners, corners_next, status, corners_next_back, status_back, 1.0)

        if len(corners) < 5:
            return None, False

        # Compute the transformation from the tracked pattern
        # -- estimate the rigid transform
        transform, mask = cv.findHomography(corners, corners_next, cv.RANSAC, 5.0)

        # -- see if this transform explains most of the displacements (thresholded..)
        if len(mask[mask > 0]) > min_matches:
            print "Enough match for motion compensation"
            return transform, True

        else:
            print "Not finding enough matchs - {}".format(len(mask[mask > 0]))
            return None, False

    @staticmethod
    def __motion_estimation_sift(ref_frame, new_frame):
        _min_match_count = 10
        _flann_index_kdtree = 0
        sift = cv.SIFT()

        # find the keypoints and descriptors with SIFT
        kp1, des1 = sift.detectAndCompute(ref_frame, None)
        kp2, des2 = sift.detectAndCompute(new_frame, None)

        index_params = dict(algorithm=_flann_index_kdtree, trees=5)
        search_params = dict(checks=50)

        flann = cv.FlannBasedMatcher(index_params, search_params)

        matches = flann.knnMatch(des1, des2, k=2)

        # store all the good matches as per Lowe's ratio test.
        good = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good.append(m)

        # - bring the second picture in the current referential
        if len(good) > _min_match_count:
            print "Enough matches for compensation - %d/%d" % (len(good), _min_match_count)
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

            transform, mask = cv.findHomography(src_pts, dst_pts, cv.RANSAC, 5.0)
            matchesMask = mask.ravel().tolist()

            h, w = ref_frame.shape
            pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
            pts_transform = cv.perspectiveTransform(pts, transform)
            #        new_frame = cv2.polylines(new_frame,[np.int32(transform)],True,255,3, cv2.LINE_AA)

        else:
            print "Not enough matches are found - %d/%d" % (len(good), _min_match_count)
            matchesMask = None

    @staticmethod
    def __draw_vec(img, corners, corners_next):
        """
        Draw motion vectors on the picture

        @param img: picture to draw onto
        @param corners: initial keypoints position
        @param corners_next: position after tracking
        """
        try:
            corn_xy = corners.reshape((-1, 2))
            corn_xy_next = corners_next.reshape((-1, 2))

            i = 0
            for x, y in corn_xy:
                cv.line(img, (int(x), int(y)), (int(corn_xy_next[i, 0]), int(corn_xy_next[i, 1])), [0, 0, 255], 5)
                i += 1

        except ValueError:
            print "Problem printing the motion vectors"

    def save(self, outputpath):
        if self.new_image_aligned is None:
            print("Image not aligned, run motion compensation first")

        outdir = os.path.dirname(outputpath)
        try:
            if not os.path.exists(outdir):
                print('Creating directory ' + outdir)
                os.makedirs(outdir)
        except:
            print(outdir)

        cv.imwrite(outputpath, self.new_image_aligned)

    @staticmethod
    def __sort_corners(corners_init, corners_tracked, status_tracked,
                       corners_tracked_back, status_tracked_back, max_dist=0.5):

        # Check that the status value is 1, and that
        i = 0
        nice_points = []
        for c1 in corners_init:
            c2 = corners_tracked_back[i]
            dist = cv.norm(c1, c2)

            if status_tracked[i] and status_tracked_back[i] and dist < max_dist:
                nice_points.append(i)

            i += 1

        return [corners_init[nice_points], corners_tracked[nice_points]]


def run_track_image(ref_image_path, new_image_path, output_path):
    fi = None

    try:
        print('-- Beginning TrackImage run for image path: ' + new_image_path)

        ti = TrackImage(ref_image_path, new_image_path)
        _, success = ti.compensate_interframe_motion(method='orb')

        if success:
            ti.save(output_path)

    except Exception as e:
        # print all at once to keep imagepath and stack trace from getting separated by multithreading
        msg = '*** Incomplete: ' + ref_image_path + ' ***\n'
        msg += traceback.format_exc()

        if fi is not None:
            print(fi.log)

        print(msg)
        return False

