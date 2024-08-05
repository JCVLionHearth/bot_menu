from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for,flash,make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
# from flask_ldap3_login import LDAP3LoginManager, AuthenticationResponseStatus
from werkzeug.security import generate_password_hash, check_password_hash
import json
import datetime
import re
import unicodedata
import io
import os

from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.units import inch
import csv

app = Flask(__name__)

# ruta del disco persistente
# db_dir='/var/data'
# os.makedirs(db_dir,exist_ok=True)
# db_path=os.path.join(db_dir,'interactions.db')
## Creación de base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///interactions.db'
# app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY']='93\+olRdZ}[I4j>0O`e?\Liw'

db = SQLAlchemy(app)

# Definición del modelo de interacción
class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)  # Añade el campo de correo
    # ip_address = db.Column(db.String(50), nullable=True)  # Añade la dirección IP
    user_input = db.Column(db.String(500), nullable=False)
    # response = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<Interaction {self.username} - {self.user_input}>'
    
# configuraciones de login manager

login_manager=LoginManager()
login_manager.init_app(app)

# Definición del modelo para el usuario
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<User {self.username}'

with app.app_context():
    db.create_all()

# Load intents
with open('intents.json', 'r', encoding='utf-8') as file:
    intents = json.load(file)

# Initialize chat history
chat_history = []

# Define patterns for greetings and farewells (normalized)
greeting_patterns = re.compile(r'\b(hola|hi|buenos dias|buenas tardes|buenas noches|saludos)\b', re.IGNORECASE)
farewell_patterns = re.compile(r'\b(adios|hasta luego|nos vemos|chau|bye|hasta pronto|gracias|muchas gracias)\b', re.IGNORECASE)

def normalize_text(text):
    # Normalize text to remove accents and convert to lowercase
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower()

# def save_interaction(username, user_input, response):
def save_interaction(username, user_input,email=None):
    if username is None:
        username='Unknown'
    #interaction = Interaction(username=username, user_input=user_input, response=response)
    interaction = Interaction(username=username, user_input=user_input,email=email)
    db.session.add(interaction)
    db.session.commit()

def get_bot_response(user_input, user_name,user_email):
    global chat_history
    # Normalize user input
    normalized_input = normalize_text(user_input)
    
    # Check for greeting patterns
    if greeting_patterns.search(normalized_input):
        initial_greeting = (f"😊Hola!!, con ¿Cuál opción puedo ayudarte? "
                            "<button class='option-button' onclick=\"sendMessage('Tengo una consulta')\">Consulta</button>"
                            "<button class='option-button' onclick=\"sendMessage('Tengo un dilema')\">Dilema</button>"
                            "<button class='option-button' onclick=\"sendMessage('Quiero consultar la normativa')\">Normativas</button>"
                            "<button class='option-button' onclick=\"sendMessage('Quiero recordar algunas definiciones')\">Definiciones</button>"
                            "<button class='option-button' onclick=\"sendMessage('Con quienes me puedo contactar')\">Contactos</button>"
                            "<button class='option-button' onclick=\"sendMessage('Quiero conocer sobre el Subsistema de Gestión Antisoborno')\">Subsistema de Gestión Antisoborno</button>")
        chat_history.append(('Bot', initial_greeting))
        save_interaction(user_name, user_input, user_email)
        #save_interaction(user_name, user_input, initial_greeting)
        return initial_greeting
    
    # Check for farewell patterns
    if farewell_patterns.search(normalized_input):
        farewell_message = "Fue un gusto servirte!!👍, ¡que tengas un buen día! Si necesitas más ayuda, estaré aquí para asistirte.👨‍💻 <br> Para más información consulta La 💻<a href='https://ecopetrol.sharepoint.com/sites/emasdigital/Paginas/L%C3%ADnea-%C3%A9tica.aspx' target='_blank'>Línea Ética<a>"
        chat_history.append(('Bot', farewell_message))
        #save_interaction(user_name, user_input, farewell_message)
        save_interaction(user_name, user_input, user_email)
        return farewell_message
    
  
    # Check for yes/no responses
    if normalized_input == 'si':
        response = get_initial_greeting(user_name)
        #save_interaction(user_name, user_input, response)
        save_interaction(user_name, user_input, user_email)
        return response
    if normalized_input == 'no':
        response = get_farewell_message()
        save_interaction(user_name, user_input, user_email)
        #save_interaction(user_name, user_input, response)
        return response
    
    for intent in intents['intents']:
        if normalized_input == normalize_text(intent['tag']):
            responses = intent.get('responses', [])
            if responses:
                response = responses[0]
            else:
                response = ""
            
            options = intent.get('options', [])
            if options:
                response += "<br><br>👨‍🏫Encontré estas opciones: " + "".join(
                    f'<button class="option-button" onclick="sendMessage(\'{opt}\')">{opt}</button>' for opt in options)
            else:
                response += "<br><br> ¿Puedo ayudarte con algo más? " \
                            "<br><button class='option-button green' onclick=\"sendMessage('SI')\">SI</button> " \
                            "<button class='option-button green' onclick=\"sendMessage('NO')\">NO</button>"
            chat_history.append(('Bot', response))
            save_interaction(user_name, user_input, user_email)
            #save_interaction(user_name, user_input, response)
            return response
    
    response = "Lo siento, No te entiendo. 😅"
    chat_history.append(('Bot', response))
    #save_interaction(user_name, user_input, response)
    save_interaction(user_name, user_input, user_email)
    return response

