"""WSGI entrypoint used by Gunicorn inside the container.

Run locally with::

    flask --app wsgi run --debug
    # or
    gunicorn --bind 0.0.0.0:5000 wsgi:app
"""

from app import create_app

app = create_app()

if __name__ == "__main__":  # pragma: no cover - local development helper
    app.run(host="0.0.0.0", port=5000, debug=False)
