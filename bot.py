import os
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

# --- Configuration des Logs ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Initialisation de l'IA Google Gemini ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=(
                "Tu es un Assistant Scolaire virtuel ultra-compétent, pédagogique, bienveillant et structuré. "
                "Ton objectif est d'aider les élèves (collège, lycée, université) à comprendre leurs cours, "
                "résoudre leurs exercices étape par étape sans donner directement la réponse brute sans explication, "
                "et résumer leurs leçons. Réponds de façon claire avec un ton encourageant."
            )
        )
        logger.info("IA Gemini configurée avec succès !")
    except Exception as e:
        logger.error(f"Erreur lors de la configuration de Gemini : {e}")

# --- Serveur Web Flask (Keep-Alive Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Assistant Scolaire IA est en ligne 24/7 !"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- Handlers Telegram ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"Bonjour **{user_name}** ! 🎓\n\n"
        "Je suis votre **Assistant Scolaire IA** intelligent.\n\n"
        "✨ **Ce que je peux faire pour vous :**\n"
        "• 📐 Résoudre et expliquer vos exercices (Maths, PC, SVT...)\n"
        "• 📖 Expliquer des cours complexes\n"
        "• 📝 Rédiger des résumés, rédactions et exposés\n"
        "• 💡 Proposer des sujets d'entraînement\n\n"
        "Posez-moi simplement votre question ci-dessous !"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📚 **Guide d'utilisation**\n\n"
        "1. Ecrivez directement votre exercice ou question.\n"
        "2. Soyez le plus clair possible dans l'énoncé.\n"
        "3. Exemple : *'Explique-moi la réaction de photosynthèse en SVT.'*\n\n"
        "Tapez /start pour revenir au menu principal."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id

    # Indiquer que le bot écrit
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    if not model:
        fallback_text = (
            f"📚 **Question reçue :** *\"{user_text}\"*\n\n"
            "⚠️ L'IA n'est pas encore connectée. N'oubliez pas d'ajouter la variable `GEMINI_API_KEY` dans Render !"
        )
        await update.message.reply_text(fallback_text, parse_mode='Markdown')
        return

    try:
        # Appel asynchrone à l'IA
        response = await asyncio.to_thread(model.generate_content, user_text)
        reply_text = response.text if response.text else "Désolé, je n'ai pas pu générer de réponse."
        await update.message.reply_text(reply_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Erreur IA : {e}")
        await update.message.reply_text("❌ Une erreur est survenue lors de la génération. Réessayez dans un instant.")

# --- Démarrage principal ---
def main():
    # Lancement du serveur Web dans un thread séparé
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Clé API Telegram
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TELEGRAM_TOKEN:
        logger.critical("TELEGRAM_TOKEN introuvable !")
        return

    # Application Telegram
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Lancement du bot Telegram...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
