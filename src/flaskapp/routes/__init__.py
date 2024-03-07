from flask import Blueprint

web_blueprint = Blueprint('web_blueprint', __name__)

from .web import *
