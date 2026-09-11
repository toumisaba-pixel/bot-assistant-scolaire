import os
import io
import logging
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import google.generativeai as genai
from PIL import Image

# Configuration des logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialisation de Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
model = None

SYSTEM_INSTRUCTION = (
    "Tu es un Assistant Scolaire virtuel ultra-compétent, pédagogique, bienveillant et structuré. "
    "Ton objectif est d'aider les élèves à comprendre leurs cours, résoudre leurs exercices étape par étape "
    "sans donner directement la réponse brute sans explication. Si une image ou une photo d'exercice te est envoyée, "
    "lis attentivement l'énoncé de l'image et résous-le de manière détaillée."
)

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY.strip())
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_INSTRUCTION
        )
        logger.info("IA Gemini connectée avec succès !")
    except Exception as e:
        logger.error(f"Erreur d'initialisation Gemini : {e}")

# Serveur Web Flask (garder Render éveillé)
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Assistant Scolaire IA est en ligne 24/7 !"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Commandes Telegram
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"Bonjour {user_name} ! 🎓\n\n"
        "Je suis votre **Assistant Scolaire IA** intelligent.\n\n"
        "✨ **Ce que je peux faire pour vous :**\n"
        "• 📸 Analyser la photo de ton exercice ou cours\n"
        "• 📐 Résoudre et expliquer vos exercices étape par étape\n"
        "• 📖 Expliquer des cours complexes\n"
        "• 📝 Rédiger des résumés, rédactions et exposés\n\n"
        "Posez-moi une question par texte ou envoyez la photo de votre devoir !"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📚 **Guide d'utilisation**\n\n"
        "1. **Texte :** Posez directement votre question.\n"
        "2. **Photo :** Prenez en photo votre feuille d'exercice et envoyez-la ici !\n\n"
        "Tapez /start pour revenir au menu principal."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Réponses aux messages texte
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    if not model:
        await update.message.reply_text("⚠️ Clé GEMINI_API_KEY introuvable ou invalide sur Render.")
        return

    try:
        response = await asyncio.to_thread(model.generate_content, user_text)
        reply_text = response.text if response.text else "Désolé, je n'ai pas pu générer de réponse."

        try:
            await update.message.reply_text(reply_text, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(reply_text)

    except Exception as e:
        logger.error(f"Erreur Texte : {e}")
        await update.message.reply_text("❌ Erreur lors de la réponse de l'IA. Vérifiez l'état du serveur.")

# Réponses aux photos
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    caption = update.message.caption or "Analyse cette image et résous ou résume l'exercice présent dessus étape par étape."

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    if not model:
        await update.message.reply_text("⚠️ Clé GEMINI_API_KEY introuvable ou invalide sur Render.")
        return

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))

        response = await asyncio.to_thread(model.generate_content, [caption, image])
        reply_text = response.text if response.text else "Impossible d'analyser l'image."

        try:
            await update.message.reply_text(reply_text, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(reply_text)

    except Exception as e:
        logger.error(f"Erreur Photo : {e}")
        await update.message.reply_text("❌ Erreur lors de l'analyse de la photo. Assurez-vous que la photo est lisible.")

# Lancement
def main():
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TELEGRAM_TOKEN:
        logger.critical("TELEGRAM_TOKEN introuvable !")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN.strip()).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Bot Telegram en cours d'exécution...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
