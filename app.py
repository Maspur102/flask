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
from sqlalchemy import inspect
import time
import logging
from flask_session import Session # Import Flask-Session

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurasi Upload Gambar dan OAuth
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Inisialisasi SQLAlchemy DULU
db = SQLAlchemy(app)

# Konfigurasi Sesi untuk keamanan dan stabilitas CSRF
app.config['SESSION_TYPE'] = 'sqlalchemy' # Menggunakan SQLAlchemy untuk menyimpan sesi
app.config['SESSION_SQLALCHEMY'] = db # Sekarang 'db' sudah didefinisikan
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Inisialisasi Flask-Session SETELAH db didefinisikan
sess = Session(app)

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
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

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
    email = StringField('Email', validators=[DataRequired()])
    submit = SubmitField('Login')

class PostForm(FlaskForm):
    title = StringField('Judul', validators=[DataRequired()])
    content = TextAreaField('Konten', validators=[DataRequired()])
    submit = SubmitField('Simpan Post')

class ProjectForm(FlaskForm):
    description = TextAreaField('Deskripsi', validators=[DataRequired()])
    submit = SubmitField('Simpan Proyek')

class HomePageForm(FlaskForm):
    intro_title = StringField('Judul Intro', validators=[DataRequired()])
    intro_subtitle = TextAreaField('Sub-judul Intro', validators=[DataRequired()])
    submit = SubmitField('Simpan Perubahan')

class AboutPageForm(FlaskForm):
    bio_text = TextAreaField('Biografi', validators=[DataRequired()])
    skills = TextAreaField('Daftar Keahlian (dipisah dengan koma)', validators=[DataRequired()])
    submit = SubmitField('Simpan Perubahan')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes Publik ---
@app.route('/')
def home():
    posts = Post.query.order_by(Post.id.desc()).limit(3).all()
    homepage_data = HomePage.query.first()
    return render_template('home.html', posts=posts, homepage_data=homepage_data)

@app.route('/blog')
def blog():
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template('blog.html', posts=posts)

@app.route('/portfolio')
def portfolio():
    projects = Project.query.order_by(Project.id.desc()).all()
    return render_template('portfolio.html', projects=projects)

@app.route('/about')
def about():
    about_data = AboutPage.query.first()
    homepage_data = HomePage.query.first()
    return render_template('about.html', about_data=about_data, homepage_data=homepage_data)

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
    redirect_uri = url_for('auth_google', _external=True, _scheme='https')
    logger.info(f"Redirecting to Google with URI: {redirect_uri}")
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google')
def auth_google():
    try:
        logger.info(f"GOOGLE_CLIENT_ID: {os.environ.get('GOOGLE_CLIENT_ID')}")
        logger.info(f"GOOGLE_CLIENT_SECRET: {'*' * len(os.environ.get('GOOGLE_CLIENT_SECRET')) if os.environ.get('GOOGLE_CLIENT_SECRET') else 'None'}")
        redirect_uri = url_for('auth_google', _external=True, _scheme='https')
        logger.info(f"Attempting to fetch token with redirect URI: {redirect_uri}")

        token = oauth.google.authorize_access_token()
        logger.info(f"Token fetched successfully: {token}")
        resp = oauth.google.get('userinfo')
        user_info = resp.json()
        logger.info(f"User info from Google: {user_info}")
        
        user = User.query.filter_by(google_id=user_info['id']).first()
        if not user:
            if User.query.count() == 0:
                user = User(google_id=user_info['id'], email=user_info['email'], is_admin=True)
                flash('Akun admin berhasil dibuat dengan Google Anda!', 'success')
            else:
                user = User(google_id=user_info['id'], email=user_info['email'], is_admin=False)
                flash('Anda tidak memiliki izin admin.', 'danger')
                return redirect(url_for('home'))
            
            db.session.add(user)
            db.session.commit()
        
        if not user.is_admin:
            flash('Anda tidak memiliki izin admin.', 'danger')
            return redirect(url_for('home'))

        login_user(user)
        flash('Login berhasil!', 'success')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        logger.error(f"Login Gagal: {e}", exc_info=True)
        flash(f'Login gagal: {e}', 'danger')
        return redirect(url_for('login'))

# --- Routes Admin (CRUD) ---
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Anda tidak memiliki akses ke halaman ini.', 'danger')
        logout_user()
        return redirect(url_for('home'))
    posts = Post.query.all()
    projects = Project.query.all()
    return render_template('admin/dashboard.html', posts=posts, projects=projects)

