import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    PORT = int(os.environ.get('PORT', 5000))

    # Database
    DATA_DIR = os.environ.get('DATA_DIR', './data')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATA_DIR}/db.sqlite"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API keys (can be overridden from DB settings)
    VK_TOKEN = os.environ.get('VK_TOKEN', '')
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID', '')

    # Processing
    TMP_DIR = '/tmp/vk_trafficker'
    OPENROUTER_MODEL = 'meta-llama/llama-3-8b-instruct'
    OPENROUTER_REQUEST_DELAY = 3  # seconds between requests