def get_initial_greeting(user_name):
    initial_greeting = (f"¿Con cuál opción puedo ayudarte? 👩‍💻"
                        "<button class='option-button' onclick=\"sendMessage('Tengo una consulta')\">Consultas</button>"
                        "<button class='option-button' onclick=\"sendMessage('Tengo un dilema')\">Dilemas</button>"
                        "<button class='option-button' onclick=\"sendMessage('Quiero consultar la normativa')\">Normativas</button>"
                        "<button class='option-button' onclick=\"sendMessage('Quiero recordar algunas definiciones')\">Definiciones</button>"
                        "<button class='option-button' onclick=\"sendMessage('Con quienes me puedo contactar')\">Contactos</button>"
                        "<button class='option-button' onclick=\"sendMessage('Quiero conocer sobre el Subsistema de Gestión Antisoborno')\">Subsistema de Gestión Antisoborno</button>")
    chat_history.append(('Bot', initial_greeting))
    return initial_greeting

def get_farewell_message():
    farewell_message = "Fue un gusto servirte!!👍, ¡que tengas un buen día! Si necesitas más ayuda, estaré aquí para asistirte.👨‍💻 <br><br> Para más información consulta La 💻<a href='https://ecopetrol.sharepoint.com/sites/emasdigital/Paginas/L%C3%ADnea-%C3%A9tica.aspx' target='_blank'>Línea Ética<a>"
    chat_history.append(('Bot', farewell_message))
    return farewell_message

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get")
def get_bot_response_endpoint():
    user_text = request.args.get('msg')
    user_name = request.args.get('user','Unknown')
    user_email = request.args.get('email', '')  # Recibe el correo
    # ip_address = request.remote_addr
    chat_history.append(('User', user_text))
    return jsonify(get_bot_response(user_text, user_name, user_email))

# descarga de excel: listado de paises
@app.route('/download_excel')
def download_excel():
    return send_file('static/listado_pais.xlsx', as_attachment=True, download_name='listado_pais.xlsx')

# descarga de excel: listado de paises
@app.route('/download_excel_mentores')
def download_excel2():
    return send_file('static/listado_mentores.xlsx', as_attachment=True, download_name='listado_mentores.xlsx')

