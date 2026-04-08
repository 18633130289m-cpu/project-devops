from flask import Flask

from api import api_bp, setup_app_data


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    setup_app_data()
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
