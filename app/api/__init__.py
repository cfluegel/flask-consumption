from functools import wraps

from flask import Blueprint, current_app, jsonify, request

api_bp = Blueprint('api', __name__, template_folder='templates', static_folder='static')


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != current_app.config.get('API_KEY'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


from . import routes
