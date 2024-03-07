from flask import Flask
from .routes import web_blueprint
import os


def create_flask_app():
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Move up two levels to the project root
    project_root = os.path.join(current_dir, '..', '..')

    # Construct absolute paths for templates and static folders
    template_dir = os.path.abspath(os.path.join(project_root, 'var', 'templates'))
    static_dir = os.path.abspath(os.path.join(project_root, 'var', 'static'))

    #Start Flask App
    app = Flask(__name__,
                template_folder=template_dir,
                static_folder=static_dir)
    # Adding Web page Routes
    app.register_blueprint(web_blueprint)

    return app