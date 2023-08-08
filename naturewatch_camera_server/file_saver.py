# -*- coding: utf-8 -*-
"""Module for saving images and videos to disk in a separate thread."""
# import datetime
import logging
import os

# import zipfile
from subprocess import call
from threading import Thread

import cv2
import psutil


class FileSaver(Thread):
    """Class for saving images and videos to disk in a separate thread."""

    def __init__(self, config, logger=None):
        """Initialise FileSaver class with config and logger.
        :param config: config dictionary
        :param logger: logger object
        """
        super().__init__()

        self.logger = logger
        if self.logger is None:
            self.logger = logging

        self.config = config

        # Scale down factor for thumbnail images
        self.thumbnail_factor = (
            self.config["tn_width"] / self.config["img_width"]
        )

    def check_storage(self):
        """Check how much storage space is used.
        :return: percentage of storage space used
        """
        # Disk information
        percent = psutil.disk_usage("/").percent
        self.logger.debug(f"FileSaver: {percent} % of storage space used.")
        return percent

    # TODO: merge save functions
    # def save_file(self, image, timestamp):
    def save_image(self, image, timestamp):
        """Save image to disk
        :param image: numpy array image
        :param timestamp: formatted timestamp string
        :return: filename
        """
        if self.check_storage() >= 99:
            self.logger.error("FileSaver: not enough space to save image")
            return None

        filename = f"{timestamp}.jpg"
        self.logger.debug("FileSaver: saving file")

        try:
            path = os.path.join(self.config["photos_path"], filename)
            cv2.imwrite(path, image)
            self.logger.info("FileSaver: saved file to %s", path)
            return filename

        except cv2.error as error:
            self.logger.error("FileSaver: save_image() error: ")
            self.logger.exception(error)
            return None

    def save_thumb(self, image, timestamp, media_type):
        """Save thumbnail image to disk.
        :param image: numpy array image
        :param timestamp: formatted timestamp string
        :param media_type: media type (photo, video, timelapse)
        :return: filename
        """
        filename = f"thumb_{timestamp}.jpg"
        self.logger.debug(f'FileSaver: saving thumb "{filename}"')

        try:
            # TODO: downscaling should be done here.
            if media_type in ("photo", "timelapse"):
                # TODO: Build a proper downscaling routine for the thumbnails
                # self.logger.debug(
                # 'Scaling by a factor of {}'.format(self.thumbnail_factor))
                # thumb = cv2.resize(
                #     image, 0, fx=self.thumbnail_factor,
                #     fy=self.thumbnail_factor, interpolation=cv2.INTER_AREA)
                path = os.path.join(self.config["photos_path"], filename)
            else:
                path = os.path.join(self.config["videos_path"], filename)

            cv2.imwrite(path, image)
            self.logger.info("FileSaver: saved thumbnail to %s", path)
            return filename

        except cv2.error as error:
            self.logger.error("FileSaver: save_thumb() error: ")
            self.logger.exception(error)
            return None

    def save_video(self, stream, timestamp):
        """Save raw video stream to disk.
        :param stream: raw picamera stream object
        :param timestamp: formatted timestamp string
        :return: none
        """
        if self.check_storage() >= 99:
            self.logger.error("FileSaver: not enough space to save video")
            return None

        filename = f"{timestamp}.h264"
        filename_mp4 = f"{timestamp}.mp4"
        input_video = os.path.join(self.config["videos_path"], filename)
        output_video = os.path.join(self.config["videos_path"], filename_mp4)

        self.logger.info("FileSaver: Writing video...")
        stream.copy_to(input_video, seconds=15)
        call(
            [
                "MP4Box",
                "-fps",
                str(self.config["frame_rate"]),
                "-add",
                input_video,
                output_video,
            ]
        )
        self.logger.info(f'FileSaver: done writing video "{filename}"')

        os.remove(input_video)
        self.logger.debug(f'FileSaver: removed interim file "{filename}"')

        return filename_mp4

    # Not used at the moment
    # @staticmethod
    # def download_all_video():
    #     """Create a zip file from all video files.
    #     :return: filename of the zip file
    #     """
    #     timestamp = datetime.datetime.now()
    #     filename = f"video_{timestamp.strftime('%Y-%m-%d-%H-%M-%S')}"
    #     return filename.strip()

    # Not used at the moment
    # def download_zip(self, filename):
    #     """Create a zip file from a video file.
    #     :param filename: filename of the video file
    #     :return: filename of the zip file
    #     """
    #     input_file = os.path.join(self.config["videos_path"], filename)
    #     output_zip = f"{input_file}.zip"

    #     with zipfile.ZipFile(output_zip, mode='w') as zip_file:
    #         self.logger.info('FileSaver: adding file')
    #         zip_file.write(input_file, os.path.basename(input_file))
    #         self.logger.info('FileSaver: closing')

    #     return output_zip
