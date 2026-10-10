"""Auslieferung der gebauten React-SPA (frontend/dist).

Catch-all für Client-Side-Routing: existierende Dateien werden direkt
ausgeliefert, alles andere bekommt index.html. Fehlt der Build, erscheint
ein Hinweis statt eines 500ers (z.B. in Tests ohne npm-Build).
"""
import os

from flask import send_from_directory

from . import spa_bp

DIST_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'dist')
)

MISSING_BUILD_HINT = (
    '<h1>Frontend-Build fehlt</h1>'
    '<p>Bitte <code>cd frontend && npm install && npm run build</code> ausführen.</p>',
    503,
)


@spa_bp.route('/', defaults={'path': ''})
@spa_bp.route('/<path:path>')
def serve(path):
    if not os.path.exists(os.path.join(DIST_DIR, 'index.html')):
        return MISSING_BUILD_HINT

    full_path = os.path.join(DIST_DIR, path)
    if path and os.path.isfile(full_path):
        return send_from_directory(DIST_DIR, path)

    return send_from_directory(DIST_DIR, 'index.html')
