from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta, datetime, timezone
import bcrypt
from ..config.database import get_db
from ..models.schemas import create_user, serialize_doc

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        name = data.get('name', '').strip()

        if not email or not password or not name:
            return jsonify({'error': 'Email, password, and name are required'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        db = get_db()

        # Check if email exists
        if db.users.find_one({'email': email}):
            return jsonify({'error': 'Email already registered'}), 409

        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Create user
        user_doc = create_user(email=email, password_hash=password_hash, name=name)
        result = db.users.insert_one(user_doc)
        user_id = str(result.inserted_id)

        # Create JWT token
        token = create_access_token(
            identity=user_id,
            expires_delta=timedelta(days=30)
        )

        return jsonify({
            'message': 'Account created successfully',
            'token': token,
            'user': {
                'id': user_id,
                'name': name,
                'email': email,
                'plan': 'free'
            }
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        db = get_db()
        user = db.users.find_one({'email': email})

        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401

        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({'error': 'Invalid email or password'}), 401

        # Update last login
        db.users.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.now(timezone.utc)}}
        )

        user_id = str(user['_id'])
        token = create_access_token(
            identity=user_id,
            expires_delta=timedelta(days=30)
        )

        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user_id,
                'name': user['name'],
                'email': user['email'],
                'plan': user.get('plan', 'free'),
                'avatar': user.get('avatar')
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    try:
        user_id = get_jwt_identity()
        db = get_db()

        from bson import ObjectId
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': {
                'id': str(user['_id']),
                'name': user['name'],
                'email': user['email'],
                'plan': user.get('plan', 'free'),
                'avatar': user.get('avatar'),
                'created_at': user['created_at'].isoformat() if isinstance(user.get('created_at'), datetime) else user.get('created_at')
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
