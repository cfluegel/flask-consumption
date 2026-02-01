from flask import Blueprint

pwa_bp = Blueprint('pwa', __name__,
                   template_folder='templates',
                   static_folder='static',
                   url_prefix='/pwa')

from . import routes
