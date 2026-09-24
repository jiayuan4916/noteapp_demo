import json
import os

import requests

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
OPENROUTER_MODEL = 'deepseek/deepseek-v4-flash'
SUPPORTED_LANGUAGES = {
    'zh': 'Simplified Chinese',
    'ja': 'Japanese',
}


class TranslationError(Exception):
    """Base error for translation failures."""


class TranslationConfigurationError(TranslationError):
    """Raised when translation configuration is missing."""


class TranslationProviderError(TranslationError):
    """Raised when the translation provider cannot fulfill a request."""


def translate_note(title, content, target_language, api_key=None):
    if target_language not in SUPPORTED_LANGUAGES:
        raise ValueError('Unsupported target language')

    if api_key is None:
        api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        raise TranslationConfigurationError('OPENROUTER_API_KEY is not configured')

    language_name = SUPPORTED_LANGUAGES[target_language]
    prompt = (
        f'Translate the following note into {language_name}. Preserve the meaning, '
        'tone, paragraph breaks, and formatting. Return only a valid JSON object with '
        'two string fields: "title" and "content". Do not include markdown fences.\n\n'
        f'Title:\n{title}\n\nContent:\n{content}'
    )
    payload = {
        'model': OPENROUTER_MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.2,
    }

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        response_data = response.json()
    except requests.RequestException as exc:
        raise TranslationProviderError('Translation provider request failed') from exc
    except ValueError as exc:
        raise TranslationProviderError('Translation provider returned invalid JSON') from exc

    try:
        translated_text = response_data['choices'][0]['message']['content']
        translated = json.loads(translated_text)
        translated_title = translated['title']
        translated_content = translated['content']
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise TranslationProviderError('Translation provider returned an invalid translation') from exc

    if not isinstance(translated_title, str) or not isinstance(translated_content, str):
        raise TranslationProviderError('Translation provider returned an invalid translation')

    return {
        'title': translated_title,
        'content': translated_content,
    }
