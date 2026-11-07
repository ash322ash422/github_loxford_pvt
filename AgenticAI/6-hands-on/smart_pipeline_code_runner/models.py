"""Provider selection stays outside the workflow and its prompts."""
import json
import os
from dataclasses import dataclass, field
from typing import Any
from langchain.chat_models import init_chat_model


@dataclass
class ModelConfig:
    provider: str = 'openai'
    model: str = 'gpt-4.1-mini'
    base_url: str | None = None
    options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def resolve(cls, provider=None, model=None, base_url=None, options=None):
        provider = provider or os.getenv('SMART_PIPELINE_PROVIDER', 'openai')
        model = model or os.getenv('SMART_PIPELINE_MODEL')
        if not model:
            if provider != 'openai':
                raise ValueError('Set --model or SMART_PIPELINE_MODEL for the selected provider')
            model = 'gpt-4.1-mini'
        raw = options if options is not None else os.getenv('SMART_PIPELINE_MODEL_OPTIONS', '{}')
        try:
            extras = json.loads(raw)
        except (ValueError, TypeError) as e:
            raise ValueError('Model options must be a JSON object') from e
        if not isinstance(extras, dict):
            raise ValueError('Model options must be a JSON object')
        if {'model', 'model_provider', 'base_url'} & extras.keys():
            raise ValueError('Use the dedicated provider, model and base URL settings')
        return cls(provider, model, base_url or os.getenv('SMART_PIPELINE_BASE_URL'), extras)


def create_model(config: ModelConfig):
    kwargs = dict(config.options)
    if config.base_url:
        kwargs['base_url'] = config.base_url
    # Each integration reads its own credential environment variables.
    # Do not force temperature/retry arguments unsupported by some providers.
    return init_chat_model(config.model, model_provider=config.provider, **kwargs)


def generated_code(response):
    """Support both string content and provider-native text content blocks."""
    content = response.content
    if isinstance(content, str):
        code = content
    elif isinstance(content, list):
        code = '\n'.join(block['text'] for block in content
                         if isinstance(block, dict) and block.get('type') == 'text'
                         and isinstance(block.get('text'), str))
    else:
        code = ''
    code = code.strip()
    lines = code.splitlines()
    if len(lines) >= 2 and lines[0].strip() in {'```python', '```py', '```'} and lines[-1].strip() == '```':
        code = '\n'.join(lines[1:-1]).strip()
    if not code:
        raise ValueError('Model returned no text code (possibly a refusal or reasoning-only response)')
    return code
