from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..config.database import get_db
from ..models.schemas import create_workspace, serialize_doc
from ..services.youtube_service import extract_video_id, get_transcript
from ..services.gemini_service import (
    generate_summary,
    generate_structured_notes,
    generate_title_from_content,
    extract_key_topics
)
from datetime import datetime, timezone

video_bp = Blueprint('video', __name__)


@video_bp.route('/video-import', methods=['POST'])
@jwt_required()
def import_video():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        url = data.get('url', '').strip()

        if not url:
            return jsonify({'error': 'YouTube URL is required'}), 400

        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL. Please provide a valid YouTube video link.'}), 400

        db = get_db()

        # Create workspace with processing status
        workspace_doc = create_workspace(
            user_id=user_id,
            title=f"Video: {url}",
            source_type="youtube"
        )
        workspace_doc['source_url'] = url
        workspace_doc['video_id'] = video_id
        workspace_doc['processing_progress'] = 10

        ws_result = db.workspaces.insert_one(workspace_doc)
        workspace_id = str(ws_result.inserted_id)

        # Fetch transcript
        db.workspaces.update_one(
            {'_id': ws_result.inserted_id},
            {'$set': {'processing_progress': 30, 'status_message': 'Fetching transcript...'}}
        )

        transcript_result = get_transcript(video_id)

        if not transcript_result['success']:
            db.workspaces.update_one(
                {'_id': ws_result.inserted_id},
                {'$set': {
                    'status': 'error',
                    'error_message': transcript_result.get('error', 'Transcript unavailable')
                }}
            )
            return jsonify({
                'error': transcript_result.get('error', 'Could not fetch transcript')
            }), 422

        transcript = transcript_result['transcript']
        segments = transcript_result.get('segments', [])

        db.workspaces.update_one(
            {'_id': ws_result.inserted_id},
            {'$set': {
                'processing_progress': 50,
                'extracted_text': transcript,
                'segments': segments,
            }}
        )

        # Generate AI content
        try:
            title = generate_title_from_content(transcript)
        except:
            title = f"Video Lecture {video_id}"

        db.workspaces.update_one(
            {'_id': ws_result.inserted_id},
            {'$set': {'title': title, 'processing_progress': 60}}
        )

        try:
            notes = generate_structured_notes(transcript)
        except:
            notes = transcript

        db.workspaces.update_one(
            {'_id': ws_result.inserted_id},
            {'$set': {'notes': notes, 'processing_progress': 75}}
        )

        try:
            summary = generate_summary(transcript, title)
        except:
            summary = ""

        try:
            topics = extract_key_topics(transcript)
        except:
            topics = []

        # Mark as ready
        db.workspaces.update_one(
            {'_id': ws_result.inserted_id},
            {'$set': {
                'status': 'ready',
                'processing_progress': 100,
                'title': title,
                'summary': summary,
                'tags': topics,
                'updated_at': datetime.now(timezone.utc),
                'duration': transcript_result.get('duration', 0),
                'word_count': transcript_result.get('word_count', 0),
            }}
        )

        # Create initial chat
        from ..models.schemas import create_chat, create_message
        chat_doc = create_chat(workspace_id=workspace_id, user_id=user_id)
        chat_doc['messages'] = [create_message(
            'assistant',
            f"I've processed the video **\"{title}\"**. The transcript has been extracted and structured into notes. What would you like to know about this lecture?"
        )]
        db.chats.insert_one(chat_doc)

        return jsonify({
            'message': 'Video processed successfully',
            'workspace_id': workspace_id,
            'title': title,
            'word_count': transcript_result.get('word_count', 0),
            'duration': transcript_result.get('duration', 0),
            'segments': segments[:5],  # Return first 5 segments as preview
            'topics': topics,
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500
