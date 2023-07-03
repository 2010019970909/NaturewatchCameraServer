"""This module contains the api endpoints for the camera server."""
# TODO: create "getSpace" api call when filesaver is global
import subprocess
import time

from flask import Blueprint, Response, current_app, json, redirect, request

api = Blueprint('api', __name__)


@api.route('/feed')
def feed():
    """
    Feed endpoint
    :return: mjpg content
    """
    current_app.logger.info("Serving camera feed...")
    with current_app.app_context():
        return Response(generate_mjpg(current_app.camera_controller),
                        mimetype='multipart/x-mixed-replace; boundary=frame')


def generate_mjpg(camera_controller):
    """
    Generate mjpg response using camera_controller
    :return: Yield string with jpeg byte array and content type
    """
    while camera_controller.is_alive() is False:
        camera_controller.start()
        time.sleep(1)

    while camera_controller.is_alive():
        latest_frame = camera_controller.get_image_binary()
        response = b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + \
            bytearray(latest_frame) + b'\r\n'
        yield response
        time.sleep(0.2)


@api.route('/frame')
def frame():
    """
    Frame endpoint
    :return: jpg content
    """
    current_app.logger.info("Requested camera frame.")
    return Response(generate_jpg(current_app.camera_controller))


def generate_jpg(camera_controller):
    """
    Generate jpg response once.
    :return: String with jpeg byte array and content type
    """
    # Start camera controller if it hasn't been started already.
    while camera_controller.is_alive() is False:
        camera_controller.start()
        time.sleep(1)
    try:
        latest_frame = camera_controller.get_image_binary()
        response = b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + \
            bytearray(latest_frame) + b'\r\n'
        return response

    except Exception as error:  # pylint: disable=broad-except
        # TODO send a error.jpg image as the frame instead.
        current_app.logger.warning("Could not retrieve image binary.")
        current_app.logger.exception(error)
        return b'Empty'


@api.route('/settings', methods=['GET', 'POST'])
def settings_handler():
    """
    Settings endpoint
    :return: settings json object
    """
    if request.method == 'GET':
        settings = construct_settings_object(
            current_app.camera_controller, current_app.change_detector)
        return Response(json.dumps(settings), mimetype='application/json')

    if request.method == 'POST':
        settings = request.json
        if "rotation" in settings:
            current_app.camera_controller.set_camera_rotation(
                settings["rotation"])

        if "sensitivity" in settings:
            if settings["sensitivity"] == "less":
                current_app.change_detector.set_sensitivity(
                    current_app.user_config["less_sensitivity"],
                    current_app.user_config["max_width"])

            elif settings["sensitivity"] == "default":
                current_app.change_detector.set_sensitivity(
                    current_app.user_config["min_width"],
                    current_app.user_config["max_width"])

            elif settings["sensitivity"] == "more":
                current_app.change_detector.set_sensitivity(
                    current_app.user_config["more_sensitivity"],
                    current_app.user_config["max_width"])

        if "mode" in settings["exposure"]:
            if settings["exposure"]["mode"] == "auto":
                current_app.camera_controller.auto_exposure()

            elif settings["exposure"]["mode"] == "off":
                if settings["exposure"]["shutter_speed"] == 0:
                    settings["exposure"]["shutter_speed"] = 5000
                current_app.camera_controller.set_exposure(
                    settings["exposure"]["shutter_speed"],
                    settings["exposure"]["iso"])

        if "timelapse" in settings:
            current_app.logger.info(
                "Changing timelapse settings to %s seconds.",
                settings["timelapse"]
            )
            current_app.change_detector.timelapse_active = settings[
                "timelapse"]["active"]
            current_app.change_detector.timelapse = settings[
                "timelapse"]["interval"]

        new_settings = construct_settings_object(
            current_app.camera_controller, current_app.change_detector)
        return Response(json.dumps(new_settings), mimetype='application/json')

    return Response("Invalid request method.", status=400)


def construct_settings_object(camera_controller, change_detector):
    """
    Construct a dictionary populated with the current settings
    of the camera controller and change detector.
    :param camera_controller: Running camera controller object
    :param change_detector: Running change detector object
    :return: settings dictionary
    """

    sensitivity = "default"
    less_sensitivity = current_app.user_config["less_sensitivity"]
    min_width = current_app.user_config["min_width"]
    more_sensitivity = current_app.user_config["more_sensitivity"]

    if change_detector.min_width == less_sensitivity:
        sensitivity = "less"

    elif change_detector.min_width == min_width:
        sensitivity = "default"

    elif change_detector.min_width == more_sensitivity:
        sensitivity = "more"

    settings = {
        "rotation": camera_controller.rotated_camera,
        "exposure": {
            "mode": camera_controller.get_exposure_mode(),
            "iso": camera_controller.get_iso(),
            "shutter_speed": camera_controller.get_shutter_speed(),
        },
        "sensitivity": sensitivity,
        "timelapse": {
            "active": current_app.change_detector.timelapse_active,
            "interval": current_app.change_detector.timelapse,
        }
    }
    return settings


