import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, PasswordField
from wtforms.validators import DataRequired
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from authlib.integrations.flask_client import OAuth
import secrets

# Konfigurasi Upload Gambar dan OAuth
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)

# Konfigurasi Authlib (Google OAuth)
oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)

# Inisialisasi Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=True) # Tambahkan kolom Google ID
    email = db.Column(db.String(100), unique=True, nullable=True)     # Tambahkan kolom email
    is_admin = db.Column(db.Boolean, default=False)                   # Tandai user sebagai admin

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.String(20), nullable=False, default=datetime.utcnow().strftime('%d %B %Y'))

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(100), nullable=True)

class HomePage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    intro_title = db.Column(db.String(100), nullable=False)
    intro_subtitle = db.Column(db.String(150), nullable=False)
    profile_pic = db.Column(db.String(100), nullable=True)

class AboutPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bio_text = db.Column(db.Text, nullable=False)
    skills = db.Column(db.Text, nullable=False)

# --- Forms ---
class LoginForm(FlaskForm):
    # Form ini tidak akan digunakan untuk Google Login, tapi tetap dipertahankan jika ingin login manual
    email = StringField('Email', validators=[DataRequired()])
    submit = SubmitField('Login')

# ... sisa Forms (PostForm, ProjectForm, dll) tetap sama ...

# Fungsi untuk memeriksa ekstensi file yang diizinkan
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes Publik ---
# ... (Semua rute publik tetap sama) ...

# --- Routes Login/Logout ---
@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('home'))

@app.route('/login/google')
def login_google():
    return oauth.google.authorize_redirect(url_for('auth_google', _external=True))

@app.route('/auth/google')
def auth_google():
    try:
        token = oauth.google.authorize_access_token()
        resp = oauth.google.get('userinfo')
        user_info = resp.json()
        
        user = User.query.filter_by(google_id=user_info['id']).first()
        if not user:
            # Jika user belum ada, buat user baru
            user = User(google_id=user_info['id'], email=user_info['email'], is_admin=True) # Semua yang login via Google dianggap admin
            db.session.add(user)
            db.session.commit()
        
        login_user(user)
        flash('Login berhasil!', 'success')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Login gagal: {e}', 'danger')
        return redirect(url_for('login'))

# --- Routes Admin (CRUD) ---
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin: # Verifikasi apakah user yang login adalah admin
        flash('Anda tidak memiliki akses ke halaman ini.', 'danger')
        logout_user()
        return redirect(url_for('home'))
    posts = Post.query.all()
    projects = Project.query.all()
    return render_template('admin/dashboard.html', posts=posts, projects=projects)

# ... (Semua rute admin lainnya tetap sama dengan tambahan decorator @login_required) ...

# Inisialisasi database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Pastikan Anda sudah mengatur variabel lingkungan untuk CLIENT_ID dan CLIENT_SECRET
    # Contoh: export GOOGLE_CLIENT_ID='...'
    # Contoh: export GOOGLE_CLIENT_SECRET='...'
    app.run(debug=True)
