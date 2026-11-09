import unittest
from types import SimpleNamespace
from unittest.mock import patch
from smart_pipeline.models import ModelConfig, create_model, generated_code


class ModelTests(unittest.TestCase):
    @patch.dict('os.environ', {}, clear=True)
    def test_defaults(self):
        self.assertEqual(ModelConfig.resolve(), ModelConfig())

    @patch.dict('os.environ', {'SMART_PIPELINE_PROVIDER': 'ollama', 'SMART_PIPELINE_MODEL': 'local-code',
                              'SMART_PIPELINE_BASE_URL': 'http://localhost:11434'}, clear=True)
    def test_environment_and_cli_precedence(self):
        config = ModelConfig.resolve()
        self.assertEqual(config.provider, 'ollama')
        self.assertEqual(config.model, 'local-code')
        self.assertEqual(ModelConfig.resolve(model='other').model, 'other')

    def test_factory_routes_without_forcing_provider_options(self):
        for provider in ['openai', 'anthropic', 'google_genai', 'ollama']:
            with self.subTest(provider=provider), patch('smart_pipeline.models.init_chat_model') as init:
                create_model(ModelConfig(provider=provider, model='coding-model'))
                init.assert_called_once_with('coding-model', model_provider=provider)
        with patch('smart_pipeline.models.init_chat_model') as init:
            create_model(ModelConfig('openai', 'local', 'http://localhost:8000/v1', {'temperature': 0}))
            init.assert_called_once_with('local', model_provider='openai', base_url='http://localhost:8000/v1', temperature=0)

    @patch.dict('os.environ', {}, clear=True)
    def test_invalid_configuration(self):
        for kwargs in [{'provider': 'ollama'}, {'options': '[]'}, {'options': 'invalid'},
                       {'options': '{"model_provider":"other"}'}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                ModelConfig.resolve(**kwargs)

    def test_provider_content_formats(self):
        self.assertEqual(generated_code(SimpleNamespace(content='```python\nprint(1)\n```')), 'print(1)')
        self.assertEqual(generated_code(SimpleNamespace(content=[{'type': 'thinking', 'thinking': 'private'},
            {'type': 'text', 'text': 'print(2)'}])), 'print(2)')
        with self.assertRaises(ValueError):
            generated_code(SimpleNamespace(content=[{'type': 'reasoning', 'text': 'no code'}]))
