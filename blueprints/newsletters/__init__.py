"""Newsletter blueprint initialization."""
from flask import Blueprint

newsletters_bp = Blueprint('newsletters', __name__)

from . import routes
