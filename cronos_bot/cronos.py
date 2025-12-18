import os
import json
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Configuración de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Cargar variables de entorno
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configuración de Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Sistema de Memoria / Calendario Simple
CALENDAR_FILE = 'calendar.json'
COMMANDS_FILE = 'commands.json'

def load_data(file_path, default_data):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return default_data

def save_data(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# Inicializar datos
calendar = load_data(CALENDAR_FILE, [])
custom_commands = load_data(COMMANDS_FILE, {
    "orion": "ORION Tech es líder en soluciones tecnológicas.",
    "cv": "Aquí está mi CV: https://juancamiloasist.github.io/cami-asist/cv.html",
    "tj": "Aquí está mi Tarjeta Digital: https://juancamiloasist.github.io/cami-asist/card.html"
})

# --- FUNCIONES DEL BOT ---

# --- CONFIGURACIÓN DE IA ---

SYSTEM_INSTRUCTIONS = """
Eres CRONOS, el asistente de IA avanzado y ejecutivo de Juan Camilo Espinosa.
Trabajas para ORION Tech. Tu objetivo es optimizar la vida y operaciones de Juan Camilo.

INFORMACIÓN CLAVE:
- Tu creador y jefe: Juan Camilo Espinosa (Director de Operaciones, ORION Tech Colombia).
- Enlace Hoja de Vida (CV): https://juancamiloasist.github.io/cami-asist/cv.html
- Enlace Tarjeta Digital (TJ): https://juancamiloasist.github.io/cami-asist/card.html
- Teléfono: +57 324 514 3926

INSTRUCCIONES DE COMPORTAMIENTO:
1. Responde de forma breve, profesional y eficiente (estilo mayordomo digital o IA táctica).
2. Si te piden la "hoja de vida", "cv", "resumen curricular", entrégales el enlace del CV.
3. Si te piden la "tarjeta", "contacto digital", "info", entrégales el enlace de la TJ.
4. Entiende lenguaje natural. Ejemplo: "Pásame el cv de camilo" -> Detecta la intención y responde con el link.
5. Usa emojis tácticos (⏳, 🚀, 💻) moderadamente.
"""

async def handle_gpt_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_name = update.effective_user.first_name

    # Respuestas rápidas (Fallback manual si la IA falla o para velocidad)
    text_lower = user_text.lower()
    if "cv" in text_lower or "hoja de vida" in text_lower:
        await update.message.reply_text(f"Aquí tienes la Hoja de Vida de Juan Camilo:\nhttps://juancamiloasist.github.io/cami-asist/cv.html")
        return
    if "tarjeta" in text_lower or "tj" in text_lower or "contacto" in text_lower:
        await update.message.reply_text(f"Aquí tienes la Tarjeta Digital:\nhttps://juancamiloasist.github.io/cami-asist/card.html")
        return

    # Procesamiento Neural (Gemini)
    try:
        # Indicador de "Escribiendo..."
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        chat = model.start_chat(history=[])
        response = chat.send_message(f"{SYSTEM_INSTRUCTIONS}\n\nInteracción actual:\nUsuario ({user_name}): {user_text}")
        
        await update.message.reply_text(response.text)
        
    except Exception as e:
        logging.error(f"Error Gemini: {e}")
        await update.message.reply_text("⚠️ CRONOS: Error en enlace neural. Reintentando...")

# --- HANDLERS COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⏳ **SISTEMA CRONOS EN LÍNEA**\n\n"
        "Saludos. Soy su asistente operativo.\n"
        "Comandos directos:\n"
        "/cv - Hoja de Vida\n"
        "/tj - Tarjeta Digital\n"
        "/agenda - Ver calendario\n\n"
        "O simplemente hábleme en lenguaje natural."
    )

# --- GESTIÓN DE AGENDA ---

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        event_text = ' '.join(context.args)
        if not event_text:
            await update.message.reply_text("Uso: /agendar [descripción del evento]")
            return

        new_event = {
            "id": len(calendar) + 1,
            "event": event_text,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        calendar.append(new_event)
        save_data(CALENDAR_FILE, calendar)
        await update.message.reply_text(f"✅ Evento agregado: {event_text}")
        
    except Exception as e:
        await update.message.reply_text("Error al guardar evento.")

async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not calendar:
        await update.message.reply_text("📅 Tu agenda está vacía.")
        return
    
    msg = "📅 **Agenda de Juan Camilo:**\n"
    for ev in calendar:
        msg += f"- {ev['event']} ({ev['created_at']})\n"
    
    await update.message.reply_text(msg)

# --- CONFIGURACIÓN PRINCIPAL ---

def main():
    if not TELEGRAM_TOKEN:
        print("Error: Falta TELEGRAM_TOKEN en .env")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("agendar", add_event))
    application.add_handler(CommandHandler("agenda", list_events))
    
    # Mensajes de texto (Cerebro Gemini)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gpt_message))

    print("⏳ CRONOS está en línea...")
    application.run_polling()

if __name__ == "__main__":
    main()
