# -*- coding: utf-8 -*-
"""Test the data blueprint."""
import datetime
import json
import os
import time

import pytest

from naturewatch_camera_server import create_app
from naturewatch_camera_server.file_saver import FileSaver

PHOTOS_LIST = []
VIDEOS_LIST = []
PHOTOS_THUMB_LIST = []
VIDEOS_THUMB_LIST = []


@pytest.fixture(scope="session")
def test_client():
    """Test client for the Flask application.
    :return: Flask test client
    """
    app = create_app()
    testing_client = app.test_client()

    # Establish application context
    ctx = app.app_context()
    ctx.push()

    file_saver = FileSaver(app.user_config)

    # Start camera controller
    while app.camera_controller.is_alive() is False:
        app.camera_controller.start()
        time.sleep(1)

    # Take 2 photos and record their filenames
    for _ in range(2):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        thumb = file_saver.save_thumb(
            app.camera_controller.get_md_image(), timestamp, "photo"
        )
        filename = file_saver.save_image(
            app.camera_controller.get_hires_image(), timestamp
        )
        PHOTOS_LIST.append(filename)
        PHOTOS_THUMB_LIST.append(thumb)
        time.sleep(1)

    # Record videos and save their filenames.
    app.camera_controller.start_video_stream()
    for _ in range(2):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        time.sleep(2)
        thumb = file_saver.save_thumb(
            app.camera_controller.get_md_image(), timestamp, "video"
        )
        app.camera_controller.wait_recording(2)
        with app.camera_controller.get_video_stream().lock:
            filename = file_saver.save_video(
                app.camera_controller.get_video_stream(), timestamp
            )
            VIDEOS_LIST.append(filename)
            VIDEOS_THUMB_LIST.append(thumb)
            time.sleep(1)

    yield testing_client

    # Teardown
    for file in PHOTOS_LIST:
        os.remove(app.user_config["photos_path"] + file)
    for file in VIDEOS_LIST:
        os.remove(app.user_config["videos_path"] + file)
    for file in PHOTOS_THUMB_LIST:
        os.remove(app.user_config["photos_path"] + file)
    for file in VIDEOS_THUMB_LIST:
        os.remove(app.user_config["videos_path"] + file)

    app.camera_controller.stop()

    ctx.pop()


def test_photos(testing_client):
    """
    GIVEN a Flask application
    WHEN '/data/photos' is requested (GET)
    THEN list of photos should be returned.
    """
    response = testing_client.get("/data/photos")
    assert response.status_code == 200
    response_list = json.loads(response.data.decode("utf8"))
    assert isinstance(response_list, list)
    for file in PHOTOS_LIST:
        assert file in response_list


def test_photo(testing_client):
    """
    GIVEN a Flask application
    WHEN '/data/photo/<photo>' is requested (GET)
    THEN a single photo should be returned.
    """
    response = testing_client.get("/data/photos/" + PHOTOS_LIST[0])
    assert response.status_code == 200


def test_delete_photo(testing_client):
    """
    GIVEN a Flask application
    WHEN '/data/photo/<photo>' is requested (GET)
    THEN a single photo should be returned.
    """
    response = testing_client.delete("/data/photos/" + PHOTOS_LIST[0])
    assert response.status_code == 200
    response_dict = json.loads(response.data.decode("utf8"))
    assert response_dict["SUCCESS"] == PHOTOS_LIST[0]
    del PHOTOS_LIST[0]
    del PHOTOS_THUMB_LIST[0]


def test_videos(testing_client):
    """
    GIVEN a Flask application
    WHEN '/data/videos' is requested (GET)
    THEN list of videos should be returned.
    """
    response = testing_client.get("/data/videos")
    assert response.status_code == 200
    response_list = json.loads(response.data.decode("utf8"))
    assert isinstance(response_list, list)
    for file in VIDEOS_LIST:
        assert file in response_list


def test_video(testing_client):
    """
    GIVEN a Flask application
    WHEN '/data/video/<video>' is requested (GET)
    THEN a single video should be returned.
    """
    response = testing_client.get("/data/videos/" + VIDEOS_LIST[0])
    assert response.status_code == 200


def test_delete_video(testing_client):
    """
    GIVEN a Flask application
    WHEN '/data/video/<video>' is requested (GET)
    THEN a single video should be returned.
    """
    response = testing_client.delete("/data/videos/" + VIDEOS_LIST[0])
    assert response.status_code == 200
    response_dict = json.loads(response.data.decode("utf8"))
    assert response_dict["SUCCESS"] == VIDEOS_LIST[0]
    del VIDEOS_LIST[0]
    del VIDEOS_THUMB_LIST[0]
