import datetime
import logging
import os
import zipfile
from subprocess import call
from threading import Thread

import cv2
import psutil


class FileSaver(Thread):

    def __init__(self, config, logger=None):
        super(FileSaver, self).__init__()

        self.logger = logger
        if self.logger is None:
            self.logger = logging

        self.config = config

        # Scaledown factor for thumbnail images
        self.thumbnail_factor = self.config["tn_width"] / self.config["img_width"]

    def check_storage(self):
        # Disk information
        percent = psutil.disk_usage('/').percent
        self.logger.debug(f'FileSaver: {percent} % of storage space used.')
        return percent

    def save_image(self, image, timestamp):
        """
        Save image to disk
        :param image: numpy array image
        :param timestamp: formatted timestamp string
        :return: filename
        """
        if self.check_storage() < 99:
            filename = f'{timestamp}.jpg'
            self.logger.debug('FileSaver: saving file')

            try:
                path = os.path.join(self.config["photos_path"], filename)
                cv2.imwrite(path, image)
                self.logger.info(f"FileSaver: saved file to {path}")
                return filename

            except Exception as error:
                self.logger.error('FileSaver: save_photo() error: ')
                self.logger.exception(error)
        else:
            self.logger.error('FileSaver: not enough space to save image')
            return None

    def save_thumb(self, image, timestamp, media_type):
        filename = f'thumb_{timestamp}.jpg'
        self.logger.debug(f'FileSaver: saving thumb "{filename}"')

        try:
            if media_type in ["photo", "timelapse"]:
            # TODO: Build a proper downscaling routine for the thumbnails
            # self.logger.debug(
            #     'Scaling by a factor of {}'.format(self.thumbnail_factor))
            # thumb = cv2.resize(
            #     image, 0, fx=self.thumbnail_factor,
            #     fy=self.thumbnail_factor, interpolation=cv2.INTER_AREA)
                path = os.path.join(self.config["photos_path"], filename)
            else:
                path = os.path.join(self.config["videos_path"], filename)

            cv2.imwrite(path, image)
            self.logger.info("FileSaver: saved thumbnail to {path}")
            return filename

        except Exception as error:
            self.logger.error('FileSaver: save_photo() error: ')
            self.logger.exception(error)

    def save_video(self, stream, timestamp):
        """
        Save raw video stream to disk
        :param stream: raw picamera stream object
        :param timestamp: formatted timestamp string
        :return: none
        """
        if self.check_storage() < 99:
            filename = f"{timestamp}.h264"
            filename_mp4 = f"{timestamp}.mp4"
            input_video = os.path.join(self.config["videos_path"], filename)
            output_video = os.path.join(self.config["videos_path"], filename_mp4)

            self.logger.info('FileSaver: Writing video...')
            stream.copy_to(input_video, seconds=15)
            call([
                "MP4Box",
                "-fps",
                str(self.config["frame_rate"]),
                "-add",
                input_video,
                output_video,
            ])
            self.logger.info(f'FileSaver: done writing video "{filename}"')

            os.remove(input_video)
            self.logger.debug(f'FileSaver: removed interim file "{filename}"')

            return filename_mp4
        else:
            self.logger.error('FileSaver: not enough space to save video')
            return None

    @staticmethod
    def download_all_video():
        timestamp = datetime.datetime.now()
        filename = f"video_{timestamp.strftime('%Y-%m-%d-%H-%M-%S')}"
        return filename.strip()

    def download_zip(self, filename):
        input_file = os.path.join(self.config["videos_path"], filename)
        output_zip = f"{input_file}.zip"
        zip_file = zipfile.ZipFile(output_zip, mode='w')

        try:
            self.logger.info('FileSaver: adding file')
            zip_file.write(input_file, os.path.basename(input_file))
        finally:
            self.logger.info('FileSaver: closing')
            zip_file.close()

        return output_zip
