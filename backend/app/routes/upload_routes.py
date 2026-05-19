import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..config.database import get_db
from ..models.schemas import create_workspace, create_uploaded_file, serialize_doc
from ..services.ocr_service import (
    extract_text_from_image,
    extract_text_from_pdf,
    allowed_file,
    get_file_type
)
from ..services.gemini_service import (
    generate_structured_notes,
    generate_summary,
    generate_mermaid_diagram,
    generate_title_from_content,
    extract_key_topics
)

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    try:
        user_id = get_jwt_identity()

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Use JPG, PNG, PDF, or GIF'}), 400

        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, unique_filename)

        # Save file
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        file_type = get_file_type(file.filename)

        # Create workspace in DB (status: processing)
        db = get_db()
        workspace_doc = create_workspace(
            user_id=user_id,
            title=f"Processing: {file.filename}",
            source_type=file_type
        )
        workspace_doc['file_path'] = file_path
        workspace_doc['original_filename'] = file.filename
        workspace_doc['processing_progress'] = 10

        ws_result = db.workspaces.insert_one(workspace_doc)
        workspace_id = str(ws_result.inserted_id)

        # Save file record
        file_doc = create_uploaded_file(
            user_id=user_id,
            workspace_id=workspace_id,
            filename=unique_filename,
            file_type=file_type,
            file_path=file_path,
            file_size=file_size
        )
        file_doc['original_name'] = file.filename
        db.files.insert_one(file_doc)

        # Update progress: OCR running
        db.workspaces.update_one(
            {'_id': ws_result.inserted_id},
            {'$set': {'processing_progress': 25, 'status': 'processing'}}
        )

        # Extract text via OCR
        if file_type == 'image':
            ocr_result = extract_text_from_image(file_path)
        elif file_type == 'pdf':
            ocr_result = extract_text_from_pdf(file_path)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400

        if not ocr_result['success'] or not ocr_result['text']:
            db.workspaces.update_one(
                {'_id': ws_result.inserted_id},
                {'$set': {'status': 'error', 'error_message': ocr_result.get('error', 'OCR failed')}}
            )
            return jsonify({'error': 'Could not extract text from file', 'details': ocr_result.get('error')}), 422

        extracted_text = ocr_result['text']

        # Update progress: AI Processing
        db.workspaces.update_one(
            {'_id': ws_result.inserted_id},
            {'$set': {'processing_progress': 50, 'extracted_text': extracted_text}}
        )

        # Generate AI content
        try:
            title = generate_title_from_content(extracted_text)
        except:
            title = file.filename

        db.workspaces.update_one(
            {'_id': ws_result.inserted_id},
            {'$set': {'processing_progress': 60, 'title': title}}
        )

        try:
            notes = generate_structured_notes(extracted_text)
        except Exception as e:
            notes = extracted_text

        db.workspaces.update_one(
            {'_id': ws_result.inserted_id},
            {'$set': {'processing_progress': 75, 'notes': notes}}
        )

        try:
            summary = generate_summary(extracted_text, title)
        except:
            summary = ""

        db.workspaces.update_one(
            {'_id': ws_result.inserted_id},
            {'$set': {'processing_progress': 90, 'summary': summary}}
        )

        try:
            topics = extract_key_topics(extracted_text)
        except:
            topics = []

        # Mark as ready
        from datetime import datetime, timezone
        from bson import ObjectId
        db.workspaces.update_one(
            {'_id': ws_result.inserted_id},
            {'$set': {
                'status': 'ready',
                'processing_progress': 100,
                'tags': topics,
                'ocr_confidence': ocr_result.get('confidence', 0),
                'updated_at': datetime.now(timezone.utc)
            }}
        )

        # Update file record with extracted content
        db.files.update_one(
            {'workspace_id': workspace_id},
            {'$set': {
                'extracted_content': extracted_text,
                'ocr_confidence': ocr_result.get('confidence', 0)
            }}
        )

        # Create initial chat for the workspace
        from ..models.schemas import create_chat, create_message
        chat_doc = create_chat(workspace_id=workspace_id, user_id=user_id)
        initial_msg = create_message(
            'assistant',
            f"Hi! I've analyzed your notes on **{title}**. I've extracted the text, generated structured notes, and created a summary. Ask me anything about this content!"
        )
        chat_doc['messages'] = [initial_msg]
        db.chats.insert_one(chat_doc)

        return jsonify({
            'message': 'File processed successfully',
            'workspace_id': workspace_id,
            'title': title,
            'extracted_text': extracted_text[:500] + '...' if len(extracted_text) > 500 else extracted_text,
            'word_count': ocr_result.get('word_count', 0),
            'ocr_confidence': ocr_result.get('confidence', 0),
            'topics': topics,
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
