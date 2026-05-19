from datetime import datetime, timezone
from bson import ObjectId

def create_user(email: str, password_hash: str, name: str, auth_provider: str = "local", google_id: str = None):
    return {
        "email": email,
        "password_hash": password_hash,
        "name": name,
        "auth_provider": auth_provider,  # "local" | "google"
        "google_id": google_id,
        "avatar": None,
        "plan": "free",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_login": datetime.now(timezone.utc),
    }

def create_workspace(user_id: str, title: str, source_type: str):
    """
    source_type: "image" | "pdf" | "youtube" | "text"
    """
    return {
        "user_id": user_id,
        "title": title,
        "source_type": source_type,
        "source_url": None,
        "file_path": None,
        "extracted_text": "",
        "summary": "",
        "explanation": "",
        "notes": "",
        "mermaid_diagram": "",
        "quiz": [],
        "flashcards": [],
        "tags": [],
        "status": "processing",  # "processing" | "ready" | "error"
        "processing_progress": 0,
        "archived": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

def create_chat(workspace_id: str, user_id: str):
    return {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "messages": [],
        "context_summary": "",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

def create_message(role: str, content: str):
    """role: 'user' | 'assistant'"""
    return {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

def create_uploaded_file(user_id: str, workspace_id: str, filename: str, file_type: str, file_path: str, file_size: int):
    return {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "filename": filename,
        "original_name": filename,
        "file_type": file_type,
        "file_path": file_path,
        "file_size": file_size,
        "extracted_content": "",
        "ocr_confidence": 0.0,
        "created_at": datetime.now(timezone.utc),
    }

def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    doc = dict(doc)
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    if 'user_id' in doc and isinstance(doc['user_id'], ObjectId):
        doc['user_id'] = str(doc['user_id'])
    if 'workspace_id' in doc and isinstance(doc['workspace_id'], ObjectId):
        doc['workspace_id'] = str(doc['workspace_id'])
    # Convert datetime objects
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc
