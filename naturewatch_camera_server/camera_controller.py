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
    import picamera2
    import libcamera
    # import picamera.array
except ImportError:
    # well, picamera2 should be compatible with
    # USB cameras... so IDK
    picamera2 = None


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

        # For video, need to extract bitrate from config
        if picamera2 is not None:
            self.camera_encoder = picamera2.encoders.H264Encoder(
                self.config.get("video_bitrate", 10000000))

            self.camera_output = picamera2.outputs.CircularOutput(
                buffersize=self.config.get("circular_output_buffer_size", 300),
            )

        self.camera = None
        self.rotated_camera = False

        # Non picamera attributes
        self.iso = None
        self.shutter_speed = None
        self.exposure_mode = None

        if picamera2 is not None:
            # Use picamera2
            self.logger.info("CameraController: picamera2 module exists.")
            self.initialise_picamera2()
        else:
            # Use webcam (OpenCV)
            self.logger.info(
                "CameraController: picamera2 module not found. "
                "Using OpenCV VideoCapture instead."
            )
            self.capture = None
            self.initialise_webcam()

        self.image = None

    # Main routine
    def run(self):
        """Run camera controller.
        :return: None
        """

        # time.sleep(15)

        # def get_formatted_time():
        #     """Get the formatted time.
        #     :return: the formatted time
        #     """
        #     from datetime import datetime
        #     current_time = datetime.utcfromtimestamp(time.time())
        #     return current_time.strftime('%Y-%m-%d-%H-%M-%S')

        # # Now when it's time to start recording the output,
        # # including the previous x seconds:
        # timestamp = get_formatted_time()
        # filename = f"{timestamp}.h264"
        # # filename_mp4 = f"{timestamp}.mp4"
        # import os
        # input_video = os.path.join(
        #     self.config["videos_path"], filename)

        # self.camera_output.fileoutput = input_video
        # print(f"Start recording to {input_video}")
        # self.camera_output.start()
        # time.sleep(5)
        # self.camera_output.stop()
        # print("Done recording")

        while not self.is_stopped():
            try:
                if picamera2 is not None:
                    try:
                        # Get image from Pi camera
                        self.image = self.camera.capture_array('main')

                        if self.image is None:
                            self.logger.warning(
                                "CameraController: got empty image.")
                        time.sleep(0.01)

                    except Exception as error:  # pylint: disable=broad-except
                        self.logger.error(
                            "CameraController: picamera2 update error.")
                        self.logger.exception(error)
                        self.initialise_picamera2()
                        time.sleep(0.02)

                else:
                    try:
                        # Get image from webcam (OpenCV)
                        _, frame = self.capture.read()
                        if frame is None:
                            self.logger.warning(
                                "CameraController: got empty webcam image.")
                        else:
                            self.image = imutils.resize(
                                frame,
                                width=self.md_width,
                                height=self.md_height
                            )
                        time.sleep(0.01)

                    except cv2.error as error:
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

        if picamera2 is not None:
            # Close pi camera
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
            md_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
            return md_image.copy()
        return None

    # Get MD image in binary jpeg encoding format
    def get_image_binary(self):
        """Get MD image in binary jpeg encoding format.
        :return: MD image in binary jpeg encoding format
        """
        return cv2.imencode(".jpg", self.get_md_image())[1]

    # def get_video_stream(self):
    #     """Get video stream.
    #     :return: video stream or None if no video stream is available.
    #     """
    #     if picamera2 is not None:
    #         return self.picamera_video_stream
    #     return None

    def start_video_stream(self):
        """Start video stream.
        :return: None
        """
        if picamera2 is not None:
            # print("Begin CircularIO")
            # Need to create config for circular buffer size (base on fps)

            # print("bitrate", self.video_bitrate)
            # self.picamera_video_stream.clear()
            # self.camera.start_recording(
            #     self.picamera_video_stream,
            #     format='h264',
            #     bitrate=self.video_bitrate,
            # )
            self.logger.debug('CameraController: recording started')

    def stop_video_stream(self):
        """Stop video stream.
        :return: None
        """
        if picamera2 is not None:
            self.camera.stop_recording()
            self.logger.debug('CameraController: recording stopped')

    def wait_recording(self, delay):
        """Wait recording.
        :param delay: delay
        :return: None
        """
        if picamera2 is not None:
            return self.camera.wait_recording(delay)
        return None

    # TODO: Not used?
    def get_thumb_image(self):
        """Get thumbnail image.
        :return: thumbnail image
        """
        self.logger.debug("CameraController: lores image requested.")
        if picamera2 is not None:
            return self.get_image_binary()
        return None

    # Get high res image
    def get_hires_image(self):
        """Get high resolution image.
        :return: high resolution image
        """
        self.logger.debug("CameraController: hires image requested.")
        if picamera2 is not None:
            # Configure camera for hires image
            capture_config = self.camera.create_still_configuration()

            # Get image from Pi camera
            image_array = self.camera.switch_mode_and_capture_array(
                capture_config,
            )

            image_array = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)

            if image_array is not None:
                return image_array.copy()

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
    def initialise_picamera2(self):
        """Initialise picamera.
        :return: None
        """
        self.logger.debug('CameraController: initialising picamera...')

        # If there is already a running instance, close it
        if self.camera is not None:
            self.camera.close()

        # Create a new instance
        self.camera = picamera2.Picamera2()

        # self.logger.debug(
        #     'CameraController: camera detected:\n'
        #     f'\tsensor format: {self.camera.sensor_format}'
        #     f'\tsensor modes: {self.camera.sensor_modes}'
        #     f'\tsensor resolution: {self.camera.sensor_resolution}'
        # )

        # Set camera parameters
        # TODO: configure
        # self.camera.framerate = self.config["frame_rate"]
        # self.camera.resolution = (self.width, self.height)

        # self.camera.rotation = 0
        self.rotated_camera = False
        camera_transform = libcamera.Transform()

        if self.config["rotate_camera"] == 1:
            # self.camera.rotation = 180
            self.rotated_camera = True
            camera_transform = libcamera.Transform(hflip=True, vflip=True)

        # print(self.camera.sensor_modes)
        config = self.camera.create_video_configuration(
            transform=camera_transform,
            buffer_count=self.config.get('camera_buffer_count', 8),
            queue=self.config.get('camera_queue', True),
            encode=self.config.get('camera_encode', 'lores'),
            lores=self.config.get('camera_lores', {"size": (1920, 1080)}),
            main=self.config.get('camera_main', {"size": (2028, 1520)}),
        )

        # Ensure the resolution are chosen optimally
        self.camera.align_configuration(config)

        self.camera.configure(config)
        # self.camera.set_controls({"ExposureTime": 10000, "AnalogueGain": 1.0})

        self.camera.start_recording(
            self.camera_encoder, self.camera_output)
        # self.camera.start()

        # capture an image
        # save an image to ~/test.jpg
        # self.camera.capture_file('test.jpg', 'main')

        # self.logger.info(
        #     'CameraController: camera initialised with a resolution of '
        #     f'{self.camera.resolution} and a framerate of '
        #     f'{self.camera.framerate}'
        # )

        # self.logger.debug(
        #     'CameraController: low resolution stream prepared with resolution'
        #     f': {self.md_width}×{self.md_height}.'
        # )

        # Set up high resolution stream for actual recording
        # Bitrate has to be specified so size can be calculated
        # from the seconds specified
        # Unfortunately the effective bitrate depends
        # on the quality-parameter specified with start_recording,
        # so the effective duration can not be predicted well
        # stream_duration = self.config["video_duration_before_motion"]
        # stream_duration += self.config["video_duration_after_motion"]

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
            if picamera2 is not None:
                self.camera.rotation = 180
            new_config = self.config
            new_config["rotate_camera"] = 1

        else:
            if picamera2 is not None:
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
        if picamera2 is not None:
            self.camera.iso = iso
            time.sleep(0.5)  # it takes more time to set up the ISO
            self.camera.shutter_speed = shutter_speed
            self.camera.exposure_mode = 'off'
            gains = self.camera.awb_gains
            self.camera.awb_mode = 'off'
            # Restore stored gains
            self.camera.awb_gains = gains
        else:
            # Well, it serves no use
            self.iso = iso
            self.shutter_speed = shutter_speed
            self.exposure_mode = 'off'

    def get_exposure_mode(self):
        """Get exposure mode.
        :return: exposure mode
        """
        if picamera2 is not None:
            print(f'{self.camera.controls}')
            return "TODO get exposure mode"
        return self.exposure_mode

    def get_iso(self):
        """Get camera iso.
        :return: iso
        """
        if picamera2 is not None:
            # return self.camera.iso
            return "TODO get iso"
        return self.iso

    def get_shutter_speed(self):
        """Get camera shutter speed.
        :return: shutter speed
        """
        if picamera2 is not None:
            return "TODO get shutter speed"
        return self.shutter_speed

    def auto_exposure(self):
        """
        Set picamera exposure to auto
        :return: none
        """
        if picamera2 is not None:
            # TODO: picamera2 auto exposure
            # self.camera.iso = 0
            # self.camera.shutter_speed = 0
            # self.camera.exposure_mode = 'auto'
            # self.camera.awb_mode = 'auto'
            pass
        else:
            # Kind of useless
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
