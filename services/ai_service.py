import time
import requests

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
MODEL = 'meta-llama/llama-3-8b-instruct'

PROMPTS = {
    'RU': {
        'system': 'Ты копирайтер для Instagram Reels.',
        'user': (
            'Оригинальный заголовок: {title}\n'
            'Оригинальное описание: {description}\n\n'
            'Напиши:\n'
            'ЗАГОЛОВОК: короткий цепляющий (до 10 слов)\n'
            'ОПИСАНИЕ: история от первого лица, 200-300 слов, заканчивай вопросом, без хештегов.\n\n'
            'Формат ответа строго:\n'
            'ЗАГОЛОВОК: [текст]\n'
            'ОПИСАНИЕ: [текст]'
        ),
        'title_prefix': 'ЗАГОЛОВОК:',
        'caption_prefix': 'ОПИСАНИЕ:',
    },
    'EN': {
        'system': 'You are an Instagram Reels copywriter.',
        'user': (
            'Original title: {title}\n'
            'Original description: {description}\n\n'
            'Write:\n'
            'TITLE: short catchy (max 10 words)\n'
            'CAPTION: first-person story, 200-300 words, end with a question, no hashtags.\n\n'
            'Strict format:\n'
            'TITLE: [text]\n'
            'CAPTION: [text]'
        ),
        'title_prefix': 'TITLE:',
        'caption_prefix': 'CAPTION:',
    },
}


def generate_text(api_key, title, description, language='RU'):
    prompt = PROMPTS.get(language, PROMPTS['RU'])
    user_msg = prompt['user'].format(
        title=title or '',
        description=description or '',
    )

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://vk-trafficker.app',
        'X-Title': 'VK Reels Trafficker',
    }

    payload = {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': prompt['system']},
            {'role': 'user', 'content': user_msg},
        ],
        'max_tokens': 600,
        'temperature': 0.8,
    }

    response = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    content = response.json()['choices'][0]['message']['content'].strip()

    return _parse_response(content, prompt['title_prefix'], prompt['caption_prefix'])


def _parse_response(text, title_prefix, caption_prefix):
    title = ''
    caption = ''
    lines = text.split('\n')

    current = None
    caption_lines = []

    for line in lines:
        if line.startswith(title_prefix):
            title = line[len(title_prefix):].strip()
            current = 'title'
        elif line.startswith(caption_prefix):
            caption_lines.append(line[len(caption_prefix):].strip())
            current = 'caption'
        elif current == 'caption':
            caption_lines.append(line)

    caption = '\n'.join(caption_lines).strip()
    return title, caption
