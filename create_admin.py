from werkzeug.security import generate_password_hash
from app import app,db, User

with app.app_context():
    # Crear usuarios administradores
    admin1 = User(username='admin1', password=generate_password_hash('password1'), is_admin=True)
    admin2 = User(username='admin2', password=generate_password_hash('password2'), is_admin=True)
    admin3 = User(username='admin3', password=generate_password_hash('password3'), is_admin=True)

    # Añadir usuarios a la base de datos
    db.session.add(admin1)
    db.session.add(admin2)
    db.session.add(admin3)
    db.session.commit()

