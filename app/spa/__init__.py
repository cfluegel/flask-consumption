from flask import Blueprint

spa_bp = Blueprint('spa', __name__)

from . import routes  # noqa: E402,F401