@api.route('/session')
def get_session():
    """
    Get session status
    :return: session status json object
    """
    session_status = {
        "mode": current_app.change_detector.mode,
        "time_started": current_app.change_detector.session_start_time
    }
    return Response(json.dumps(session_status), mimetype='application/json')


@api.route('/session/start/<session_type>', methods=['POST'])
def start_session_handler(session_type):
    """
    Start session of type photo or video
    :return: session status json object
    """
    current_app.change_detector.start_session(session_type)

    session_status = {
        "mode": current_app.change_detector.mode,
        "time_started": current_app.change_detector.session_start_time
    }
    return Response(json.dumps(session_status), mimetype='application/json')


@api.route('/session/stop', methods=['POST'])
def stop_session_handler():
    """
    Stop running session
    :return: session status json object
    """
    current_app.change_detector.stop_session()
    session_status = {
        "mode": current_app.change_detector.mode,
        "time_started": current_app.change_detector.session_start_time
    }
    return Response(json.dumps(session_status), mimetype='application/json')


@api.route('/time/<time_string>', methods=['POST'])
def update_time(time_string):
    """
    Update device time
    :param time_string: time string
    :return: json response
    """
    if current_app.change_detector.device_time is not None:
        return Response(
            '{"NOT_MODIFIED": "' + time_string + '"}',
            status=304, mimetype='application/json')

    if float(time_string) > 1580317004:
        current_app.change_detector.device_time = float(time_string)
        current_app.change_detector.device_time_start = time.time()
        return Response(
            '{"SUCCESS": "' + time_string + '"}',
            status=200, mimetype='application/json')

    return Response(
        '{"ERROR": "' + time_string + '"}',
        status=400, mimetype='application/json')


@api.route('/version')
@api.route('/version/<argument>')
@api.route('/version/redirect_to/<destination>')
def get_version(argument: str = 'date', destination: str = ''):
    """Get the current version of the software.
    :param argument: The argument to return. Can be one of:
        - 'date': The date of the current commit
        - 'hash': The full hash of the current commit
        - 'short_hash': The short hash of the current commit
        - 'url': The URL of the remote repository
        - 'commit_url': The URL of the current commit
    :param destination: If not empty, the URL to redirect to.
    :return: The requested argument.
    """
    if destination != '' and 'url' in destination:
        return redirect(get_version(destination))

    if argument == 'hash':
        return git('rev-parse', 'HEAD')

    if argument == 'short_hash':
        return git('rev-parse', '--short', 'HEAD')

    if argument == 'url':
        return git('remote', 'get-url', 'origin')

    if argument == 'commit_url':
        url = git('remote', 'get-url', 'origin')
        if url.endswith('.git'):
            url = url[:url.rfind('.git')]
        commit_hash = git('rev-parse', 'HEAD')
        return f'{url}/commit/{commit_hash}'

    # Default: return the date of the current commit
    commit_hash = git('rev-parse', 'HEAD')
    return git('show', '-s', r'--format=%ci', commit_hash)


def git(*parameters: str):
    """Run a git command.
    :param parameters: The parameters to pass to git.
    :return: The output of the git command.
    """
    command = ['git']
    command.extend(parameters)

    git_result = subprocess.run(command, stdout=subprocess.PIPE, check=False)
    return git_result.stdout.decode('utf-8').replace('\n', '')


@api.route('/reboot')
def reboot():
    """Reboot the device.
    :return: A message to display to the user.
    """
    # TODO: redirect to / after 1 or 2 minutes.
    try:
        return "Rebooting (refresh the page in 1 or 2 minutes)."
    finally:
        time.sleep(3)
        maintenance('reboot')


@api.route('/shutdown')
def shutdown():
    """Shutdown the device.
    :return: A message to display to the user.
    """
    # TODO: announce shutdown and add a delay of 5 seconds, then shutdown.
    try:
        return "Shutdown ..."
    finally:
        time.sleep(3)
        maintenance('shutdown', 'now')


def maintenance(*parameters: str):
    """Run a maintenance command.
    :param parameters: The parameters to pass to the command.
    :return: The output of the command.
    """
    # The service is already started has root...
    command = ['sudo']
    command.extend(parameters)

    git_result = subprocess.run(command, stdout=subprocess.PIPE, check=False)
    return git_result.stdout.decode('utf-8').replace('\n', '')
