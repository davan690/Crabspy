#!/usr/bin/env python3

"""
This code intends to count feeding activity in crabs.
"""

import argparse
import cv2
import sys
import csv
from datetime import datetime
import os
from collections import deque
import numpy as np
# from random import randint
import random as rng
from skimage.morphology import skeletonize
from skimage.util import invert
from skimage import measure, filters, feature, exposure, segmentation, color
from skimage.future import graph

import matplotlib.pyplot as plt
from matplotlib import animation
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib import colors
import matplotlib.gridspec as gridspec
import time


__author__ = "Cesar Herrera"
__copyright__ = "Copyright (C) 2019 Cesar Herrera"
__license__ = "GNU GPL"

'''
Parser arguments
'''
ap = argparse.ArgumentParser()
ap.add_argument('-v', '--video', default="VIRB0037-3.MP4", help='Provide path to video file')
ap.add_argument('-s', '--seconds', default=640,
                help='Provide time in seconds of target video section showing the key points')
args = vars(ap.parse_args())

# Read video
# vid = cv2.VideoCapture(args['video'])
vid = cv2.VideoCapture('video/' + args['video'])

fname = os.path.basename(args['video'])
filename, file_ext = os.path.splitext(fname)
print(fname)
dirname = 'samples_pos'

startTime = datetime.now()

# SECONDS
fps = vid.get(cv2.CAP_PROP_FPS)
if args['seconds'] is None:
    target_frame = 1
else:
    target_frame = int(int(args['seconds']) * fps)
vid.set(1, target_frame-1)


# Exit if video not opened.
if not vid.isOpened():
    print("Could not open video")
    sys.exit()

'''
This section creates a background model for do background substraction'''

# ave
(rAvg, gAvg, bAvg) = (None, None, None)
total_ave = 0


position = (0, 0)
center = (0, 0)

tracker = cv2.TrackerBoosting_create()

# Read first frame.q
ok, frame = vid.read()
frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
if not ok:
    print('Cannot read video file')
    sys.exit()

# Define an initial bounding box
# bbox = (650, 355, 25, 25)
# bbox = cv2.selectROI('tracking select', frame, fromCenter=False)
bbox = (357, 431, 182, 108)

print(bbox)
cv2.destroyAllWindows()

# Initialize tracker with first frame and bounding box
ok = tracker.init(frame, bbox)


# initialize the list of tracked points, the frame counter,
# and the coordinate deltas
pts = deque(maxlen=10000)
counter = 0
(dX, dY) = (0, 0)
direction = ""

fgbg1 = cv2.createBackgroundSubtractorMOG2(history=5000, varThreshold=20)
# fgbg1 = cv2.createBackgroundSubtractorMOG2(history = 100, varThreshold=10)
fgbg2 = cv2.createBackgroundSubtractorMOG2(history=5000, varThreshold=100)
fgbg3 = cv2.createBackgroundSubtractorKNN(history=5000, dist2Threshold=250)

# for_er = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5, 5))
for_er = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
for_di = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (20, 20))
for_di1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

# out = cv2.VideoWriter('Uca_detection+tracking.avi',cv2.VideoWriter_fourcc('M','J','P','G'), 24, (960,720))
# BG_MODEL = cv2.imread('BG_model.jpg')
hull_list = []

element = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))

# fig = plt.figure()
# grid = gridspec.GridSpec(ncols=2, nrows=2)
# ax1 = fig.add_subplot(grid[:-1,:], projection = "3d")
# ax2 = fig.add_subplot(grid[-1,:-1])
# ax3 = fig.add_subplot(grid[-1,-1])

