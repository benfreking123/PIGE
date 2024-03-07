from . import web_blueprint

@web_blueprint.route('/')
def index():
    return "Home Page"