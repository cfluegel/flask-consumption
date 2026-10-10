from flask import Blueprint

web_api_bp = Blueprint('web_api', __name__)

from . import routes  # noqa: E402,F401
