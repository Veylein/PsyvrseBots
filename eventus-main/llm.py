import os
import aiohttp
import asyncio

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

async def generate_chat(system: str, prompt: str, max_tokens: int = 150):
    if not OPENAI_API_KEY:
        return None
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': DEFAULT_MODEL,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': max_tokens,
        'temperature': 0.8
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENAI_URL, json=payload, headers=headers, timeout=30) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    return None
                data = await resp.json()
                # Support different response shapes
                if 'choices' in data and len(data['choices']):
                    content = data['choices'][0]['message']['content']
                    return content.strip()
                return None
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None

async def polish_text(text: str, tone: str = 'polished, professional, concise'):
    system = "You are a creative assistant that rewrites short announcements to be engaging and professional."
    prompt = f"Rewrite the following announcement to be {tone}. Keep placeholders like { '{event_id}' } and { '{title}' } unchanged.\n\nOriginal:\n{text}"
    out = await generate_chat(system, prompt, max_tokens=200)
    return out

async def craft_topic_from_keywords(keywords):
    system = "You are a community builder. Produce a single short discussion prompt (1-2 sentences) to spark conversation, based on keywords." 
    prompt = f"Keywords: {', '.join(keywords)}\n\nWrite a 1-2 sentence discussion topic that feels friendly and engaging." 
    out = await generate_chat(system, prompt, max_tokens=80)
    return out
