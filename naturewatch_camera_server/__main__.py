# import os
import argparse
# import subprocess
import traceback

from naturewatch_camera_server import create_app, create_error_app

# TODO: instantiate the logger here, so that it can be used here and in the app.
# probably need to pass it to the app and to fetch the config for the log file path.
parser = argparse.ArgumentParser(
    description='Launch My Naturewatch Camera'
)
parser.add_argument(
    '-p',
    action='store',
    dest='port',
    default=5000,
    help='Port number to attach to',
)
args = parser.parse_args()


# class CameraNotFoundException(Exception):
#     """Exception raised when the camera is not found."""

#     def __init__(self, message="Camera not found"):
#         """Initialize the exception.
#         :param message: The error message.
#         :type message: str
#         """
#         self.message = message
#         super().__init__(self.message)


# def is_camera_enabled():
#     # inspired by https://stackoverflow.com/questions/58250817/raspberry-pi-camera-module-check-if-connected#comment102874971_58250817
#     vcgencmd_result = subprocess.run(
#         ['vcgencmd', 'get_camera'], stdout=subprocess.PIPE)
#     result_text = vcgencmd_result.stdout.decode('utf-8').strip()
#     # Split parameters and remove unwanted coma
#     result_text = result_text.replace(',', '').split(' ')
#     # Only keep parameters with equal sign
#     result_text = [parameter for parameter in result_text if '=' in parameter]

#     properties = dict(pair.split('=') for pair in result_text)
#     return properties['supported'] == '1'


if __name__ == '__main__':
    try:
        app = create_app()
        app.camera_controller.start()
        app.change_detector.start()

    # VS: I understand why this is here, but I'm not sure
    # it's the best solution.
    except Exception as error:
        # if "Camera is not enabled" in str(error):
        # This error message appears even if the camera _is_ enabled, but the camera is not found.
        # e.g. due to a connection problem.
        # We don't want to mislead users into messing with raspi-config, so check if the
        # camera interface is really disabled.
        # if (is_camera_enabled()):
        #     error = CameraNotFoundException(
        #         "Unable to access camera. Is the cable properly connected?")
        error = traceback.format_exc()
        print(f'{error = }')

        app = create_error_app(error)

    app.run(debug=False, threaded=True, port=args.port, host='0.0.0.0')
