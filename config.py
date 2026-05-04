import os
from dotenv import load_dotenv

load_dotenv()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    PORT = int(os.environ.get('PORT', 5000))

    # Database — always absolute so SQLite can find/create the file
    DATA_DIR = os.path.abspath(os.environ.get('DATA_DIR', os.path.join(_BASE_DIR, 'data')))
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
