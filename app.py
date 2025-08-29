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

# Konfigurasi Upload Gambar
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kunci-rahasia-super-kuat-dan-aman'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)

# Inisialisasi Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Pastikan direktori upload ada
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.String(20), nullable=False, default=datetime.utcnow().strftime('%d %B %Y'))

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # title = db.Column(db.String(100), nullable=False) # Kita hapus title dari sini
    description = db.Column(db.Text, nullable=False)
    # tech_stack = db.Column(db.String(100), nullable=False) # Dihapus
    # link = db.Column(db.String(200), nullable=False) # Dihapus
    image_file = db.Column(db.String(100), nullable=True) # Hanya foto dan deskripsi

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
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class PostForm(FlaskForm):
    title = StringField('Judul', validators=[DataRequired()])
    content = TextAreaField('Konten', validators=[DataRequired()])
    submit = SubmitField('Simpan Post')

class ProjectForm(FlaskForm):
    # title = StringField('Judul Proyek', validators=[DataRequired()]) # Dihapus dari form
    description = TextAreaField('Deskripsi', validators=[DataRequired()])
    # tech_stack = StringField('Teknologi', validators=[DataRequired()]) # Dihapus
    # link = StringField('Link', validators=[DataRequired()]) # Dihapus
    submit = SubmitField('Simpan Proyek')

class HomePageForm(FlaskForm):
    intro_title = StringField('Judul Intro', validators=[DataRequired()])
    intro_subtitle = TextAreaField('Sub-judul Intro', validators=[DataRequired()])
    submit = SubmitField('Simpan Perubahan')

class AboutPageForm(FlaskForm):
    bio_text = TextAreaField('Biografi', validators=[DataRequired()])
    skills = TextAreaField('Daftar Keahlian (dipisah dengan koma)', validators=[DataRequired()])
    submit = SubmitField('Simpan Perubahan')

# Fungsi untuk memeriksa ekstensi file yang diizinkan
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
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Login berhasil!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Login gagal. Periksa username dan password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('home'))

# --- Routes Admin (CRUD) ---
@app.route('/admin')
@login_required
def admin_dashboard():
    posts = Post.query.all()
    projects = Project.query.all()
    return render_template('admin/dashboard.html', posts=posts, projects=projects)

# CRUD Post
@app.route('/admin/post/create', methods=['GET', 'POST'])
@login_required
def create_post():
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
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Postingan berhasil dihapus!', 'success')
    return redirect(url_for('admin_dashboard'))

# CRUD Project
@app.route('/admin/project/create', methods=['GET', 'POST'])
@login_required
def create_project():
    form = ProjectForm()
    if form.validate_on_submit():
        image_file = None
        if 'project_image' in request.files: # Nama field di HTML harus 'project_image'
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
            description=form.description.data, # Hanya deskripsi
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
            elif file.filename == '' and not project.image_file: # Jika tidak ada file baru dan tidak ada file lama
                flash('Anda harus mengunggah gambar untuk proyek.', 'danger')
                return render_template('admin/edit_project.html', form=form, project=project)
        
        project.description = form.description.data # Hanya deskripsi
        db.session.commit()
        flash('Proyek berhasil diperbarui!', 'success')
        return redirect(url_for('admin_dashboard'))
    elif request.method == 'GET':
        form.description.data = project.description
    return render_template('admin/edit_project.html', form=form, project=project)

@app.route('/admin/project/delete/<int:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
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

# CRUD Homepage
@app.route('/admin/home/edit', methods=['GET', 'POST'])
@login_required
def edit_home():
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

# CRUD AboutPage
@app.route('/admin/about/edit', methods=['GET', 'POST'])
@login_required
def edit_about():
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


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)