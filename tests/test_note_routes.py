import unittest

from src.main import app
from src.models.user import db


class NoteRouteValidationTests(unittest.TestCase):
    def setUp(self):
        app.config.update(
            TESTING=True,
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
