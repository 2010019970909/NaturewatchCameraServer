# -*- coding: utf-8 -*-
"""Module for static page endpoints."""
import os

from flask import (
    Blueprint,
    Response,
    current_app,
    render_template,
    send_from_directory,
)

from .api import get_version

static_page = Blueprint("static_page", __name__)
version_hash = get_version("short_hash")
version_date = get_version("date")[:11]


@static_page.route("/", defaults={"path": ""})
@static_page.route("/<path:path>")
def serve(path):
    """
    Static root endpoint
    :return: index.html or file requested
    """
    static_path = os.path.join(current_app.static_folder, path)

    if path != "" and os.path.exists(static_path):
        return send_from_directory(current_app.static_folder, path)

    if path == "" or "gallery" in path:
        return render_template(
            "index.html",
            version_hash=version_hash,
            version_date=version_date,
        )

    return Response("Page not found. Please check the URL!", status=404)
