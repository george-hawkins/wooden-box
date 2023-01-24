import argparse
import sys

# IMPORTANT: to get auto-complete etc. for `cv2`, I had to follow this comment here:
# https://youtrack.jetbrains.com/issue/PY-35691/Code-completion-doesnt-work-for-cv2-module#focus=Comments-27-6666997.0-0
import cv2
import numpy as np

from pathlib import Path
from os import path


_MAX_FEATURES = 500
_KEEP_PERCENT = 0.2


def align_images(template_img, current_img):
    # Convert both the template and current images grayscale.
    template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
    current_gray = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)

    # Use ORB to detect key points and extract (binary) local invariant features.
    orb = cv2.ORB_create(_MAX_FEATURES)
    (kp1, des1) = orb.detectAndCompute(template_gray, None)
    (kp2, des2) = orb.detectAndCompute(current_gray, None)

    # Match the features.
    matcher = cv2.DescriptorMatcher_create(cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING)
    matches = matcher.match(des1, des2, None)

    # Sort the matches by their distance (the smaller the distance, # the "more similar" the features are).
    matches = sorted(matches, key=lambda x: x.distance)
    # keep only the top matches
    keep = int(len(matches) * _KEEP_PERCENT)
    matches = matches[:keep]

    # Print the worst distance that will be used, 30 or above is poor.
    worst_distance = matches[-1].distance
    print(f"Worst match distance: {worst_distance}")

    # Extract the best matching points into two arrays of points.
    pts1 = np.empty((keep, 2), dtype="float")
    pts2 = np.empty((keep, 2), dtype="float")
    for (i, m) in enumerate(matches):
        # Indicate that the two key points in the respective images map to each other.
        pts1[i] = kp1[m.queryIdx].pt
        pts2[i] = kp2[m.trainIdx].pt

    # Find the homology matrix.
    (H, _) = cv2.findHomography(pts1, pts2, method=cv2.RANSAC)

    (height, width) = current_img.shape[:2]
    aligned_img = cv2.warpPerspective(template_img, H, (width, height))

    return aligned_img


# For a more sophisticated approaches (that doesn't rely on knowing which image will be darker than the other), see:
# * https://docs.opencv.org/4.x/d1/dc5/tutorial_background_subtraction.html
# * The answers to https://stackoverflow.com/q/21425992/245602 (except the accepted answer from Mohammad Moghimi).
def subtract_images(aligned_img, current_img, output_filename):
    aligned_gray = cv2.bitwise_not(cv2.cvtColor(aligned_img, cv2.COLOR_BGR2GRAY))
    current_gray = cv2.bitwise_not(cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY))

    difference_img = cv2.bitwise_not(cv2.subtract(current_gray, aligned_gray))
    cv2.imwrite(output_filename, difference_img)


def load(filename):
    img = cv2.imread(filename)
    if img is None:
        sys.exit(f'Error: could not load "{filename}\"')
    return img


# Usage: --template template.png --current current.png
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-t", "--template", required=True, help="path to template image")
    ap.add_argument("-o", "--output", required=True, help="path to output directory")
    ap.add_argument("images", metavar="img", nargs="+", help="images to diff against template")
    args = vars(ap.parse_args())

    output_dir = args["output"]
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        sys.exit(f"could not create output directory - {e}")

    template_img = load(args["template"])
    images = args["images"]
    for current_filename in images:
        current_img = load(current_filename)
        aligned_img = align_images(template_img, current_img)

        output_filename = path.join(output_dir, path.basename(current_filename))
        subtract_images(aligned_img, current_img, output_filename)


if __name__ == '__main__':
    main()
