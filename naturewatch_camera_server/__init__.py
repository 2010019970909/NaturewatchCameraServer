#!../venv/bin/python
# -*- coding: utf-8 -*-
"""Initialise the naturewatch camera server."""
import json
import logging
import os

# from logging.handlers import RotatingFileHandler
from shutil import copyfile

from flask import Flask

from naturewatch_camera_server.api import api
from naturewatch_camera_server.camera_controller import CameraController
from naturewatch_camera_server.change_detector import ChangeDetector
from naturewatch_camera_server.data import data
from naturewatch_camera_server.file_saver import FileSaver
from naturewatch_camera_server.static_page import static_page


def extract_config(app):
    """Extract config from config.json file.
    :param app: Flask app object
    :return: Flask app object, module path, camera log path
    """
    # Retrieve module path
    module_path = os.path.abspath(os.path.dirname(__file__))
    app.logger.info("Module path: %s", module_path)

    # Load configuration json
    # load central config file first
    config_path = os.path.join(module_path, "config.json")
    with open(config_path, encoding="utf-8") as json_file:
        app.user_config = json.load(json_file)

    data_path = app.user_config["data_path"]
    user_config_path = os.path.join(module_path, data_path, "config.json")
    camera_log_path = os.path.join(module_path, data_path, "camera.log")

    # Check if a config file exists in data directory
    if os.path.isfile(user_config_path):
        # if yes, load that file, too
        app.logger.info("Using config file from data context")
        with open(user_config_path, encoding="utf-8") as json_file:
            app.user_config = json.load(json_file)
    else:
        # if not, copy central config file to data directory
        app.logger.warning(
            "Config file does not exist within the data "
            "context, copying file"
        )
        copyfile(config_path, user_config_path)
    return app, module_path, camera_log_path


def create_app():
    """
    Create flask app
    :return: Flask app object
    """
    # Setup blueprints, static and template folders
    flask_app = Flask(
        __name__,
        static_folder="static/client/build",
        template_folder="static/client/build",
    )
    flask_app.register_blueprint(api, url_prefix="/api")
    flask_app.register_blueprint(data, url_prefix="/data")
    flask_app.register_blueprint(static_page)

    # Setup logger
    flask_app.logger = logging.getLogger(__name__)
    flask_app.logger.setLevel(logging.DEBUG)
    # setup logging handler for stderr
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.INFO)
    flask_app.logger.addHandler(stderr_handler)

    # Load config file
    flask_app, module_path, camera_log_path = extract_config(flask_app)

    # Set up logging to file
    file_handler = logging.handlers.RotatingFileHandler(
        camera_log_path,
        maxBytes=1024000,
        backupCount=5,
    )
    file_handler.setLevel(logging.INFO)
    log_level = flask_app.user_config["log_level"]
    numeric_loglevel = getattr(logging, log_level.upper(), None)

    if not isinstance(numeric_loglevel, int):
        flask_app.logger.info(
            "Invalid log level in config file: %s", log_level
        )
    else:
        file_handler.setLevel(numeric_loglevel)

    logging_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(logging_format)
    file_handler.setFormatter(formatter)
    flask_app.logger.addHandler(file_handler)
    flask_app.logger.info("Logging to file initialised")

    # Find photos and videos paths
    # TODO: check what ?
    flask_app.user_config["photos_path"] = os.path.join(
        module_path, flask_app.user_config["photos_path"]
    )
    flask_app.logger.info(
        "Photos path: %s",
        flask_app.user_config["photos_path"],
    )
    if os.path.isdir(flask_app.user_config["photos_path"]) is False:
        os.mkdir(flask_app.user_config["photos_path"])
        flask_app.logger.warning(
            "Photos directory does not exist, creating path"
        )
    flask_app.user_config["videos_path"] = os.path.join(
        module_path, flask_app.user_config["videos_path"]
    )
    if os.path.isdir(flask_app.user_config["videos_path"]) is False:
        os.mkdir(flask_app.user_config["videos_path"])
        flask_app.logger.warning(
            "Videos directory does not exist, creating path"
        )

    # Instantiate classes
    # Camera controller is only used in the ChangeDetector class
    flask_app.camera_controller = CameraController(
        flask_app.logger, flask_app.user_config
    )
    flask_app.logger.debug("Instantiating classes...")
    flask_app.change_detector = ChangeDetector(
        flask_app.camera_controller, flask_app.user_config, flask_app.logger
    )
    flask_app.file_saver = FileSaver(flask_app.user_config, flask_app.logger)

    flask_app.logger.debug("Initialisation finished")
    return flask_app


def create_error_app(error):
    """
    Create flask app about an error occurred in the main app
    :return: Flask app object
    """
    flask_app = Flask(__name__, static_folder="static/client/build")

    @flask_app.route("/")
    def index():
        return (
            "<html><body><h1>Unable to start NaturewatchCameraServer.</h1>"
            f"An error occurred:<pre>{error}</pre></body></html>"
        )

    return flask_app
