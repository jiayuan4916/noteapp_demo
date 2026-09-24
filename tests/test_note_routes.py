import unittest
from unittest.mock import Mock, patch

import requests
from src.main import app
from src.models.note import Note
from src.models.user import db


class NoteRouteValidationTests(unittest.TestCase):
    def setUp(self):
        app.config.update(
            TESTING=True,
            OPENROUTER_API_KEY='test-key',
            SQLALCHEMY_DATABASE_URI='sqlite://',
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )

        with app.app_context():
            db.drop_all()
            db.create_all()

        self.client = app.test_client()

    def test_create_note_requires_non_empty_title(self):
        response = self.client.post('/api/notes', json={'title': '   ', 'content': 'hello'})

        self.assertEqual(response.status_code, 400)
        self.assertIn('Title is required', response.get_json()['error'])

    def create_note(self):
        response = self.client.post(
            '/api/notes',
            json={'title': 'Travel plans', 'content': 'Visit Kyoto in spring.'},
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    @staticmethod
    def mocked_translation_response(title='旅行计划', content='春天去京都。'):
        response = Mock()
        response.json.return_value = {
            'choices': [{'message': {'content': f'{{"title": "{title}", "content": "{content}"}}'}}]
        }
        return response

    @patch('src.services.translation.requests.post')
    def test_translate_note_replaces_note_with_chinese_translation(self, mock_post):
        note = self.create_note()
        mock_post.return_value = self.mocked_translation_response()

        response = self.client.post(
            f"/api/notes/{note['id']}/translate",
            json={'target_language': 'zh'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['target_language'], 'zh')
        self.assertEqual(response.get_json()['title'], '旅行计划')
        self.assertEqual(response.get_json()['content'], '春天去京都。')
        with app.app_context():
            stored_note = db.session.get(Note, note['id'])
        self.assertEqual(stored_note.title, '旅行计划')
        self.assertEqual(stored_note.content, '春天去京都。')
        self.assertNotIn('test-key', mock_post.call_args.kwargs['json']['messages'][0]['content'])

    @patch('src.services.translation.requests.post')
    def test_translate_note_supports_japanese(self, mock_post):
        note = self.create_note()
        mock_post.return_value = self.mocked_translation_response('旅行計画', '春に京都を訪れる。')

        response = self.client.post(
            f"/api/notes/{note['id']}/translate",
            json={'target_language': 'ja'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['target_language'], 'ja')
        self.assertEqual(response.get_json()['content'], '春に京都を訪れる。')

    def test_translate_note_rejects_unsupported_language(self):
        note = self.create_note()

        response = self.client.post(
            f"/api/notes/{note['id']}/translate",
            json={'target_language': 'fr'},
        )

        self.assertEqual(response.status_code, 400)

    def test_translate_note_returns_not_found_for_missing_note(self):
        response = self.client.post(
            '/api/notes/999999/translate',
            json={'target_language': 'zh'},
        )

        self.assertEqual(response.status_code, 404)

    def test_translate_note_requires_api_key(self):
        note = self.create_note()
        app.config['OPENROUTER_API_KEY'] = None

        response = self.client.post(
            f"/api/notes/{note['id']}/translate",
            json={'target_language': 'zh'},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn('OPENROUTER_API_KEY', response.get_json()['error'])

    @patch('src.services.translation.requests.post')
    def test_translate_note_handles_provider_failure(self, mock_post):
        note = self.create_note()
        mock_post.return_value = Mock()
        mock_post.return_value.raise_for_status.side_effect = requests.RequestException('provider failed')

        response = self.client.post(
            f"/api/notes/{note['id']}/translate",
            json={'target_language': 'zh'},
        )

        self.assertEqual(response.status_code, 502)

    @patch('src.services.translation.requests.post')
    def test_translate_note_handles_malformed_provider_response(self, mock_post):
        note = self.create_note()
        mock_post.return_value = Mock()
        mock_post.return_value.json.return_value = {'choices': []}

        response = self.client.post(
            f"/api/notes/{note['id']}/translate",
            json={'target_language': 'zh'},
        )

        self.assertEqual(response.status_code, 502)

    def test_update_note_requires_non_empty_title(self):
        create_response = self.client.post('/api/notes', json={'title': 'Original', 'content': 'first version'})
        note_id = create_response.get_json()['id']

        response = self.client.put(
            f'/api/notes/{note_id}',
            json={'title': '   ', 'content': 'updated content'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('Title is required', response.get_json()['error'])


if __name__ == '__main__':
    unittest.main()
