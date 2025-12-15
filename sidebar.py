from flask import Blueprint, render_template

sidebar_bp = Blueprint('sidebar', __name__)

@sidebar_bp.route('/sidebar')
def sidebar():
    # Aquí podrías pasar imágenes específicas si lo deseas
    return render_template('sidebar.html')
