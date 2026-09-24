from flask import Blueprint, current_app, jsonify, request
from src.models.note import Note, db
from src.services.translation import (
    SUPPORTED_LANGUAGES,
    TranslationConfigurationError,
    TranslationProviderError,
    translate_note,
)

note_bp = Blueprint('note', __name__)


def _validate_title(title_value):
    if title_value is None or not str(title_value).strip():
        raise ValueError('Title is required')
    return str(title_value).strip()


@note_bp.route('/notes', methods=['GET'])
def get_notes():
    """Get all notes, ordered by most recently updated"""
    notes = Note.query.order_by(Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])

@note_bp.route('/notes', methods=['POST'])
def create_note():
    """Create a new note"""
    try:
        data = request.json
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400

        title = _validate_title(data['title'])
        content = data['content']

        if content is None:
            return jsonify({'error': 'Title and content are required'}), 400

        note = Note(title=title, content=content)
        db.session.add(note)
        db.session.commit()
        return jsonify(note.to_dict()), 201
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """Get a specific note by ID"""
    note = Note.query.get_or_404(note_id)
    return jsonify(note.to_dict())


@note_bp.route('/notes/<int:note_id>/translate', methods=['POST'])
def translate_note_route(note_id):
    """Translate and replace a stored note."""
    note = Note.query.get_or_404(note_id)
    data = request.get_json(silent=True) or {}
    target_language = data.get('target_language')

    if target_language not in SUPPORTED_LANGUAGES:
        return jsonify({'error': 'Target language must be zh or ja'}), 400

    try:
        translation = translate_note(
            note.title,
            note.content,
            target_language,
            api_key=current_app.config.get('OPENROUTER_API_KEY') or '',
        )
        note.title = translation['title']
        note.content = translation['content']
        db.session.commit()
        return jsonify({
            'target_language': target_language,
            **note.to_dict(),
        })
    except TranslationConfigurationError as exc:
        return jsonify({'error': str(exc)}), 503
    except TranslationProviderError as exc:
        return jsonify({'error': str(exc)}), 502
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """Update a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        if 'title' not in data:
            return jsonify({'error': 'Title is required'}), 400

        title = _validate_title(data.get('title', note.title))
        content = data.get('content', note.content)
        if content is None:
            return jsonify({'error': 'Content is required'}), 400

        note.title = title
        note.content = content
        db.session.commit()
        return jsonify(note.to_dict())
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        db.session.delete(note)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/search', methods=['GET'])
def search_notes():
    """Search notes by title or content"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    notes = Note.query.filter(
        (Note.title.contains(query)) | (Note.content.contains(query))
    ).order_by(Note.updated_at.desc()).all()
    
    return jsonify([note.to_dict() for note in notes])

