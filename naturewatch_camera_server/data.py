# -*- coding: utf-8 -*-
"""The data module contains all the routes for getting and deleting data."""
import os

from flask import (
    Blueprint,
    Response,
    current_app,
    json,
    request,
    send_from_directory,
)

from .zipfile_generator import ZipfileGenerator

data = Blueprint("data", __name__)


@data.route("/photos")
def get_photos():
    """Get a list of photos.
    :return: A response object.
    """
    photos_list = construct_directory_list(
        current_app, current_app.user_config["photos_path"]
    )
    return Response(json.dumps(photos_list), mimetype="application/json")


@data.route("/videos")
def get_videos():
    """Get a list of videos.
    :return: A response object.
    """
    videos_list = construct_directory_list(
        current_app, current_app.user_config["videos_path"]
    )
    return Response(json.dumps(videos_list), mimetype="application/json")


@data.route("/photos/<filename>")
def get_photo(filename):
    """Get a photo file.
    :param filename: The name of the file to get.
    :return: A response object.
    """
    file_path = current_app.user_config["photos_path"] + filename
    if os.path.isfile(os.path.join(file_path)):
        return send_from_directory(
            os.path.join("static/data/photos"), filename, mimetype="image/jpg"
        )

    return Response(
        "{'NOT_FOUND':'" + filename + "'}",
        status=404,
        mimetype="application/json",
    )


@data.route("/photos/<filename>", methods=["DELETE"])
# TODO: create a unique delete function for videos and photos (see below)
def delete_photo(filename):
    """Delete a photo file.
    :param filename: The name of the file to delete.
    :return: A response object.
    """
    file_path = current_app.user_config["photos_path"] + filename
    thumb_path = f'{current_app.user_config["photos_path"]}thumb_{filename}'

    if os.path.isfile(os.path.join(file_path)):
        os.remove(file_path)
        os.remove(thumb_path)
        if os.path.isfile(os.path.join(file_path)) is False:
            return Response(
                '{"SUCCESS": "' + filename + '"}',
                status=200,
                mimetype="application/json",
            )

    return Response(
        '{"ERROR": "' + filename + '"}',
        status=500,
        mimetype="application/json",
    )


@data.route("/videos/<filename>")
def get_video(filename):
    """Get a video file.
    :param filename: The name of the file to get.
    :return: A response object.
    """
    file_path = current_app.user_config["videos_path"] + filename

    if not os.path.isfile(os.path.join(file_path)):
        return Response(
            "{'NOT_FOUND':'" + filename + "'}",
            status=404,
            mimetype="application/json",
        )

    if filename.endswith(".jpg"):
        return send_from_directory(
            os.path.join("static/data/videos"),
            filename,
            mimetype="image/jpg",
        )

    return send_from_directory(
        os.path.join("static/data/videos"),
        filename,
        mimetype="video/mp4",
    )


@data.route("/videos/<filename>", methods=["DELETE"])
# TODO: create a unique delete function for videos and photos
def delete_video(filename):
    """Delete a video file.
    :param filename: The name of the file to delete.
    :return: A response object.
    """
    file_path = current_app.user_config["videos_path"] + filename
    thumb_path = current_app.user_config["videos_path"] + "thumb_" + filename
    thumb_path = thumb_path.replace(".mp4", ".jpg")

    # It only checks for the video file, not the thumbnail
    if os.path.isfile(os.path.join(file_path)):
        os.remove(file_path)
        os.remove(thumb_path)
        if os.path.isfile(os.path.join(file_path)) is False:
            return Response(
                '{"SUCCESS": "' + filename + '"}',
                status=200,
                mimetype="application/json",
            )

    # TODO: this should be more specific
    return Response(
        '{"ERROR": "' + filename + '"}',
        status=500,
        mimetype="application/json",
    )


def generate_files_list(path, paths_list):
    """Generate a list of files from a given list of paths.
    :param path: The path to get the files from.
    :param paths_list: The list of paths to get the files from.
    :return: The list of files.
    """
    return list(
        map(
            lambda fn: {"filename": os.path.join(path, fn), "arcname": fn},
            paths_list,
        )
    )


def get_all_files(app, src_path):
    """Get all files in a given directory.
    :param src_path: The path to get the files from.
    :return: The list of files.
    """
    # TODO: just for now... we should take an array of file names
    src_list = construct_directory_list(app, src_path)
    return generate_files_list(src_path, src_list)


@data.route("/download/videos.zip", methods=["POST", "GET"])
def download_videos():
    """Download a zip file of all videos.
    :return: The zip file of all videos in a response.
    """
    videos_path = current_app.user_config["videos_path"]
    if request.is_json:
        body = request.get_json()
        paths = generate_files_list(videos_path, body["paths"])
    else:
        paths = get_all_files(current_app, videos_path)

    return Response(
        ZipfileGenerator(paths).get(),
        mimetype="application/zip",
    )


@data.route("/download/photos.zip", methods=["POST", "GET"])
def download_photos():
    """Download a zip file of all photos.
    :return: The zip file of all photos in a response.
    """
    photos_path = current_app.user_config["photos_path"]

    if request.is_json:
        body = request.get_json()
        paths = generate_files_list(photos_path, body["paths"])

    else:
        paths = get_all_files(current_app, photos_path)

    return Response(ZipfileGenerator(paths).get(), mimetype="application/zip")


def construct_directory_list(app, path):
    """Construct a list of files in a given directory.
    :param path: The path to construct the list for.
    :return: The list of files.
    """
    # TODO: refactor using filters
    files = [
        f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))
    ]
    files = [f for f in files if f.lower().endswith((".jpg", ".mp4"))]
    files = [f for f in files if not f.lower().startswith("thumb_")]
    files.sort(
        key=lambda f: os.path.getmtime(
            os.path.join(get_correct_filepath(app, f))
        ),
        reverse=True,
    )
    return files


def get_correct_filepath(app, path):
    """Get the expended filepath for a given path.
    :param path: The path to get the expended filepath for.
    :return: The expended filepath.
    """
    if path.lower().endswith(".jpg"):
        return os.path.join(app.user_config["photos_path"], path)

    if path.lower().endswith(".mp4"):
        return os.path.join(app.user_config["videos_path"], path)

    return None
