import asyncio
import telegram


def send_video_and_caption(bot_token, channel_id, video_path, title, caption):
    """Send video file then text caption to Telegram channel."""
    asyncio.run(_send(bot_token, channel_id, video_path, title, caption))


async def _send(bot_token, channel_id, video_path, title, caption):
    bot = telegram.Bot(token=bot_token)

    with open(video_path, 'rb') as f:
        await bot.send_video(
            chat_id=channel_id,
            video=f,
            supports_streaming=True,
        )

    text = f"📌 НАЗВАНИЕ:\n{title}\n\n📝 ОПИСАНИЕ:\n{caption}"
    await bot.send_message(chat_id=channel_id, text=text)


def send_test_message(bot_token, channel_id):
    asyncio.run(_send_test(bot_token, channel_id))


async def _send_test(bot_token, channel_id):
    bot = telegram.Bot(token=bot_token)
    await bot.send_message(
        chat_id=channel_id,
        text="✅ VK Reels Trafficker — тестовое сообщение. Бот работает!",
    )
