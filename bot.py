import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Serveur Web Flask pour garder le bot éveillé ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Le bot est en ligne et fonctionnel !"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- Logic du Bot Telegram ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"Bonjour {user_name} ! 👋\n\n"
        "Je suis votre **Assistant Scolaire**. Je peux vous aider à :\n"
        "• Résoudre vos exercices (Maths, Physique-Chimie, etc.)\n"
        "• Expliquer vos cours\n"
        "• Rédiger des sujets et résumés\n\n"
        "Envoyez-moi votre question ou l'énoncé de votre exercice !"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📚 **Aide Assistant Scolaire**\n\n"
        "Posez simplement votre question directement par message.\n"
        "Exemple : *Explique-moi le théorème de Pythagore* ou *Aide-moi à équilibrer cette équation chimique.*"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # Réponse automatique d'accueil aux questions
    response = (
        f"J'ai bien reçu votre question : *\"{text}\"*\n\n"
        "Posez vos questions de devoirs, cours ou exercices, et je vous guiderai pas à pas !"
    )
    await update.message.reply_text(response, parse_mode='Markdown')

def main():
    # Lancement du serveur Web Flask en arrière-plan
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    # Récupération du TOKEN Telegram depuis les variables d'environnement
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        print("Erreur : La variable TELEGRAM_TOKEN n'est pas configurée.")
        return

    # Initialisation de l'application Telegram
    application = ApplicationBuilder().token(TOKEN).build()

    # Ajout des gestionnaires de commandes
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Lancement du bot en mode polling
    application.run_polling()

if __name__ == '__main__':
    main()
