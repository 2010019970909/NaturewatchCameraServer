import datetime
import os
import time

import pytest

from naturewatch_camera_server import create_app
from naturewatch_camera_server.file_saver import FileSaver

FILE_SAVER = None
APP = None


@pytest.fixture(autouse=True, scope="session")
def run_around_tests():
    global FILE_SAVER
    global APP
    APP = create_app()
    FILE_SAVER = FileSaver(APP.user_config)
    testing_client = APP.test_client()

    while APP.camera_controller.is_alive() is False:
        APP.camera_controller.start()
        time.sleep(1)

    # Establish application context
    ctx = APP.app_context()
    ctx.push()

    yield testing_client

    APP.camera_controller.stop()

    ctx.pop()


def test_image_save():
    """
    GIVEN a FileSaver instance
    WHEN an image is saved
    THEN the image should exist in the file system and should not be empty
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    filename = FILE_SAVER.save_image(APP.camera_controller.get_md_image(), timestamp)
    assert os.path.isfile(APP.user_config["photos_path"] + filename)
    assert os.path.getsize(APP.user_config["photos_path"] + filename) != 0
    os.remove(APP.user_config["photos_path"] + filename)


def test_check_storage():
    """
    GIVEN a FileSaver instance
    WHEN check_storage is called
    THEN percentage of available storage should be returned
    """
    assert FILE_SAVER.check_storage() <= 100
