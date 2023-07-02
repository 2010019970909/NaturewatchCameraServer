"""Camera controller module."""
import io
import json
import logging
import os
import threading
import time

import cv2
import imutils
import numpy as np

try:
    import picamera
    import picamera.array
except ImportError:
    picamera = None


class CameraController(threading.Thread):
    """Camera controller class."""

    def __init__(self, logger, config):
        """Initialise camera controller.
        :param logger: logger object
        :param config: config object
        """
        threading.Thread.__init__(self)
        self._stop_event = threading.Event()
        self.cancelled = False

        self.logger = logger
        if self.logger is None:
            self.logger = logging

        self.config = config

        # Desired image resolution
        self.width = self.config["img_width"]
        self.height = self.config["img_height"]

        # Image resolution used for motion detection,
        # same aspect ratio as desired image
        self.md_width = self.config["md_width"]
        self.md_height = self.md_width * self.height // self.width

        # TODO: this parameter should only be required in case of photo-mode
        self.use_video_port = self.config["use_video_port"]

        # For photos
        self.picamera_photo_stream = None

        # For motion detection
        self.picamera_md_output = None
        self.picamera_md_stream = None

        # For video
        self.picamera_video_stream = None
        self.video_bitrate = 10000000

        self.camera = None
        self.rotated_camera = False

        # Non picamera attributes
        self.iso = None
        self.shutter_speed = None
        self.exposure_mode = None
        self.raw_image = None

        if picamera is not None:
            # Use pi camera
            self.logger.info("CameraController: picamera module exists.")
            self.initialise_picamera()
        else:
            # Use webcam
            self.logger.info(
                "CameraController: picamera module not found. "
                "Using OpenCV VideoCapture instead."
            )
            self.capture = None
            self.initialise_webcam()

        self.image = None
        self.hires_image = None

    # Main routine
    def run(self):
        """Run camera controller.
        :return: None
        """
        while not self.is_stopped():
            try:
                if picamera is not None:
                    try:
                        # Get image from Pi camera
                        self.picamera_md_output.truncate(0)
                        self.picamera_md_output.seek(0)
                        next(self.picamera_md_stream)
                        self.image = self.picamera_md_output.array
                        if self.image is None:
                            self.logger.warning(
                                "CameraController: got empty image.")
                        time.sleep(0.01)
                    except Exception as error:  # pylint: disable=broad-except
                        self.logger.error(
                            "CameraController: picamera update error.")
                        self.logger.exception(error)
                        self.initialise_picamera()
                        time.sleep(0.02)

                else:
                    try:
                        # Get image from webcam
                        _, self.raw_image = self.capture.read()
                        if self.raw_image is None:
                            self.logger.warning(
                                "CameraController: got empty webcam image.")
                        else:
                            self.image = imutils.resize(
                                self.raw_image,
                                width=self.md_width,
                                height=self.md_height
                            )
                        time.sleep(0.01)

                    except (cv2.error, Exception) as error:  # pylint: disable=broad-except
                        self.logger.error(
                            "CameraController: webcam update error.")
                        self.logger.exception(error)
                        self.initialise_webcam()
                        time.sleep(0.02)

            except KeyboardInterrupt:
                self.logger.info(
                    "CameraController: received KeyboardInterrupt, shutting "
                    "down ..."
                )
                self.stop()

    # Stop thread
    def stop(self):
        """Stop thread.
        :return: None
        """
        self._stop_event.set()

        if picamera is not None:
            # Close pi camera
            self.picamera_md_output.truncate(0)
            self.picamera_md_output.seek(0)
            self.camera.close()
            self.camera = None
        else:
            # Close webcam
            self.capture.release()

        self.logger.info('CameraController: cancelling ...')

    # Check if thread is stopped
    def is_stopped(self):
        """Check if thread is stopped.
        :return: True if thread is stopped, False otherwise.
        """
        return self._stop_event.is_set()

    # Get MD image
    def get_md_image(self):
        """Get MD image.
        :return: MD image or None if no image is available.
        """
        if self.image is not None:
            return self.image.copy()
        return None

    # Get MD image in binary jpeg encoding format
    def get_image_binary(self):
        """Get MD image in binary jpeg encoding format.
        :return: MD image in binary jpeg encoding format
        """
        _, buf = cv2.imencode(".jpg", self.get_md_image())
        return buf

    def get_video_stream(self):
        """Get video stream.
        :return: video stream or None if no video stream is available.
        """
        if picamera is not None:
            return self.picamera_video_stream
        return None

    def start_video_stream(self):
        """Start video stream.
        :return: None
        """
        if picamera is not None:
            self.picamera_video_stream.clear()
            self.camera.start_recording(
                self.picamera_video_stream,
                format='h264',
                bitrate=self.video_bitrate,
            )
            self.logger.debug('CameraController: recording started')

    def stop_video_stream(self):
        """Stop video stream.
        :return: None
        """
        if picamera is not None:
            self.camera.stop_recording()
            self.logger.debug('CameraController: recording stopped')

    def wait_recording(self, delay):
        """Wait recording.
        :param delay: delay
        :return: None
        """
        if picamera is not None:
            return self.camera.wait_recording(delay)
        return None

    # TODO: Not used?
    def get_thumb_image(self):
        """Get thumbnail image.
        :return: thumbnail image
        """
        self.logger.debug("CameraController: lores image requested.")
        if picamera is not None:
            return self.get_image_binary()
        return None

    # Get high res image
    def get_hires_image(self):
        """Get high resolution image.
        :return: high resolution image
        """
        self.logger.debug("CameraController: hires image requested.")
        if picamera is not None:
            # TODO: understand the decode.
            # Is another more intuitive way possible?
            self.picamera_photo_stream = io.BytesIO()
            self.camera.capture(
                self.picamera_photo_stream,
                format='jpeg',
                use_video_port=self.use_video_port,
            )
            self.picamera_photo_stream.seek(0)
            # "Decode" the image from the stream, preserving colour
            decoded_image = cv2.imdecode(np.fromstring(
                self.picamera_photo_stream.getvalue(), dtype=np.uint8), 1)

            if decoded_image is not None:
                return decoded_image.copy()
            return None

        # By default, get image from webcam
        _, raw_image = self.capture.read()
        if raw_image is None:
            self.logger.error(
                "CameraController: webcam returned empty hires image.")
            return None
        return raw_image.copy()

    # Initialise picamera. If already started, close and reinitialise.
    # TODO - reset with manual exposure, if it was set before.
    def initialise_picamera(self):
        """Initialise picamera.
        :return: None
        """
        self.logger.debug('CameraController: initialising picamera...')

        # If there is already a running instance, close it
        if self.camera is not None:
            self.camera.close()

        # Create a new instance
        self.camera = picamera.PiCamera()
        # Check for module revision
        # TODO: set maximum resolution based on module revision
        self.logger.debug(
            f'CameraController: camera module revision {self.camera.revision}'
            ' detected.'
        )

        # Set camera parameters
        self.camera.framerate = self.config["frame_rate"]
        self.camera.resolution = (self.width, self.height)

        picamera.PiCamera.CAPTURE_TIMEOUT = 60

        self.camera.rotation = 0
        self.rotated_camera = False

        if self.config["rotate_camera"] == 1:
            self.camera.rotation = 180
            self.rotated_camera = True

        self.logger.info(
            'CameraController: camera initialised with a resolution of '
            f'{self.camera.resolution} and a framerate of '
            f'{self.camera.framerate}'
        )

        # TODO: use correct port fitting the requested resolution
        # Set up low res stream for motion detection
        self.picamera_md_output = picamera.array.PiRGBArray(
            self.camera,
            size=(self.md_width, self.md_height),
        )
        self.picamera_md_stream = self.camera.capture_continuous(
            self.picamera_md_output,
            format="bgr",
            use_video_port=True,
            splitter_port=2,
            resize=(self.md_width, self.md_height),
        )
        self.logger.debug(
            'CameraController: low resolution stream prepared with resolution'
            f': {self.md_width}×{self.md_height}.'
        )

        # Set up high resolution stream for actual recording
        # Bitrate has to be specified so size can be calculated
        # from the seconds specified
        # Unfortunately the effective bitrate depends
        # on the quality-parameter specified with start_recording,
        # so the effective duration can not be predicted well
        stream_duration = self.config["video_duration_before_motion"]
        stream_duration += self.config["video_duration_after_motion"]

        self.picamera_video_stream = picamera.PiCameraCircularIO(
            self.camera,
            bitrate=self.video_bitrate,
            seconds=stream_duration)
        self.logger.debug(
            'CameraController: circular stream prepared for video.')

        time.sleep(2)

    # initialise webcam
    def initialise_webcam(self):
        """Initialise webcam.
        :return: None
        """
        if self.capture is not None:
            self.capture.release()

        self.capture = cv2.VideoCapture(0)

        self.shutter_speed = 0
        self.exposure_mode = "auto"
        self.iso = "auto"

        self.logger.info("CameraController: preparing capture...")
        self.capture.set(3, self.width)
        self.capture.set(4, self.height)

    # Set camera rotation
    def set_camera_rotation(self, rotation):
        """Set camera rotation.
        :param rotation: rotation
        :return: None
        """
        # Only change the configuration when the camera rotation change
        if self.rotated_camera == rotation:
            return

        self.rotated_camera = rotation
        module_path = os.path.abspath(os.path.dirname(__file__))
        user_config_path = os.path.join(
            module_path, self.config["data_path"], 'config.json')

        if self.rotated_camera is True:
            if picamera is not None:
                self.camera.rotation = 180
            new_config = self.config
            new_config["rotate_camera"] = 1

        else:
            if picamera is not None:
                self.camera.rotation = 0
            new_config = self.config
            new_config["rotate_camera"] = 0

        self.config = self.update_config(new_config, user_config_path)

    # Set picamera exposure
    def set_exposure(self, shutter_speed, iso):
        """Set picamera exposure.
        :param shutter_speed: shutter speed
        :param iso: iso
        :return: None
        """
        if picamera is not None:
            self.camera.iso = iso
            time.sleep(0.5)
            self.camera.shutter_speed = shutter_speed
            self.camera.exposure_mode = 'off'
            gains = self.camera.awb_gains
            self.camera.awb_mode = 'off'
            # Restore stored gains
            self.camera.awb_gains = gains
        else:
            self.iso = iso
            self.shutter_speed = shutter_speed
            self.exposure_mode = 'off'

    def get_exposure_mode(self):
        """Get exposure mode.
        :return: exposure mode
        """
        if picamera is not None:
            return self.camera.exposure_mode
        return self.exposure_mode

    def get_iso(self):
        """Get camera iso.
        :return: iso
        """
        if picamera is not None:
            return self.camera.iso
        return self.iso

    def get_shutter_speed(self):
        """Get camera shutter speed.
        :return: shutter speed
        """
        if picamera is not None:
            return self.camera.shutter_speed
        return self.shutter_speed

    def auto_exposure(self):
        """
        Set picamera exposure to auto
        :return: none
        """
        if picamera is not None:
            self.camera.iso = 0
            self.camera.shutter_speed = 0
            self.camera.exposure_mode = 'auto'
            self.camera.awb_mode = 'auto'
        else:
            self.iso = 'auto'
            self.shutter_speed = 0
            self.exposure_mode = 'auto'

    @staticmethod
    def update_config(new_config, config_path):
        """Update config.
        :param new_config: new config
        :param config_path: config path
        :return: new config
        """
        contents = json.dumps(
            new_config, sort_keys=True, indent=4, separators=(',', ': '))
        with open(config_path, 'w', encoding='utf-8') as config_file:
            config_file.write(contents)
        return new_config
