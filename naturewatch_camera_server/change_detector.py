import logging
import time
from datetime import datetime
from threading import Thread

import cv2
import imutils
import numpy as np

from naturewatch_camera_server.file_saver import FileSaver


class ChangeDetector(Thread):

    def __init__(self, camera_controller, config, logger):
        super(ChangeDetector, self).__init__()
        self.config = config
        self.daemon = True
        self.cancelled = False

        self.camera_controller = camera_controller

        self.logger = logger
        if self.logger is None:
            self.logger = logging

        self.file_saver = FileSaver(self.config, logger=self.logger)

        self.min_width = self.config["min_width"]
        self.max_width = self.config["max_width"]
        self.min_height = self.config["min_height"]
        self.max_height = self.config["max_height"]

        self.device_time = None
        self.device_time_start = None

        self.mode = "inactive"
        self.session_start_time = None
        self.avg = None
        self.last_photo_time = self.get_fake_time()
        self.number_of_photos = 0

        self.active_colour = (255, 255, 0)
        self.inactive_colour = (100, 100, 100)
        self.is_min_active = False
        self.current_image = None

        self.timelapse_active = False
        self.timelapse = self.config["default_timelapse"]

        self.logger.info("ChangeDetector: initialised")

    def run(self):
        """
        Main run function
        :return: none
        """
        while not self.cancelled:
            try:
                self.update()
            except Exception as error:
                self.logger.exception(error)

    def cancel(self):
        """
        Cancel thread
        :return: none
        """
        self.cancelled = True
        self.camera_controller.stop()

    # @staticmethod
    # def save_photo(image):
    #     """
    #     Save numpy image to a jpg file
    #     :param image: numpy array image
    #     :return: none
    #     """
    #     timestamp = datetime.datetime.now()
    #     filename = f"{timestamp.strftime('%Y-%m-%d-%H-%M-%S')}.jpg"

    #     try:
    #         cv2.imwrite(f"photos/{filename}", image)
    #     except Exception as error:
    #         self.logger.error('ChangeDetector: save_photo() error: ')
    #         self.logger.exception(error)

    def detect_change_contours(self, img):
        """
        Detect changed contours in frame
        :param img: current image
        :return: True if it's time to capture
        """
        # convert to gray
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.avg is None:
            self.avg = gray.copy().astype("float")
            return False

        # add to accumulation model and find the change
        cv2.accumulateWeighted(gray, self.avg, 0.5)
        frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(self.avg))

        # threshold, dilate and find contours
        thresh = cv2.threshold(frame_delta, self.config["delta_threshold"],
                               255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

        # find largest contour
        largest_contour = self.get_largest_contour(cnts)

        if largest_contour is None:
            return False

        _, _, width, height = cv2.boundingRect(largest_contour)

        # if the contour is too small or too big, return false
        if (width < self.min_width or height < self.min_height or
                width > self.max_width or height > self.max_height):
            return False

        time_interval = self.get_fake_time() - self.last_photo_time
        if time_interval >= self.config['min_photo_interval_s']:
            return True

        return False

    @staticmethod
    def get_largest_contour(contours):
        """
        Get the largest contour in a list of contours
        :param contours: a list of contours
        :return: the largest contour object
        """
        if not contours:
            return None
        else:
            areas = [cv2.contourArea(c) for c in contours]
            return contours[np.argmax(areas)]

    def set_sensitivity(self, min_width, max_width):
        self.max_height = max_width
        self.min_height = min_width
        self.max_width = max_width
        self.min_width = min_width

    def start_photo_session(self):
        self.logger.info('ChangeDetector: starting photo capture')
        self.mode = "photo"
        self.session_start_time = self.get_fake_time()

    def start_video_session(self):
        self.logger.info('ChangeDetector: starting video capture')
        self.mode = "video"
        self.camera_controller.start_video_stream()
        self.session_start_time = self.get_fake_time()

    def start_timelapse_session(self):
        self.logger.info('ChangeDetector: starting timelapse capture')
        self.mode = "timelapse"
        self.session_start_time = self.get_fake_time()

    def stop_session(self):
        self.logger.info('ChangeDetector: ending capture')
        if self.mode == "video":
            self.camera_controller.stop_video_stream()
        # Not useful
        # elif self.mode == "photo" or self.mode == "timelapse":
        #     pass
        self.mode = "inactive"

    # TODO: whether to use the video-port or not does not directly
    # depend on the mode
    # In case video is requested, the video port will always be used for both
    # resolutions
    # In case photo is requested, the video port can be used, but need not.
    # It should be left a matter of configuration
    def update(self):
        time.sleep(0.02)
        # only check for motion while a session is active
        if self.mode in ["photo", "video"]:
            # get an md image
            img = self.camera_controller.get_md_image()

            # only proceed if there is an image
            if img is not None:
                if self.detect_change_contours(img) is True:
                    self.logger.info(
                        "ChangeDetector: detected motion. Starting capture..."
                    )
                    timestamp = self.get_formatted_time()
                    if self.mode == "photo":
                        image = self.camera_controller.get_hires_image()
                        self.file_saver.save_image(image, timestamp)
                        self.file_saver.save_thumb(
                            imutils.resize(
                                image, width=self.config["md_width"]),
                            timestamp,
                            self.mode,
                        )
                        self.last_photo_time = self.get_fake_time()
                        self.logger.info(
                            "ChangeDetector: photo capture completed")

                    elif self.mode == "video":
                        self.file_saver.save_thumb(img, timestamp, self.mode)
                        self.camera_controller.wait_recording(
                            self.config["video_duration_after_motion"])
                        self.logger.info(
                            "ChangeDetector: video capture completed")

                        with self.camera_controller.get_video_stream().lock:
                            self.file_saver.save_video(
                                self.camera_controller.get_video_stream(),
                                timestamp,
                            )

                        self.last_photo_time = self.get_fake_time()
                        self.logger.debug("ChangeDetector: video timer reset")
                    else:
                        # TODO: Add debug code that logs a line
                        # every x seconds so we can see the ChangeDetector
                        # is still alive:
                        # self.logger.debug("ChangeDetector: idle")
                        pass
            else:
                self.logger.error("ChangeDetector: not receiving any images "
                                  "for motion detection!")
                time.sleep(1)

        # TODO: implement periodic pictures
        elif self.mode == "timelapse":
            # take one picture every minute
            if self.get_fake_time() - self.last_photo_time >= self.timelapse:
                self.logger.info(
                    f"ChangeDetector: {self.timelapse} s elapsed -> "
                    "capturing...")
                # TODO: no magic numbers! (make it configurable)
                timestamp = self.get_formatted_time()
                image = self.camera_controller.get_hires_image()
                self.file_saver.save_image(image, timestamp)
                self.file_saver.save_thumb(
                    imutils.resize(image, width=self.config["md_width"]),
                    timestamp,
                    self.mode,
                )
                self.last_photo_time = self.get_fake_time()
                self.logger.info("ChangeDetector: photo capture completed")

    def get_fake_time(self):
        if self.device_time is None:
            return time.time()
        return self.device_time + time.time() - self.device_time_start

    def get_formatted_time(self):
        current_time = datetime.utcfromtimestamp(self.get_fake_time())
        return current_time.strftime('%Y-%m-%d-%H-%M-%S')