@app.route('/admin/post/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if not current_user.is_admin: return redirect(url_for('home'))
    form = PostForm()
    if form.validate_on_submit():
        new_post = Post(title=form.title.data, content=form.content.data)
        db.session.add(new_post)
        db.session.commit()
        flash('Postingan berhasil dibuat!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/create_post.html', form=form)

@app.route('/admin/post/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    if not current_user.is_admin: return redirect(url_for('home'))
    post = Post.query.get_or_404(post_id)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Postingan berhasil diperbarui!', 'success')
        return redirect(url_for('admin_dashboard'))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('admin/edit_post.html', form=form, post=post)

@app.route('/admin/post/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    if not current_user.is_admin: return redirect(url_for('home'))
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Postingan berhasil dihapus!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/project/create', methods=['GET', 'POST'])
@login_required
def create_project():
    if not current_user.is_admin: return redirect(url_for('home'))
    form = ProjectForm()
    if form.validate_on_submit():
        image_file = None
        if 'project_image' in request.files:
            file = request.files['project_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_file = filename
            else:
                flash('Format gambar tidak diizinkan atau tidak ada gambar diunggah.', 'danger')
                return render_template('admin/create_project.html', form=form)
        else:
            flash('Anda harus mengunggah gambar untuk proyek.', 'danger')
            return render_template('admin/create_project.html', form=form)
        
        new_project = Project(
            description=form.description.data,
            image_file=image_file
        )
        db.session.add(new_project)
        db.session.commit()
        flash('Proyek berhasil dibuat!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/create_project.html', form=form)

@app.route('/admin/project/edit/<int:project_id>', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    if not current_user.is_admin: return redirect(url_for('home'))
    project = Project.query.get_or_404(project_id)
    form = ProjectForm()
    if form.validate_on_submit():
        if 'project_image' in request.files:
            file = request.files['project_image']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                if project.image_file:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], project.image_file))
                    except OSError:
                        pass
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                project.image_file = filename
            elif file.filename == '' and not project.image_file:
                flash('Anda harus mengunggah gambar untuk proyek.', 'danger')
                return render_template('admin/edit_project.html', form=form, project=project)
        
        project.description = form.description.data
        db.session.commit()
        flash('Proyek berhasil diperbarui!', 'success')
        return redirect(url_for('admin_dashboard'))
    elif request.method == 'GET':
        form.description.data = project.description
    return render_template('admin/edit_project.html', form=form, project=project)

@app.route('/admin/project/delete/<int:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
    if not current_user.is_admin: return redirect(url_for('home'))
    project = Project.query.get_or_404(project_id)
    if project.image_file:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], project.image_file))
        except OSError:
            pass
    db.session.delete(project)
    db.session.commit()
    flash('Proyek berhasil dihapus!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/home/edit', methods=['GET', 'POST'])
@login_required
def edit_home():
    if not current_user.is_admin: return redirect(url_for('home'))
    homepage = HomePage.query.first()
    if not homepage:
        homepage = HomePage(intro_title='Judul Default', intro_subtitle='Sub-judul Default', profile_pic='default.png')
        db.session.add(homepage)
        db.session.commit()
    
    form = HomePageForm(obj=homepage)
    if form.validate_on_submit():
        form.populate_obj(homepage)

        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                if homepage.profile_pic and homepage.profile_pic != 'default.png':
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], homepage.profile_pic))
                    except OSError:
                        pass
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                homepage.profile_pic = filename
        
        db.session.commit()
        flash('Data halaman Home berhasil diperbarui!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_home.html', form=form, homepage=homepage)

@app.route('/admin/about/edit', methods=['GET', 'POST'])
@login_required
def edit_about():
    if not current_user.is_admin: return redirect(url_for('home'))
    aboutpage = AboutPage.query.first()
    if not aboutpage:
        aboutpage = AboutPage(bio_text='Biografi default', skills='Keahlian1, Keahlian2')
        db.session.add(aboutpage)
        db.session.commit()
    
    form = AboutPageForm(obj=aboutpage)
    if form.validate_on_submit():
        form.populate_obj(aboutpage)
        db.session.commit()
        flash('Data halaman About berhasil diperbarui!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/edit_about.html', form=form)

# Inisialisasi database saat aplikasi dimulai
# Penting: Ini harus berada di luar blok if __name__ == '__main__': agar dijalankan oleh Gunicorn di Koyeb
with app.app_context():
    # Menggunakan inspeksi untuk memeriksa keberadaan tabel dan membuatnya jika belum ada
    inspector = inspect(db.engine)
    
    # Daftar semua model yang perlu dibuat tabelnya
    models = [User, Post, Project, HomePage, AboutPage]
    
    for model in models:
        # Tambahkan penguncian file untuk memastikan hanya satu worker yang melakukan inisialisasi
        lock_file_path = os.path.join(app.root_path, 'db_init.lock')
        with open(lock_file_path, 'a') as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX) # Kunci eksklusif

            try:
                for model in models:
                    if not inspector.has_table(model.__tablename__):
                        logger.info(f"Creating table: {model.__tablename__}")
                        model.__table__.create(db.engine) # Buat tabel dengan engine
                        time.sleep(0.1) # Sedikit delay antar tabel
                
                # Tambahkan user admin pertama kali jika belum ada
                if User.query.count() == 0:
                    logger.info("Membuat akun admin awal. Login pertama kali melalui Google untuk menjadi admin.")
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN) # Lepaskan kunci

if __name__ == '__main__':
    app.run(debug=True)