@app.route('/download')
def download_chat():
    global chat_history
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=80, bottomMargin=50)  # Márgenes ajustados

    Story = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    normal_style = styles["Normal"]
    company_style = ParagraphStyle(
        'CompanyStyle',
        parent=normal_style,
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor="#4B4B4B",
        spaceAfter=10,
    )
    
    message_style = ParagraphStyle(
        'MessageStyle',
        parent=normal_style,
        fontName='Helvetica',
        fontSize=12,
        leading=14,
        textColor="#333333",
        spaceAfter=12,
    )

    disclaimer_style = ParagraphStyle(
        'DisclaimerStyle',
        parent=normal_style,
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=12,
        textColor="#777777",
        spaceAfter=20,
    )

    def clean_html(text):
        clean = re.compile('<.*?>')
        return re.sub(clean, ' / ', text)

    # Encabezado con logo y detalles de la compañía
    company_logo = "static/images/logo_ethos.PNG"  # Ruta al logo de la empresa
    if company_logo:
        im = Image(company_logo, 2*inch, 1*inch)
        Story.append(im)
    
    company_info = Paragraph("Dirección Corporativa de Cumplimiento<br/>Línea Ética<br/>Línea Internacional <b>018009121013</b><br/>Línea Nacional en Bogotá <b>3103158600</b><br/>Extensión <b>43900</b>", company_style)
    Story.append(company_info)
    Story.append(Spacer(1, 12))

    # Añadir el disclaimer
    disclaimer_text = "DISCLAIMER: Las respuestas dadas por el bot son orientativas frente a aspectos comúnmente consultados.\
    Para una respuesta con mayor detalle a un caso específico, consulte a través de la línea ética."
    disclaimer = Paragraph(disclaimer_text, disclaimer_style)
    Story.append(disclaimer)
    Story.append(Spacer(1, 20))

    # Añadir los mensajes del chat
    for sender, message in chat_history:
        clean_message = clean_html(message).replace('\n', ' ')
        text = f"<b>{sender}:</b> {clean_message}"
        p = Paragraph(text, message_style)
        Story.append(p)

    # Añadir pie de página personalizado
    def header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 12)
        header_text = "Historia del Chat"
        date_text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        page_text = f"Página {doc.page}"

        canvas.drawString(50, 750, header_text)
        canvas.drawString(450, 750, date_text)
        canvas.setFont("Helvetica", 10)
        canvas.drawString(50, 30, page_text)
        canvas.drawString(50, 15, "Confidencial - Solo para uso interno")
        canvas.restoreState()

    doc.build(Story, onFirstPage=header_footer, onLaterPages=header_footer)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="Historial_Ethos.pdf")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Nombre de usuario o contraseña incorrectos')
    return render_template('admin_login.html',error='')

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html')

@app.route('/admin_download_interactions', methods=['POST'])
@login_required
def download_interactions():
    if not current_user.is_admin:
        return redirect(url_for('home'))
    # Generar el archivo CSV
    datos = io.StringIO()
    writer = csv.writer(datos,quoting=csv.QUOTE_MINIMAL,delimiter=";")
    writer.writerow(['ID', 'Username', 'User Input', 'Timestamp'])
    interactions = Interaction.query.all()
    for interaction in interactions:
        writer.writerow([interaction.id, interaction.username, interaction.user_input, interaction.timestamp])
    output = make_response(datos.getvalue().encode('utf-8'))
    output.headers["Content-Disposition"] = "attachment; filename=interacciones.csv"
    output.headers["Content-type"] = "text/csv;charset=utf-8"
    return output

# Contraseña para reiniciar
RESET_PASSWORD = ')09-KX1L/R4e'

@app.route('/clear_interactions', methods=['GET', 'POST'])
@login_required
def clear_interactions():
    if not current_user.is_admin:
        return redirect(url_for('home'))
    password = request.form['password']
    if password == RESET_PASSWORD:
        Interaction.query.delete()
        db.session.commit()
        flash('Interacciones limpiadas exitosamente')
    else:
        flash('Contraseña incorrecta')
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(debug=True)