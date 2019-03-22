#!/usr/bin/env python3

import cv2
import numpy as np
import argparse
from collections import deque
import sys
from datetime import datetime

import methods
import constant

ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", default="GP010016.mp4", help="Provide path to video file")
ap.add_argument("-s", "--seconds", default=None,
                help="Provide time in seconds of target video section showing the key points")
ap.add_argument("-c", "--crab_id", default="crab_", help="Provide a name for the crab to be tracked")
args = vars(ap.parse_args())

# Return video information
vid, length_vid, fps, _, _, vid_duration, _ = methods.read_video(args["video"])
local_creation, creation = methods.get_file_creation(args["video"])
# Set frame where video should start to be read
vid, target_frame = methods.set_video_star(vid, args["seconds"], fps)

while vid.isOpened():
    ret, frame = vid.read()

    methods.enable_point_capture(constant.CAPTURE_VERTICES)
    frame = methods.draw_points_mousepos(frame, methods.quadratpts, methods.posmouse)
    cv2.imshow("Vertices selection", frame)

    if len(methods.quadratpts) == 4:
        print("Vertices were captured. Coordinates in pixels are: top-left {}, top-right {}, "
              "bottom-left {}, and bottom-right {}".format(*methods.quadratpts))
        break

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        # print("Q - key pressed. Window quit by user")
        break

# vid.release()
cv2.destroyAllWindows()

M, side, vertices_draw, IM, conversion = methods.calc_proj(methods.quadratpts)
center = (0, 0)
mini = np.amin(vertices_draw, axis=0)
maxi = np.amax(vertices_draw, axis=0)

ok, frame = vid.read()
frame = cv2.warpPerspective(frame, M, (side, side))

if not ok:
    print("Cannot read video file")
    sys.exit()

# Set up tracker.
# Instead of MIL, you can also use
# BOOSTING, MIL, KCF, TLD, MEDIANFLOW or GOTURN

# tracker = cv2.Tracker_create("BOOSTING")
# tracker = cv2.TrackerBoosting_create()
# tracker = cv2.TrackerMedianFlow_create()
tracker = cv2.TrackerMIL_create()
# tracker = cv2.TrackerKCF_create()
# print(tracker)
# Define an initial bounding box
# bbox = (650, 355, 25, 25)
bbox = cv2.selectROI("tracking select", frame, fromCenter=False)
crab_center = (int(bbox[0] + bbox[2] / 2), int(bbox[1] + bbox[3] / 2))
print(crab_center)

crab_id = args["video"] + "_" + args["crab_id"] + str(crab_center)
print(crab_id)

# Uncomment the line below to select a different bounding box
# bbox = cv2.selectROI(frame, False)

# Initialize tracker with first frame and bounding box
ok = tracker.init(frame, bbox)

# initialize the list of tracked points, the frame counter,
# and the coordinate deltas
pts = deque(maxlen=100000)


counter = 0
(dX, dY) = (0, 0)
direction = ""

startTime = datetime.now()

cv2.destroyAllWindows()

# From warp.py
fgbg1 = cv2.createBackgroundSubtractorMOG2(history=5000, varThreshold=20)
fgbg2 = cv2.createBackgroundSubtractorMOG2(history=5000, varThreshold=100)
fgbg3 = cv2.createBackgroundSubtractorKNN(history=5000, dist2Threshold=250)

for_er = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
for_di = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
for_di1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

out = cv2.VideoWriter("Uca_detection.avi",
                      cv2.VideoWriter_fourcc("M", "J", "P", "G"), 24, (464, 464))


