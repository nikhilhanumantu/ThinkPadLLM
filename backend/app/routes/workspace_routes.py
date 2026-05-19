from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime, timezone
from ..config.database import get_db
from ..models.schemas import serialize_doc

workspace_bp = Blueprint('workspace', __name__)


@workspace_bp.route('/workspaces', methods=['GET'])
@jwt_required()
def get_workspaces():
    try:
        user_id = get_jwt_identity()
        db = get_db()

        archived = request.args.get('archived', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 20))
        skip = int(request.args.get('skip', 0))

        query = {
            'user_id': user_id,
            'archived': archived
        }

        workspaces = list(db.workspaces.find(
            query,
            {'extracted_text': 0, 'notes': 0, 'explanation': 0}  # Exclude large fields
        ).sort('updated_at', -1).skip(skip).limit(limit))

        total = db.workspaces.count_documents(query)

        return jsonify({
            'workspaces': [serialize_doc(w) for w in workspaces],
            'total': total,
            'skip': skip,
            'limit': limit
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workspace_bp.route('/workspaces/<workspace_id>', methods=['GET'])
@jwt_required()
def get_workspace(workspace_id):
    try:
        user_id = get_jwt_identity()
        db = get_db()

        workspace = db.workspaces.find_one({
            '_id': ObjectId(workspace_id),
            'user_id': user_id
        })

        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404

        # Get associated chat
        chat = db.chats.find_one({
            'workspace_id': workspace_id,
            'user_id': user_id
        })

        result = serialize_doc(workspace)
        result['chat_history'] = chat.get('messages', []) if chat else []

        return jsonify({'workspace': result}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workspace_bp.route('/workspaces/<workspace_id>', methods=['PUT'])
@jwt_required()
def update_workspace(workspace_id):
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        db = get_db()

        # Only allow certain fields to be updated
        allowed_fields = {'title', 'notes', 'tags', 'archived'}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        update_data['updated_at'] = datetime.now(timezone.utc)

        result = db.workspaces.update_one(
            {'_id': ObjectId(workspace_id), 'user_id': user_id},
            {'$set': update_data}
        )

        if result.matched_count == 0:
            return jsonify({'error': 'Workspace not found'}), 404

        return jsonify({'message': 'Workspace updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workspace_bp.route('/workspaces/<workspace_id>', methods=['DELETE'])
@jwt_required()
def delete_workspace(workspace_id):
    try:
        user_id = get_jwt_identity()
        db = get_db()

        result = db.workspaces.delete_one({
            '_id': ObjectId(workspace_id),
            'user_id': user_id
        })

        if result.deleted_count == 0:
            return jsonify({'error': 'Workspace not found'}), 404

        # Also delete associated chats and files
        db.chats.delete_many({'workspace_id': workspace_id})
        db.files.delete_many({'workspace_id': workspace_id})

        return jsonify({'message': 'Workspace deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workspace_bp.route('/workspaces/<workspace_id>/archive', methods=['POST'])
@jwt_required()
def archive_workspace(workspace_id):
    try:
        user_id = get_jwt_identity()
        db = get_db()

        workspace = db.workspaces.find_one({
            '_id': ObjectId(workspace_id),
            'user_id': user_id
        })
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404

        new_archived = not workspace.get('archived', False)
        db.workspaces.update_one(
            {'_id': ObjectId(workspace_id)},
            {'$set': {'archived': new_archived, 'updated_at': datetime.now(timezone.utc)}}
        )

        return jsonify({
            'message': f'Workspace {"archived" if new_archived else "unarchived"} successfully',
            'archived': new_archived
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workspace_bp.route('/search', methods=['POST'])
@jwt_required()
def search_workspaces():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        query_text = data.get('query', '').strip()

        if not query_text:
            return jsonify({'results': []}), 200

        db = get_db()

        # Text search using MongoDB text index
        try:
            results = list(db.workspaces.find(
                {
                    '$text': {'$search': query_text},
                    'user_id': user_id
                },
                {
                    'score': {'$meta': 'textScore'},
                    'extracted_text': 0
                }
            ).sort([('score', {'$meta': 'textScore'})]).limit(10))
        except Exception:
            # Fallback: regex search
            results = list(db.workspaces.find({
                'user_id': user_id,
                '$or': [
                    {'title': {'$regex': query_text, '$options': 'i'}},
                    {'summary': {'$regex': query_text, '$options': 'i'}},
                ]
            }, {'extracted_text': 0}).limit(10))

        return jsonify({
            'results': [serialize_doc(r) for r in results],
            'query': query_text
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@workspace_bp.route('/workspaces/<workspace_id>/share', methods=['POST'])
@jwt_required()
def create_share_link(workspace_id):
    try:
        user_id = get_jwt_identity()
        db = get_db()
        import uuid

        workspace = db.workspaces.find_one({
            '_id': ObjectId(workspace_id),
            'user_id': user_id
        })
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404

        # Generate a share token
        share_token = workspace.get('share_token') or uuid.uuid4().hex
        db.workspaces.update_one(
            {'_id': ObjectId(workspace_id)},
            {'$set': {'share_token': share_token, 'is_public': True}}
        )

        share_url = f"http://localhost:5173/shared/{share_token}"
        return jsonify({'share_url': share_url, 'share_token': share_token}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
