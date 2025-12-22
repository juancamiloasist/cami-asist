import os
import json
import logging
import asyncio
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# Configuración de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Cargar variables de entorno
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configuración de Gemini (nuevo SDK)
client = genai.Client(api_key=GEMINI_API_KEY)

# Sistema de Archivos de Datos
CALENDAR_FILE = 'calendar.json'
COMMANDS_FILE = 'commands.json'
CONTACTS_FILE = 'contacts.json'
MEMORY_FILE = 'memory.json'
DOWNLOADS_DIR = 'downloads'

# Crear directorio de descargas si no existe
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

def load_data(file_path, default_data):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default_data

def save_data(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Inicializar datos
calendar = load_data(CALENDAR_FILE, [])
contacts = load_data(CONTACTS_FILE, {})
memory = load_data(MEMORY_FILE, {})
custom_commands = load_data(COMMANDS_FILE, {
    "orion": "ORION Tech es líder en soluciones tecnológicas.",
    "cv": "Aquí está mi CV: https://juancamiloasist.github.io/cami-asist/cv.html",
    "tj": "Aquí está mi Tarjeta Digital: https://juancamiloasist.github.io/cami-asist/card.html"
})

# Links de AI Studio
AI_STUDIO_LINKS = [
    "https://ai.studio/apps/drive/1qqUcvHx_KD94VplUFjDxAiAl84Ji1jt7?fullscreenApplet=true",
    "https://ai.studio/apps/drive/1tFuWAILHDMavaoM033YMbnjlS8Ww6FVK?fullscreenApplet=true"
]

# --- CONFIGURACIÓN DE IA ---

SYSTEM_INSTRUCTIONS = """
Eres CRONOS, asistente de IA de ORION Tech Colombia.
Hablas con acento colombiano paisa (Medellín) - cálido, amigable, profesional.
Representas a Juan Camilo Espinosa (Director de Operaciones Colombia).

🏢 SOBRE ORION TECH:
- Empresa de automatización con IA para negocios
- Sede principal: San José, California (Alex G. Espinosa, CEO)
- Oficina Colombia: Eje Cafetero (Juan Camilo Espinosa, Director)

💰 PRECIOS COLOMBIA (COP/mes):
- INDIVIDUAL: $890,000 | SALONES: $2,990,000 | RETAIL: $2,990,000
- LICORERAS: $3,890,000 | RESTAURANTES: $4,490,000 | CONTRATISTAS: $4,490,000
- ENTERPRISE: $14,990,000+

🚀 NEKON AI (CONSULTORÍA):
- Estratégica: $1.200 USD | Agente: $8.500 USD | Sistema: $25K+ USD

🔧 PRICE BOOK: Tarifa de labor: $185 USD/hr.

📞 CONTACTOS:
- Colombia: +57 324 514 3926 (Juan Camilo)
- USA: (669) 234-2444 (Alex CEO)

⚠️ REGLAS:
- Máximo 3 oraciones por respuesta
- Sé cálido y cercano como buen paisa
- Usa expresiones: "parce", "qué más", "bacano", "hágale pues"
"""

# --- HANDLERS DE COMANDOS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⏳ **SISTEMA CRONOS EN LÍNEA**\n\n"
        "Comandos disponibles:\n"
        "/cv - Hoja de Vida\n"
        "/tj - Tarjeta Digital\n"
        "/links - AI Studio Apps\n"
        "/agenda - Ver calendario\n"
        "/agendar [evento] - Agregar evento\n"
        "/contactos - Ver contactos\n"
        "/addcontact [nombre] [telefono] - Agregar contacto\n"
        "/recuerda [clave] es [valor] - Guardar en memoria\n"
        "/memoria [clave] - Buscar en memoria\n"
        "/yt [url] - Descargar video YouTube\n\n"
        "💡 También puedo responder en lenguaje natural.",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 **COMANDOS CRONOS**\n\n"
        "🎭 /start - Iniciar bot\n"
        "📄 /cv - Ver Hoja de Vida\n"
        "💳 /tj - Ver Tarjeta Digital\n"
        "🔗 /links - AI Studio Apps\n\n"
        "📅 /agenda - Ver calendario\n"
        "➕ /agendar [evento] - Agregar evento\n\n"
        "👥 /contactos - Ver contactos\n"
        "➕ /addcontact [nombre] [tel] - Nuevo contacto\n"
        "🗑️ /delcontact [nombre] - Eliminar contacto\n\n"
        "🧠 /recuerda [clave] es [valor] - Guardar\n"
        "🔍 /memoria [clave] - Buscar\n"
        "📋 /memorias - Ver todo\n\n"
        "📹 /yt [url] - Descargar YouTube\n",
        parse_mode='Markdown'
    )

