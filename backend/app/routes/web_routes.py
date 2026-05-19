from flask import Blueprint, render_template

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def home():
    return render_template('upload.html')

@web_bp.route('/processing')
def processing():
    return render_template('previews.html')

@web_bp.route('/workspace/<id>')
def workspace(id):
    return render_template('main.html')

@web_bp.route('/login')
def login():
    return render_template('login.html')