class CompileInformation(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

info = [CompileInformation("local_creation", local_creation),
        CompileInformation("creation", creation),
        CompileInformation("length_vid", length_vid),
        CompileInformation("fps", fps),
        CompileInformation("vid_duration", vid_duration),
        CompileInformation("target_frame", target_frame),
        CompileInformation("side", side),
        CompileInformation("conversion", conversion),
        CompileInformation("tracker", str(tracker))]

info_video = {}
for i in info:
    info_video[i.name] = i.value
# print(info_video)

result_file = methods.data_writer(args["video"], info_video, True)
result_file.close()

start, end, step, _, _ = methods.frame_to_time(info_video)
print("The video recording was started at: ", start, "\n The video recording was ended at: ", end,
      "\n This information might not be precise as it depends on your computer file system")

while vid.isOpened():
    _, img = vid.read()
    # print(img.shape)
    # img = cv2.resize(img, (640,400))
    crop_img = img[mini[1]-10:maxi[1]+10, mini[0]-10:maxi[0]+10]

    result = cv2.warpPerspective(img, M, (side, side))
    crab_frame = cv2.warpPerspective(img, M, (side, side))
    # result_speed = result
    # print(crop_img.shape)
    # print("Dimensions for result are: ", result.shape)
    # result_1 = cv2.warpPerspective(result, IM, (682,593))

    methods.draw_quadrat(img, vertices_draw)
    # cv2.polylines(img, np.int32([quadratpts]), True, (204, 204, 0), thickness=2)

    # From warp.py
    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    hsl = cv2.cvtColor(result, cv2.COLOR_BGR2HLS_FULL)
    one, two, three = cv2.split(hsl)
    fb_res_two3 = fgbg3.apply(two, learningRate=-1)
    fb_res_two3 = cv2.erode(fb_res_two3, for_er)
    fb_res_two3 = cv2.dilate(fb_res_two3, for_di)
    masked = cv2.bitwise_and(result, result, mask=fb_res_two3)

    masked = cv2.addWeighted(result, 0.3, masked, 0.7, 0)
    edge = cv2.Canny(masked, threshold1=100, threshold2=230)

    # cv2.circle(masked, (52,85), 2, (240, 10, 10), 2)
    # cv2.circle(masked, (382,13), 2, (240, 10, 10), 2)
    # cv2.circle(masked, (225,132), 2, (240, 10, 10), 2)
    # cv2.circle(masked, (313,298), 2, (240, 10, 10), 2)
    # cv2.circle(masked, (291,205), 2, (240, 10, 10), 2)
    # cv2.circle(masked, (446,249), 2, (240, 10, 10), 2)
    # cv2.circle(masked, (369,98), 2, (240, 10, 10), 2)
    # cv2.circle(masked, (163, 335), 2, (240, 10, 10), 2)

    # Update tracker
    # ok, bbox = tracker.update(masked)
    ok, bbox = tracker.update(result)
    # print(position)
    position1 = (bbox[0], bbox[1])

    startTime1 = datetime.now().strftime("%Y%m%d_%H%M%S.%f")[:-3]

    # wr.writerow(position)
    # Draw bounding box
    if ok:
        p1 = (int(bbox[0]), int(bbox[1]))
        p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
        cv2.rectangle(result, p1, p2, (204, 204, 100), 2)
        cv2.rectangle(masked, p1, p2, (204, 204, 0))
        # cv2.circle(result, (180,180), 3, (0, 204, 100), 3)

        center = (int(bbox[0] + bbox[2] / 2), int(bbox[1] + bbox[3] / 2))

        _, _, _, time_absolute, time_since_start = methods.frame_to_time(info_video)

        info = [CompileInformation("Frame", counter),
                CompileInformation("Time_absolute", str(time_absolute)),
                CompileInformation("Time_since_start", str(time_since_start)),
                CompileInformation("Crab_ID", crab_id),
                CompileInformation("Crab_Position_x", center[0]),
                CompileInformation("Crab_Position_y", center[1]),
                CompileInformation("Counter", counter)]

        for i in info:
            info_video[i.name] = i.value

        crab = crab_frame[center[1] - 15:center[1] + 15, center[0] - 15:center[0] + 15]
        # crab = frame[int(bbox[0] + bbox[2]/2):100, int(bbox[1] + bbox[3]/2):100]
        # crab = frame[100:(100 + 50), 250:(250 + 50)]
        # filename = os.path.join(dirname, fname, str(center), startTime1)
        # cv2.imwrite(dirname + "/" + filename + "_" + startTime1 + str(center) + "_" + ".jpg", crab)

        pts.appendleft(center)
        # print(center)
        # print(pts)
        # wr.writerow(center)
        # loop over the set of tracked points
        for i in np.arange(1, len(pts)):
            # if either of the tracked points are None, ignore
            # them
            if pts[i - 1] is None or pts[i] is None:
                continue

            # check to see if enough points have been accumulated in
            # the buffer
            if counter >= 5 and i == 1 and pts[-5] is not None:
                # compute the difference between the x and y
                # coordinates and re-initialize the direction
                # text variables
                dX = pts[-5][0] - pts[i][0]
                # dX = pts[i][0] - pts[-5][0]
                dY = pts[-5][1] - pts[i][1]
                # dY = pts[i][1] - pts[-5][1]
                dX = int(dX*0.11)
                dY = int(dY*0.11)
                # print(dX, dY)
                (dirX, dirY) = ("", "")

                # ensure there is significant movement in the
                # x-direction
                if np.abs(dX) > 2:
                    dirX = "East" if np.sign(dX) == 1 else "West"

                # ensure there is significant movement in the
                # y-direction
                if np.abs(dY) > 2:
                    dirY = "North" if np.sign(dY) == 1 else "South"

                # handle when both directions are non-empty
                if dirX != "" and dirY != "":
                    direction = "{}-{}".format(dirY, dirX)

                # otherwise, only one direction is non-empty
                else:
                    direction = dirX if dirX != "" else dirY

            # otherwise, compute the thickness of the line and
            # draw the connecting lines
            thickness = int(np.sqrt(10 / float(i + 1)) * 2.5)
            if thickness == 0:
                thickness = 1

            # cv2.line(result, pts[i - 1], pts[i], (204, 204, 0), thickness)
            cv2.line(result, pts[i - 1], pts[i], (54, 54, 250), thickness)

        # show the movement deltas and the direction of movement on
        # the frame
        direction = "Uca movement " + str(direction)
        cv2.putText(result, direction, (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (10, 10, 10), 2)
        cv2.putText(result, "Displacement (cm) dx: {}, dy: {}".format(dX, dY),
                    (10, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (10, 10, 10), 2)

        # Back transform and show tracker and data in original image

    # counter_f += 1
    # print("Frame count ", counter_f)
    # if counter_f == 60:
    #     counter_f = 0
    #     cv2.imshow("One every ten", result)

    # DISPLAY (Multiple panels video)
    # edge_3_ch = cv2.cvtColor(edge, cv2.COLOR_GRAY2BGR)
    # fb_res_two3_3_ch = cv2.cvtColor(fb_res_two3, cv2.COLOR_GRAY2BGR)
    # original_reshape = cv2.resize(crop_img, (809, 928))
    # display00 = np.hstack((edge_3_ch, fb_res_two3_3_ch))
    # display01 = np.hstack((masked, result))
    # display03 = np.vstack((display00, display01))
    #
    # display = np.hstack((original_reshape, display03))
    #
    # cv2.line(display, (809, 0), (809,928), (239, 170, 0), 6)
    # cv2.line(display, (1273, 0), (1273,928), (239, 170, 0), 4)
    # cv2.line(display, (1737, 464), (809,464), (239, 170, 0), 4)
    #
    # display = cv2.resize(display, (0,0), fx=.5, fy=.5)
    # print(display.shape)
    out.write(result)

    # cv2.imshow("result_1", result_1)
    # cv2.imshow("original", img)
    # cv2.imshow("cropped", crop_img)
    # cv2.imshow("Crab", crab)
    # cv2.imshow("result", result)

    # From warp.py
    # cv2.imshow("background substraction", fb_res_two3)
    # cv2.imshow("masked", masked)
    cv2.imshow("result", result)
    # cv2.imshow("Canny Edges", edge)
    # cv2.imshow("display00", display00)
    # cv2.imshow("display01", display01)
    # cv2.imshow("display", display)
    result_file = methods.data_writer(args["video"], info_video, False)
    counter += 1

    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        break

vid.release()
cv2.destroyAllWindows()
result_file.close()
