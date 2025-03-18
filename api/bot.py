import os
import json
import time
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, Filters, Dispatcher
from datetime import datetime, timedelta

# Get the Telegram bot token from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = Bot(token=TELEGRAM_TOKEN)

# Image upload directory
UPLOAD_DIR = "/tmp/images"  # Vercel provides a temporary storage area at /tmp
IMAGE_LIST_FILE = "/tmp/image_list.json"  # A file to store the list of images
CHAT_ID_FILE = "/tmp/group_chat_id.json"  # File to store group chat_id

# Ensure the upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Load the image list (if any)
def load_image_list():
    if os.path.exists(IMAGE_LIST_FILE):
        with open(IMAGE_LIST_FILE, "r") as file:
            return json.load(file)
    return []

# Save the image list
def save_image_list(image_list):
    with open(IMAGE_LIST_FILE, "w") as file:
        json.dump(image_list, file)

# Add a new image to the list
def add_image_to_list(image_file_path):
    image_list = load_image_list()
    image_list.append(image_file_path)
    save_image_list(image_list)

# Load the group chat ID (if any)
def load_chat_id():
    if os.path.exists(CHAT_ID_FILE):
        with open(CHAT_ID_FILE, "r") as file:
            return json.load(file)["chat_id"]
    return None

# Save the group chat ID
def save_chat_id(chat_id):
    with open(CHAT_ID_FILE, "w") as file:
        json.dump({"chat_id": chat_id}, file)

def start(update, context):
    """Responds to the /start command."""
    update.message.reply_text("Hello! Send me a picture and I'll upload it.")

def echo(update, context):
    """Echoes the text sent by the user."""
    update.message.reply_text(update.message.text)

def upload_image(update, context):
    """Handles image upload."""
    if update.message.photo:
        # Get the highest quality photo
        photo_file = update.message.photo[-1].get_file()
        
        # Define the file path to save the image
        file_path = os.path.join(UPLOAD_DIR, f"{photo_file.file_id}.jpg")
        
        # Download the photo
        photo_file.download(file_path)
        
        # Add the uploaded image to the list
        add_image_to_list(file_path)
        
        # Send a confirmation message to the user
        update.message.reply_text(f"Image uploaded successfully! Saved as {file_path}.")
    else:
        update.message.reply_text("Please send a photo.")

def change_profile_picture():
    """Change the group profile picture to the next image in the list."""
    chat_id = load_chat_id()
    if chat_id is None:
        print("Chat ID not found. Make sure the bot has received a message from the group.")
        return
    
    image_list = load_image_list()
    
    if image_list:
        # Get the first image from the list
        image_path = image_list.pop(0)  # Get and remove the first image
        try:
            with open(image_path, "rb") as image_file:
                bot.set_chat_photo(chat_id=chat_id, photo=image_file)
                bot.send_message(chat_id=chat_id, text=f"Profile picture updated to: {image_path}")
        except Exception as e:
            bot.send_message(chat_id=chat_id, text=f"Failed to update profile picture: {e}")
        
        # Save the remaining image list
        save_image_list(image_list)
    else:
        bot.send_message(chat_id=chat_id, text="No images available to update the profile picture.")

def scheduled_task():
    """Call the profile picture change function weekly."""
    while True:
        # Change profile picture every week
        change_profile_picture()
        
        # Wait for one week (604800 seconds)
        time.sleep(604800)  # 7 days * 24 hours * 60 minutes * 60 seconds

def webhook(request):
    """Webhook handler to process Telegram updates."""
    dispatcher = Dispatcher(bot, None, workers=0)

    # Define command and message handlers
    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(Filters.text & ~Filters.command, echo)
    image_handler = MessageHandler(Filters.photo, upload_image)

    # Add handlers to the dispatcher
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(image_handler)

    # Handle the incoming Telegram update
    if request.method == "POST":
        update = Update.de_json(json.loads(request.data), bot)
        dispatcher.process_update(update)

        # Save the chat_id when the bot receives the first message
        if not load_chat_id():
            chat_id = update.message.chat.id
            save_chat_id(chat_id)
            bot.send_message(chat_id=chat_id, text="Chat ID saved successfully!")
    
    return "OK", 200
