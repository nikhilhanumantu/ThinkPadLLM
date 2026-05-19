import os
from pymongo import MongoClient, TEXT
from dotenv import load_dotenv

load_dotenv()

_client = None
_db = None

def init_db(app):
    global _client, _db
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        raise ValueError("MONGO_URI environment variable is not set")
    _client = MongoClient(mongo_uri)
    _db = _client.get_database()

    # Create text indexes for search
    try:
        _db.workspaces.create_index([
            ("title", TEXT),
            ("extracted_text", TEXT),
            ("summary", TEXT)
        ])
        _db.chats.create_index([("messages.content", TEXT)])
    except Exception as e:
        print(f"Index creation warning: {e}")

    app.db = _db
    print("Connected to MongoDB Atlas")
    return _db

def get_db():
    global _db
    if _db is None:
        mongo_uri = os.getenv('MONGO_URI')
        _client = MongoClient(mongo_uri)
        _db = _client.get_database()
    return _db
