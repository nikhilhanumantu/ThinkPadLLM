from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from ..config.database import get_db
from ..models.schemas import create_message, serialize_doc
from ..services.gemini_service import (
    chat_with_context,
    stream_chat_with_context,
    generate_summary,
    generate_explanation,
    generate_mermaid_diagram,
    generate_quiz,
    generate_flashcards,
    generate_structured_notes
)
import json

ai_bp = Blueprint('ai', __name__)


def get_workspace_context(workspace_id: str, user_id: str) -> dict:
    """Get workspace and its content for AI context."""
    db = get_db()
    workspace = db.workspaces.find_one({
        '_id': ObjectId(workspace_id),
        'user_id': user_id
    })
    return workspace


@ai_bp.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        workspace_id = data.get('workspace_id')
        user_message = data.get('message', '').strip()
        stream = data.get('stream', False)

        if not user_message:
            return jsonify({'error': 'Message is required'}), 400

        db = get_db()

        # Get or create chat
        chat_doc = None
        if workspace_id:
            chat_doc = db.chats.find_one({
                'workspace_id': workspace_id,
                'user_id': user_id
            })

        if not chat_doc:
            from ..models.schemas import create_chat
            chat_doc = create_chat(workspace_id=workspace_id or '', user_id=user_id)
            result = db.chats.insert_one(chat_doc)
            chat_doc['_id'] = result.inserted_id
            chat_doc['messages'] = []

        # Get context from workspace
        context = ""
        if workspace_id:
            try:
                workspace = db.workspaces.find_one({
                    '_id': ObjectId(workspace_id),
                    'user_id': user_id
                })
                if workspace:
                    context = workspace.get('extracted_text', '') or workspace.get('notes', '')
            except:
                pass

        messages = chat_doc.get('messages', [])

        # Add user message to history
        user_msg = create_message('user', user_message)
        messages.append(user_msg)

        if stream:
            # Streaming response
            def generate():
                full_response = ""
                try:
                    for chunk in stream_chat_with_context(messages, context, user_message):
                        full_response += chunk
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                finally:
                    # Save the complete response to DB
                    if full_response:
                        ai_msg = create_message('assistant', full_response)
                        messages.append(ai_msg)
                        from datetime import datetime, timezone
                        db.chats.update_one(
                            {'_id': chat_doc['_id']},
                            {'$set': {
                                'messages': messages[-50:],  # Keep last 50 messages
                                'updated_at': datetime.now(timezone.utc)
                            }}
                        )
                    yield f"data: {json.dumps({'done': True})}\n\n"

            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            # Regular response
            ai_response = chat_with_context(messages, context, user_message)

            # Save messages to DB
            ai_msg = create_message('assistant', ai_response)
            messages.append(ai_msg)

            from datetime import datetime, timezone
            db.chats.update_one(
                {'_id': chat_doc['_id']},
                {'$set': {
                    'messages': messages[-50:],
                    'updated_at': datetime.now(timezone.utc)
                }}
            )

            # Check if response contains a diagram
            contains_diagram = '[DIAGRAM]:' in ai_response
            mermaid_code = None
            if contains_diagram:
                parts = ai_response.split('[DIAGRAM]:')
                if len(parts) > 1:
                    mermaid_code = parts[1].strip()

            return jsonify({
                'response': ai_response,
                'contains_diagram': contains_diagram,
                'mermaid_code': mermaid_code,
                'chat_id': str(chat_doc['_id'])
            }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/summary', methods=['POST'])
@jwt_required()
def generate_summary_route():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        workspace_id = data.get('workspace_id')

        if not workspace_id:
            return jsonify({'error': 'workspace_id is required'}), 400

        db = get_db()
        workspace = db.workspaces.find_one({
            '_id': ObjectId(workspace_id),
            'user_id': user_id
        })

        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404

        text = workspace.get('extracted_text', '')
        if not text:
            return jsonify({'error': 'No content to summarize'}), 400

        summary = generate_summary(text, workspace.get('title', ''))

        # Save to workspace
        from datetime import datetime, timezone
        db.workspaces.update_one(
            {'_id': ObjectId(workspace_id)},
            {'$set': {'summary': summary, 'updated_at': datetime.now(timezone.utc)}}
        )

        return jsonify({'summary': summary}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/explain', methods=['POST'])
@jwt_required()
def generate_explanation_route():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        workspace_id = data.get('workspace_id')

        if not workspace_id:
            return jsonify({'error': 'workspace_id is required'}), 400

        db = get_db()
        workspace = db.workspaces.find_one({
            '_id': ObjectId(workspace_id),
            'user_id': user_id
        })

        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404

        text = workspace.get('extracted_text', '')
        if not text:
            return jsonify({'error': 'No content to explain'}), 400

        explanation = generate_explanation(text, workspace.get('title', ''))

        from datetime import datetime, timezone
        db.workspaces.update_one(
            {'_id': ObjectId(workspace_id)},
            {'$set': {'explanation': explanation, 'updated_at': datetime.now(timezone.utc)}}
        )

        return jsonify({'explanation': explanation}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/flowchart', methods=['POST'])
@jwt_required()
def generate_flowchart():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        workspace_id = data.get('workspace_id')
        custom_text = data.get('text')  # Optional custom text

        db = get_db()

        text = custom_text
        if not text and workspace_id:
            workspace = db.workspaces.find_one({
                '_id': ObjectId(workspace_id),
                'user_id': user_id
            })
            if workspace:
                text = workspace.get('extracted_text', '') or workspace.get('notes', '')

        if not text:
            return jsonify({'error': 'No content available to generate diagram'}), 400

        mermaid_code = generate_mermaid_diagram(text)

        if workspace_id:
            from datetime import datetime, timezone
            db.workspaces.update_one(
                {'_id': ObjectId(workspace_id)},
                {'$set': {'mermaid_diagram': mermaid_code, 'updated_at': datetime.now(timezone.utc)}}
            )

        return jsonify({'mermaid_code': mermaid_code}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/quiz', methods=['POST'])
@jwt_required()
def generate_quiz_route():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        workspace_id = data.get('workspace_id')
        num_questions = data.get('num_questions', 5)

        db = get_db()
        workspace = db.workspaces.find_one({
            '_id': ObjectId(workspace_id),
            'user_id': user_id
        })

        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404

        text = workspace.get('extracted_text', '')
        if not text:
            return jsonify({'error': 'No content to generate quiz from'}), 400

        quiz = generate_quiz(text, num_questions)

        from datetime import datetime, timezone
        db.workspaces.update_one(
            {'_id': ObjectId(workspace_id)},
            {'$set': {'quiz': quiz, 'updated_at': datetime.now(timezone.utc)}}
        )

        return jsonify({'quiz': quiz}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/flashcards', methods=['POST'])
@jwt_required()
def generate_flashcards_route():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        workspace_id = data.get('workspace_id')

        db = get_db()
        workspace = db.workspaces.find_one({
            '_id': ObjectId(workspace_id),
            'user_id': user_id
        })

        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404

        text = workspace.get('extracted_text', '')
        if not text:
            return jsonify({'error': 'No content to generate flashcards from'}), 400

        flashcards = generate_flashcards(text)

        from datetime import datetime, timezone
        db.workspaces.update_one(
            {'_id': ObjectId(workspace_id)},
            {'$set': {'flashcards': flashcards, 'updated_at': datetime.now(timezone.utc)}}
        )

        return jsonify({'flashcards': flashcards}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/notes', methods=['POST'])
@jwt_required()
def generate_notes_route():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        workspace_id = data.get('workspace_id')

        db = get_db()
        workspace = db.workspaces.find_one({
            '_id': ObjectId(workspace_id),
            'user_id': user_id
        })

        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404

        text = workspace.get('extracted_text', '')
        if not text:
            return jsonify({'error': 'No content available'}), 400

        notes = generate_structured_notes(text)

        from datetime import datetime, timezone
        db.workspaces.update_one(
            {'_id': ObjectId(workspace_id)},
            {'$set': {'notes': notes, 'updated_at': datetime.now(timezone.utc)}}
        )

        return jsonify({'notes': notes}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/history', methods=['GET'])
@jwt_required()
def get_chat_history():
    try:
        user_id = get_jwt_identity()
        workspace_id = request.args.get('workspace_id')

        db = get_db()
        query = {'user_id': user_id}
        if workspace_id:
            query['workspace_id'] = workspace_id

        chat = db.chats.find_one(query, sort=[('updated_at', -1)])
        if not chat:
            return jsonify({'messages': []}), 200

        messages = chat.get('messages', [])
        return jsonify({
            'messages': messages,
            'chat_id': str(chat['_id'])
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
