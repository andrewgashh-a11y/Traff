# VK Reels Trafficker

Personal tool for downloading VK videos, processing with FFmpeg, generating Instagram Reels captions via AI, and posting to Telegram.

## Setup

### 1. Clone & install

```bash
git clone <repo>
cd vk-trafficker
pip install -r requirements.txt
```

FFmpeg must be installed locally (`brew install ffmpeg` / `apt install ffmpeg`).

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your keys (optional — all keys can be set from the UI Settings section)
```

### 3. Run

```bash
python app.py
```

Open http://localhost:5000

## Railway Deploy

1. Push repo to GitHub
2. Create new project on Railway → connect GitHub repo
3. Railway auto-detects `railway.toml` and installs FFmpeg via nixpacks
4. Set env vars in Railway dashboard (or use the UI Settings after deploy)
5. Add a **Volume** mounted at `/data` for persistent SQLite storage

## Required API Keys

| Key | Where to get |
|---|---|
| `VK_TOKEN` | VK → Settings → Security → App tokens (user token) |
| `OPENROUTER_API_KEY` | openrouter.ai → Keys |
| `TELEGRAM_BOT_TOKEN` | @BotFather on Telegram |
| `TELEGRAM_CHANNEL_ID` | Channel ID (e.g. `-100xxxxxxxxxx`) |

## Notes

- All API keys stored in SQLite, editable from the Settings panel
- Temp video files stored in `/tmp/` and deleted immediately after Telegram send
- OpenRouter free tier: 20 req/min — 3s delay is applied automatically between requests
- Max video size via Telegram Bot API: 50 MB (15s clips always fit)
