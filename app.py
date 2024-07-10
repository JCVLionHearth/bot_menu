from flask import Flask, render_template, request, jsonify, send_file
import json
import datetime
import re
import unicodedata
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import utils
app = Flask(__name__)
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
def get_bot_response(user_input, user_name):
    global chat_history
    # Normalize user input
    normalized_input = normalize_text(user_input)
    
    # Check for greeting patterns
    if greeting_patterns.search(normalized_input):
        initial_greeting = (f"😊Hola!!, con ¿Cuál opción puedo ayudarte? "
                            "<button class='option-button' onclick=\"sendMessage('Tengo una consulta')\">Consulta</button>"
                            "<button class='option-button' onclick=\"sendMessage('Tengo un dilema')\">Dilema</button>"
                            "<button class='option-button' onclick=\"sendMessage('Con quienes me puedo contactar')\">Contactos</button>")
        chat_history.append(('Bot', initial_greeting))
        return initial_greeting
    
    # Check for farewell patterns
    if farewell_patterns.search(normalized_input):
        farewell_message = "Fue un gusto servirte!!👍, ¡que tengas un buen día! Si necesitas más ayuda, estaré aquí para asistirte.👨‍💻"
        chat_history.append(('Bot', farewell_message))
        return farewell_message
    
    # Check for yes/no responses
    if normalized_input == 'si':
        return get_initial_greeting(user_name)
    if normalized_input == 'no':
        return get_farewell_message()
    
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
            return response
    
    return "Lo siento, No te entiendo. 😅"
def get_initial_greeting(user_name):
   initial_greeting = (f"¿Con cuál opción puedo ayudarte? 👩‍💻"
                       "<button class='option-button' onclick=\"sendMessage('Tengo una consulta')\">Consultas</button>"
                       "<button class='option-button' onclick=\"sendMessage('Tengo un dilema')\">Dilemas</button>"
                       "<button class='option-button' onclick=\"sendMessage('Con quienes me puedo contactar')\">Contactos</button>")
   chat_history.append(('Bot', initial_greeting))
   return initial_greeting
def get_farewell_message():
   farewell_message = "Fue un gusto servirte!!👍, ¡que tengas un buen día! Si necesitas más ayuda, estaré aquí para asistirte.👨‍💻"
   chat_history.append(('Bot', farewell_message))
   return farewell_message
@app.route("/")
def home():
   return render_template("index.html")
@app.route("/get")
def get_bot_response_endpoint():
   user_text = request.args.get('msg')
   user_name = request.args.get('user')
   chat_history.append(('User', user_text))
   return jsonify(get_bot_response(user_text, user_name))
@app.route('/download')
def download_chat():
   global chat_history
   buffer = BytesIO()
   c = canvas.Canvas(buffer, pagesize=letter)
   width, height = letter
   c.setFont("Helvetica", 12)
   c.drawString(200, height - 40, "Historia del Chat")
   c.drawString(200, height - 60, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
   y = height - 100
   max_width = width - 60  # Reduce the width to avoid cutting off the text
   def draw_text(text_object, text, max_width):
       lines = utils.simpleSplit(text, text_object._fontname, text_object._fontsize, max_width)
       for line in lines:
           text_object.textLine(line)
   text_object = c.beginText(30, y)
   text_object.setFont("Helvetica", 12)
   def clean_html(text):
       clean = re.compile('<.*?>')
       return re.sub(clean, ' / ', text)
   for sender, message in chat_history:
       clean_message = clean_html(message).replace('\n', ' ')
       text = f"{sender}: {clean_message}"
       if text_object.getY() < 40:
           c.drawText(text_object)
           c.showPage()
           text_object = c.beginText(30, height - 40)
           text_object.setFont("Helvetica", 12)
       draw_text(text_object, text, max_width)
       text_object.moveCursor(0, 14)
   c.drawText(text_object)
   c.save()
   buffer.seek(0)
   return send_file(buffer, as_attachment=True, download_name="chat_history.pdf")
if __name__ == "__main__":
   app.run(debug=True)