from app import app, db, User

def create_admin_user():
    """
    Skrip untuk membuat akun admin baru secara interaktif.
    """
    with app.app_context():
        # Cek apakah database sudah dibuat
        db.create_all()

        print("--- Buat Akun Admin Baru ---")
        username = input("Masukkan username: ")
        
        # Cek apakah username sudah ada
        if User.query.filter_by(username=username).first():
            print(f"Error: Username '{username}' sudah ada. Silakan coba yang lain.")
            return

        password = input("Masukkan password: ")
        
        # Buat user baru
        new_user = User(username=username)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()
        print("\nAkun admin berhasil dibuat!")
        print("Anda sekarang bisa login menggunakan username dan password yang baru.")

if __name__ == '__main__':
    create_admin_user()