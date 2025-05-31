from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    """Home page with navigation to all tools."""
    return render_template('home.html')