while True:
    # Read a new frame
    ok, frame_ori = vid.read()

    if not ok:
        break

    if ok:
        frame = cv2.resize(frame_ori, (0, 0), fx=0.5, fy=0.5)
        frame_norec = frame.copy()

        hsl = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS_FULL)
        one, two, three = cv2.split(hsl)
        blue, green, red = cv2.split(frame)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Update tracker
        ok, bbox = tracker.update(frame)
        # print(position)
        position = (bbox[0], bbox[1])

        p1 = (int(bbox[0]), int(bbox[1]))
        p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))

        center = (int(bbox[0] + bbox[2]/2), int(bbox[1] + bbox[3]/2))
        cv2.rectangle(frame, p1, p2, (0, 0, 255))

        # crab = gray[center[1]-100:center[1]+100, center[0]-100:center[0]+100]
        crab = three[center[1]-100:center[1]+100, center[0]-100:center[0]+100]
        crab_color = frame[center[1]-100:center[1]+100, center[0]-100:center[0]+100]
        crab_red = red[center[1]-100:center[1]+100, center[0]-100:center[0]+100]

        opening = cv2.morphologyEx(crab, cv2.MORPH_OPEN, (11, 11))
        blur = cv2.GaussianBlur(opening, (5, 5), 0)
        blur1 = cv2.GaussianBlur(opening, (9, 9), 0)

        result = blur1

        _, th4 = cv2.threshold(result, 240, 255, cv2.THRESH_OTSU+cv2.THRESH_BINARY)
        th4[th4 == 255] = 1

        th5 = np.array(th4, dtype=np.uint8)
        th5[th5 == 1] = 255
        # image = invert(th4)
        skeleton = skeletonize(th4)
        skeleton = np.array(skeleton, dtype=np.uint8)
        skeleton[skeleton == 1] = 255

        row0 = np.hstack((crab, result))
        # row0 = np.hstack((crab_ch, result))
        row1 = np.hstack((opening, blur))
        row2 = np.hstack((th5, skeleton))

        res1 = np.vstack((row1, row2))
        res = np.vstack((row0, res1))

        # contours = measure.find_contours(red, 0.8)
        # new = filters.sobel(crab_red)
        # new = np.array(new, dtype=np.uint8)
        # new[new == 1] = 255

        # Sobel filter
        # new_x = cv2.Sobel(crab_red, cv2.CV_32F, 1, 0)
        # new_y = cv2.Sobel(crab_red, cv2.CV_32F, 0, 1)
        # new_xcvt = cv2.convertScaleAbs(new_x)
        # new_ycvt = cv2.convertScaleAbs(new_y)
        # new = cv2.addWeighted(new_xcvt, 0.5, new_ycvt, 0.5, 0)

        # Adjust exposure with Gamma and Logarithmic correction
        # new_gamma = exposure.adjust_gamma(opening, 3)
        # new_log = exposure.adjust_log(opening, 2, inv=True)
        new_sigmoid = exposure.adjust_sigmoid(opening, cutoff=0.1, gain=15, inv=False)

        # HOG
        new_fd, new_hog = feature.hog(new_sigmoid, orientations=5, pixels_per_cell=(22, 22), block_norm="L1",
                                      cells_per_block=(5, 5), transform_sqrt=False, visualize=True, multichannel=False)
        new_hog = exposure.rescale_intensity(new_hog, in_range=(0, 10))


        # # RAG
        # labels = segmentation.slic(opening, compactness=30, n_segments=200)
        # edges = filters.sobel(opening)
        # edges_rgb = color.gray2rgb(edges)
        # g = graph.rag_boundary(labels, edges)
        # lc = graph.show_rag(labels, g, edges_rgb, img_cmap=None, edge_cmap='viridis', edge_width=1.2)


        # skel = np.zeros(crab.shape, np.uint8)
        # eroded = cv2.erode(crab, element)
        # dilated =cv2.dilate(eroded, element)
        # result = cv2.subtract(crab, dilated)
        # skel = cv2.bitwise_or(skel, result)

        pts.appendleft(center)

        # cv2.imshow("Tracking", frame)
        # cv2.imshow('Crab', crab)

        # cv2.imshow('eroded', eroded)
        # cv2.imshow('dilated', dilated)
        # cv2.imshow('result', result)
        # cv2.imshow('Skel', skel)

        # cv2.imshow("opening", opening)
        # cv2.imshow("blur", blur)
        # cv2.imshow("th4", th4)
        # cv2.imshow("th5", th5)
        # cv2.imshow("image", image)
        # cv2.imshow("skeleton", skeleton)

        cv2.imshow("res", res)
        cv2.imshow("Crab color", crab_color)
        cv2.imshow("Crab color2", new_hog.astype("uint8")*255)
        # cv2.imshow("Crab color3", new_gamma.astype("uint8")*255)
        # cv2.imshow("Crab color3", new_log.astype("uint8")*255)
        # cv2.imshow("Crab color3", new_sigmoid.astype("uint8")*255)
        # cv2.imshow("Crab red", crab_red)

        # crab_color2 = frame_norec[p1[1]:p2[1], p1[0]:p2[0]]
        # hsv = cv2.cvtColor(crab_color2, cv2.COLOR_BGR2HSV)
        # hsv = cv2.GaussianBlur(hsv, (21,21), 0)
        # one, two, three = cv2.split(hsv)
        #
        # crab_color2 = cv2.cvtColor(crab_color2, cv2.COLOR_BGR2RGB)
        # # one, two, three = cv2.split(crab_color2)
        # crab_color2 = cv2.GaussianBlur(crab_color2, (21, 21), 0)
        # pixel_colors = crab_color2.reshape((np.shape(crab_color2)[0] * np.shape(crab_color2)[1], 3))
        # norm = colors.Normalize(vmin=-1., vmax=1.)
        # norm.autoscale(pixel_colors)
        # pixel_colors = norm(pixel_colors).tolist()
        # ax1.clear()
        # ax1.scatter(one.flatten(), two.flatten(), three.flatten(), facecolors=pixel_colors, marker=".")
        # ax1.set_xlabel("Hue")
        # # ax1.set_xlabel("Red")
        # ax1.set_ylabel("Saturation")
        # # ax1.set_ylabel("Green")
        # ax1.set_zlabel("Value")
        # # ax1.set_zlabel("Blue")
        # # plt.pause(0.00001)
        # # Hue: 0-180
        # # Saturation: 0-255
        # # Value: 0-255
        # lower_hsv1 = np.array([0, 0, 0])
        # upper_hsv1 = np.array([180, 50, 40])
        # lower_hsv2 = np.array([0, 50, 80])
        # upper_hsv2 = np.array([180, 100, 120])
        # # mask1 = cv2.inRange(hsv, lower_hsv1, upper_hsv1)
        # mask1 = cv2.inRange(crab_color2, lower_hsv1, upper_hsv1)
        # # mask2 = cv2.inRange(hsv, lower_hsv2, upper_hsv2)
        # mask2 = cv2.inRange(crab_color2, lower_hsv2, upper_hsv2)
        # mask = cv2.bitwise_or(mask1, mask2)
        # # result_plt = cv2.bitwise_not(crab_color2, crab_color2, mask=mask1)
        # result_plt = cv2.bitwise_and(crab_color2, crab_color2, mask=mask)
        #
        # ax2.clear()
        # ax2.imshow(cv2.bitwise_not(mask), cmap="gray")
        #
        # ax3.clear()
        # ax3.imshow(result_plt)
        #
        # plt.pause(0.001)

        counter += 1

        # Exit if ESC pressed
        k = cv2.waitKey(1) & 0xff
        if k == 27:
            break

# plt.draw()
# plt.show()
vid.release()
cv2.destroyAllWindows()
print(datetime.now() - startTime)