# --- LINKS ---
async def links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    links_text = "🔗 **AI STUDIO APPS**\n\n"
    for i, link in enumerate(AI_STUDIO_LINKS, 1):
        links_text += f"{i}. {link}\n"
    await update.message.reply_text(links_text, parse_mode='Markdown')

# --- CV y TJ ---
async def cv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 **Hoja de Vida Juan Camilo:**\nhttps://juancamiloasist.github.io/cami-asist/cv.html", parse_mode='Markdown')

async def tj_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💳 **Tarjeta Digital:**\nhttps://juancamiloasist.github.io/cami-asist/card.html", parse_mode='Markdown')

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
    for ev in calendar[-10:]:  # Últimos 10 eventos
        msg += f"- {ev['event']} ({ev['created_at']})\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# --- GESTIÓN DE CONTACTOS ---

async def list_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not contacts:
        await update.message.reply_text("👥 No hay contactos guardados.")
        return
    
    msg = "👥 **CONTACTOS**\n\n"
    for name, info in contacts.items():
        msg += f"• **{name}**: {info.get('telefono', 'N/A')}\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def add_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text("Uso: /addcontact [nombre] [telefono]")
            return
        
        name = context.args[0]
        phone = ' '.join(context.args[1:])
        
        contacts[name] = {
            "telefono": phone,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_data(CONTACTS_FILE, contacts)
        await update.message.reply_text(f"✅ Contacto guardado: {name} - {phone}")
        
    except Exception as e:
        await update.message.reply_text("Error al guardar contacto.")

async def del_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Uso: /delcontact [nombre]")
            return
        
        name = context.args[0]
        if name in contacts:
            del contacts[name]
            save_data(CONTACTS_FILE, contacts)
            await update.message.reply_text(f"🗑️ Contacto eliminado: {name}")
        else:
            await update.message.reply_text(f"❌ Contacto no encontrado: {name}")
            
    except Exception as e:
        await update.message.reply_text("Error al eliminar contacto.")

# --- SISTEMA DE MEMORIA ---

async def remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = ' '.join(context.args)
        if ' es ' not in text:
            await update.message.reply_text("Uso: /recuerda [clave] es [valor]")
            return
        
        parts = text.split(' es ', 1)
        key = parts[0].strip().lower()
        value = parts[1].strip()
        
        memory[key] = {
            "value": value,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_data(MEMORY_FILE, memory)
        await update.message.reply_text(f"🧠 Guardado: **{key}** = {value}", parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text("Error al guardar en memoria.")

async def recall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Uso: /memoria [clave]")
            return
        
        key = ' '.join(context.args).strip().lower()
        
        if key in memory:
            value = memory[key]['value']
            await update.message.reply_text(f"🧠 **{key}**: {value}", parse_mode='Markdown')
        else:
            # Buscar coincidencias parciales
            matches = [k for k in memory.keys() if key in k]
            if matches:
                msg = "🔍 Coincidencias encontradas:\n"
                for m in matches[:5]:
                    msg += f"• **{m}**: {memory[m]['value']}\n"
                await update.message.reply_text(msg, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ No encontré nada sobre: {key}")
                
    except Exception as e:
        await update.message.reply_text("Error al buscar en memoria.")

async def list_memories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not memory:
        await update.message.reply_text("🧠 La memoria está vacía.")
        return
    
    msg = "🧠 **MEMORIA**\n\n"
    for key, data in list(memory.items())[-15:]:  # Últimos 15
        msg += f"• **{key}**: {data['value'][:50]}...\n" if len(data['value']) > 50 else f"• **{key}**: {data['value']}\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# --- YOUTUBE DOWNLOADER ---

async def download_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Uso: /yt [url de YouTube]")
            return
        
        url = context.args[0]
        await update.message.reply_text("⏳ Descargando video...")
        
        # Usar yt-dlp para descargar
        output_template = os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s')
        
        process = subprocess.run(
            ['yt-dlp', '-f', 'best[height<=720]', '-o', output_template, url],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos máximo
        )
        
        if process.returncode == 0:
            # Buscar el archivo descargado más reciente
            files = [os.path.join(DOWNLOADS_DIR, f) for f in os.listdir(DOWNLOADS_DIR)]
            if files:
                latest_file = max(files, key=os.path.getctime)
                file_name = os.path.basename(latest_file)
                await update.message.reply_text(f"✅ Descargado: {file_name}")
                
                # Intentar enviar el video si es pequeño (< 50MB)
                if os.path.getsize(latest_file) < 50 * 1024 * 1024:
                    await update.message.reply_video(video=open(latest_file, 'rb'))
            else:
                await update.message.reply_text("✅ Descarga completada (archivo en servidor)")
        else:
            await update.message.reply_text(f"❌ Error: {process.stderr[:200]}")
            
    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ Timeout: El video es muy largo.")
    except FileNotFoundError:
        await update.message.reply_text("❌ yt-dlp no está instalado. Ejecuta: pip install yt-dlp")
    except Exception as e:
        logging.error(f"Error YT: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")

# --- MENSAJES GENERALES (Chat IA) ---

async def handle_gpt_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_name = update.effective_user.first_name

    # Respuestas rápidas
    text_lower = user_text.lower()
    if "cv" in text_lower or "hoja de vida" in text_lower:
        await update.message.reply_text("📄 Hoja de Vida:\nhttps://juancamiloasist.github.io/cami-asist/cv.html")
        return
    if "tarjeta" in text_lower or "tj" in text_lower or "contacto" in text_lower:
        await update.message.reply_text("💳 Tarjeta Digital:\nhttps://juancamiloasist.github.io/cami-asist/card.html")
        return

    # Procesamiento Neural (Gemini)
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        prompt = f"{SYSTEM_INSTRUCTIONS}\n\nInteracción actual:\nUsuario ({user_name}): {user_text}"
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        await update.message.reply_text(response.text)
        
    except Exception as e:
        logging.error(f"Error Gemini: {e}")
        await update.message.reply_text("⚠️ CRONOS: Error en enlace neural. Reintentando...")

# --- CONFIGURACIÓN PRINCIPAL ---

def main():
    if not TELEGRAM_TOKEN:
        print("Error: Falta TELEGRAM_TOKEN en .env")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers de comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cv", cv_command))
    application.add_handler(CommandHandler("tj", tj_command))
    application.add_handler(CommandHandler("links", links_command))
    
    # Agenda
    application.add_handler(CommandHandler("agendar", add_event))
    application.add_handler(CommandHandler("agenda", list_events))
    
    # Contactos
    application.add_handler(CommandHandler("contactos", list_contacts))
    application.add_handler(CommandHandler("addcontact", add_contact))
    application.add_handler(CommandHandler("delcontact", del_contact))
    
    # Memoria
    application.add_handler(CommandHandler("recuerda", remember))
    application.add_handler(CommandHandler("memoria", recall))
    application.add_handler(CommandHandler("memorias", list_memories))
    
    # YouTube
    application.add_handler(CommandHandler("yt", download_youtube))
    
    # Mensajes de texto (Cerebro Gemini)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gpt_message))

    print("⏳ CRONOS está en línea...")
    application.run_polling()

if __name__ == "__main__":
    main()
