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
# Mengambil SECRET_KEY dari environment variable untuk keamanan di produksi
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)

# Konfigurasi Authlib (Google OAuth)
oauth = OAuth(app)
oauth.register(
    name='google',
    # Mengambil Client ID dan Client Secret dari environment variables
    # Ini PENTING untuk keamanan di Koyeb
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
login_manager.login_view = 'login' # Rute untuk halaman login

# Pastikan direktori upload ada saat aplikasi dimulai
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Database Models ---
# Model untuk pengguna (admin)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=True) # ID unik dari Google
    email = db.Column(db.String(100), unique=True, nullable=False)     # Email pengguna
    is_admin = db.Column(db.Boolean, default=False)                   # Flag untuk menandai apakah user adalah admin

# Model untuk postingan blog
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.String(20), nullable=False, default=datetime.utcnow().strftime('%d %B %Y'))

# Model untuk proyek portofolio
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(100), nullable=True) # Nama file gambar proyek

# Model untuk konten halaman Home
class HomePage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    intro_title = db.Column(db.String(100), nullable=False)
    intro_subtitle = db.Column(db.String(150), nullable=False)
    profile_pic = db.Column(db.String(100), nullable=True) # Nama file foto profil

# Model untuk konten halaman About
class AboutPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bio_text = db.Column(db.Text, nullable=False)
    skills = db.Column(db.Text, nullable=False)

# --- Forms ---
# Formulir untuk login (tidak digunakan untuk Google Login, tapi bisa untuk login manual jika diaktifkan)
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    submit = SubmitField('Login')

# Formulir untuk postingan blog
class PostForm(FlaskForm):
    title = StringField('Judul', validators=[DataRequired()])
    content = TextAreaField('Konten', validators=[DataRequired()])
    submit = SubmitField('Simpan Post')

# Formulir untuk proyek portofolio
class ProjectForm(FlaskForm):
    description = TextAreaField('Deskripsi', validators=[DataRequired()])
    submit = SubmitField('Simpan Proyek')

# Formulir untuk halaman Home
class HomePageForm(FlaskForm):
    intro_title = StringField('Judul Intro', validators=[DataRequired()])
    intro_subtitle = TextAreaField('Sub-judul Intro', validators=[DataRequired()])
    submit = SubmitField('Simpan Perubahan')

# Formulir untuk halaman About
class AboutPageForm(FlaskForm):
    bio_text = TextAreaField('Biografi', validators=[DataRequired()])
    skills = TextAreaField('Daftar Keahlian (dipisah dengan koma)', validators=[DataRequired()])
    submit = SubmitField('Simpan Perubahan')

# Fungsi pembantu untuk memeriksa ekstensi file yang diizinkan
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Fungsi user_loader untuk Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes Publik ---
# Halaman utama
@app.route('/')
def home():
    posts = Post.query.order_by(Post.id.desc()).limit(3).all()
    homepage_data = HomePage.query.first()
    return render_template('home.html', posts=posts, homepage_data=homepage_data)

# Halaman blog
@app.route('/blog')
def blog():
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template('blog.html', posts=posts)

# Halaman portofolio
@app.route('/portfolio')
def portfolio():
    projects = Project.query.order_by(Project.id.desc()).all()
    return render_template('portfolio.html', projects=projects)

# Halaman tentang saya
@app.route('/about')
def about():
    about_data = AboutPage.query.first()
    homepage_data = HomePage.query.first()
    return render_template('about.html', about_data=about_data, homepage_data=homepage_data)

# --- Routes Login/Logout ---
# Halaman login (menampilkan tombol Google Login)
@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    return render_template('login.html')

# Logout pengguna
@app.route('/logout')
@login_required # Hanya bisa diakses jika sudah login
def logout():
    logout_user()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('home'))

# Memulai proses otorisasi Google OAuth
@app.route('/login/google')
def login_google():
    return oauth.google.authorize_redirect(url_for('auth_google', _external=True))

# Callback setelah otorisasi Google berhasil
@app.route('/auth/google')
def auth_google():
    try:
        token = oauth.google.authorize_access_token()
        resp = oauth.google.get('userinfo')
        user_info = resp.json()
        
        user = User.query.filter_by(google_id=user_info['id']).first()
        if not user:
            # Jika user belum ada, buat user baru
            # Akun Google pertama yang login akan menjadi admin
            if User.query.count() == 0: # Hanya user pertama yang terdaftar sebagai admin
                user = User(google_id=user_info['id'], email=user_info['email'], is_admin=True)
                flash('Akun admin berhasil dibuat dengan Google Anda!', 'success')
            else:
                user = User(google_id=user_info['id'], email=user_info['email'], is_admin=False) # User berikutnya bukan admin
                flash('Anda tidak memiliki izin admin.', 'danger')
                return redirect(url_for('home')) # Redirect jika bukan admin
            
            db.session.add(user)
            db.session.commit()
        
        # Jika user sudah ada dan bukan admin, jangan izinkan login ke dashboard
        if not user.is_admin:
            flash('Anda tidak memiliki izin admin.', 'danger')
            return redirect(url_for('home'))

        login_user(user)
        flash('Login berhasil!', 'success')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Login gagal: {e}', 'danger')
        return redirect(url_for('login'))

# --- Routes Admin (CRUD) ---
# Dashboard admin
@app.route('/admin')
@login_required # Hanya bisa diakses jika sudah login
def admin_dashboard():
    if not current_user.is_admin: # Verifikasi apakah user yang login adalah admin
        flash('Anda tidak memiliki akses ke halaman ini.', 'danger')
        logout_user()
        return redirect(url_for('home'))
    posts = Post.query.all()
    projects = Project.query.all()
    return render_template('admin/dashboard.html', posts=posts, projects=projects)

# Membuat postingan blog baru
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

# Mengedit postingan blog
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

# Menghapus postingan blog
@app.route('/admin/post/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    if not current_user.is_admin: return redirect(url_for('home'))
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Postingan berhasil dihapus!', 'success')
    return redirect(url_for('admin_dashboard'))

# Membuat proyek portofolio baru
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

# Mengedit proyek portofolio
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

# Menghapus proyek portofolio
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

# Mengedit halaman Home
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

# Mengedit halaman About
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
    db.metadata.create_all(db.engine, checkfirst=True) # Perbaikan di sini

if __name__ == '__main__':
    # Pastikan Anda sudah mengatur variabel lingkungan untuk SECRET_KEY, GOOGLE_CLIENT_ID, dan GOOGLE_CLIENT_SECRET
    # Contoh: export SECRET_KEY='kunci-rahasia-anda'
    # Contoh: export GOOGLE_CLIENT_ID='...'
    # Contoh: export GOOGLE_CLIENT_SECRET='...'
    app.run(debug=True)
