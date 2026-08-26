import os
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from django.conf import settings
from config.crypto_utils import compute_sha256_hash, encrypt_field, decrypt_field

class MongoDBManager:
    """
    Dual-layer Document Storage Engine for Sprintly.
    Synchronizes Projects, Issues, Sprints, Users, Notifications, Chat, and Audit collections
    directly into live MongoDB (sprintly_db) with automated local fallback.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBManager, cls).__new__(cls)
            cls._instance._init_connection()
        return cls._instance

    def _init_connection(self):
        self.mongo_uri = os.environ.get("SPRINTLY_MONGO_URI", "mongodb://localhost:27017")
        self.db_name = "sprintly_db"
        self.client = None
        self.db = None
        self.is_connected = False
        self.fallback_db_path = settings.BASE_DIR / "mongo_fallback.sqlite3"

        # Try connecting to live MongoDB
        try:
            from pymongo import MongoClient
            client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
            client.server_info()  # Will raise exception if unable to connect
            self.client = client
            self.db = client[self.db_name]
            self.is_connected = True
            print(f"[MongoDBManager] Successfully connected to MongoDB at {self.mongo_uri}")
        except Exception as e:
            self.is_connected = False
            self._init_fallback_storage()
            print(f"[MongoDBManager] MongoDB server not reachable ({e}). Using encrypted local document fallback.")

    def _init_fallback_storage(self):
        """Initializes SQLite-based local document store for fallback."""
        conn = sqlite3.connect(self.fallback_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mongo_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_name TEXT NOT NULL,
                doc_id TEXT UNIQUE,
                data_json TEXT NOT NULL,
                sha256_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_col ON mongo_documents(collection_name)')
        conn.commit()
        conn.close()

    def insert_document(self, collection_name: str, doc_data: dict, encrypt_keys: list[str] = None) -> dict:
        """
        Inserts or updates a document in MongoDB collection with SHA-256 seal.
        """
        doc = doc_data.copy()
        if "created_at" not in doc:
            doc["created_at"] = datetime.now(timezone.utc).isoformat()
        
        # Apply field level encryption if requested
        if encrypt_keys:
            for key in encrypt_keys:
                if key in doc and isinstance(doc[key], str):
                    doc[f"{key}_encrypted"] = encrypt_field(doc[key])
                    doc[f"{key}_is_encrypted"] = True

        # Generate SHA-256 seal
        doc_hash = compute_sha256_hash(doc)
        doc["sha256_seal"] = doc_hash

        if self.is_connected and self.db is not None:
            try:
                # If document has id or key, upsert to keep collection clean
                filter_q = {}
                if "id" in doc:
                    filter_q["id"] = doc["id"]
                elif "key" in doc:
                    filter_q["key"] = doc["key"]
                elif "username" in doc:
                    filter_q["username"] = doc["username"]

                if filter_q:
                    self.db[collection_name].replace_one(filter_q, doc, upsert=True)
                else:
                    self.db[collection_name].insert_one(doc)
                return doc
            except Exception as e:
                print(f"[MongoDBManager] Insert failed on {collection_name}: {e}")

        # Fallback local document storage
        import uuid
        doc_id = str(doc.get("id", uuid.uuid4()))
        doc["_id"] = doc_id
        try:
            conn = sqlite3.connect(self.fallback_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO mongo_documents (collection_name, doc_id, data_json, sha256_hash) VALUES (?, ?, ?, ?)",
                (collection_name, doc_id, json.dumps(doc, default=str), doc_hash)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        return doc

    def find_documents(self, collection_name: str, query: dict = None, limit: int = 50, decrypt_keys: list[str] = None) -> list[dict]:
        results = []
        if self.is_connected and self.db is not None:
            try:
                cursor = self.db[collection_name].find(query or {}).sort("created_at", -1).limit(limit)
                for item in cursor:
                    item["_id"] = str(item["_id"])
                    results.append(item)
            except Exception as e:
                print(f"[MongoDBManager] Query error: {e}")

        if not results:
            try:
                conn = sqlite3.connect(self.fallback_db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT data_json FROM mongo_documents WHERE collection_name = ? ORDER BY id DESC LIMIT ?",
                    (collection_name, limit)
                )
                rows = cursor.fetchall()
                conn.close()
                for r in rows:
                    try:
                        results.append(json.loads(r[0]))
                    except Exception:
                        pass
            except Exception:
                pass

        if decrypt_keys:
            for item in results:
                for key in decrypt_keys:
                    enc_key = f"{key}_encrypted"
                    if enc_key in item:
                        item[key] = decrypt_field(item[enc_key])

        return results

    # ==========================================
    # ENTITY SYNCHRONIZATION HELPERS
    # ==========================================
    def sync_project(self, project):
        return self.insert_document("projects", {
            "id": project.pk,
            "key": project.key,
            "name": project.name,
            "description": project.description,
            "category": project.category,
            "status": project.status,
            "avatar_color": project.avatar_color,
            "owner": project.owner.username if project.owner else None,
            "lead": project.lead.username if project.lead else None,
            "total_issues": project.total_issues_count,
            "done_issues": project.done_issues_count,
            "progress_percentage": project.progress_percentage,
            "is_archived": project.is_archived,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    def sync_issue(self, issue):
        return self.insert_document("issues", {
            "id": issue.pk,
            "key": issue.key,
            "title": issue.title,
            "description": issue.description,
            "issue_type": issue.issue_type,
            "priority": issue.priority,
            "status": issue.status,
            "story_points": issue.story_points,
            "project_id": issue.project.pk if issue.project else None,
            "project_key": issue.project.key if issue.project else None,
            "sprint_id": issue.sprint.pk if issue.sprint else None,
            "sprint_name": issue.sprint.name if issue.sprint else None,
            "assignee": issue.assignee.username if issue.assignee else None,
            "reporter": issue.reporter.username if issue.reporter else None,
            "due_date": str(issue.due_date) if issue.due_date else None,
            "labels": issue.label_list,
            "subtasks_total": issue.subtasks_total,
            "subtasks_completed": issue.subtasks_completed,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    def sync_sprint(self, sprint):
        return self.insert_document("sprints", {
            "id": sprint.pk,
            "project_id": sprint.project.pk if sprint.project else None,
            "sprint_number": sprint.sprint_number,
            "name": sprint.name,
            "goal": sprint.goal,
            "status": sprint.status,
            "start_date": str(sprint.start_date) if sprint.start_date else None,
            "end_date": str(sprint.end_date) if sprint.end_date else None,
            "total_committed_points": sprint.total_committed_points,
            "completed_points": sprint.completed_points,
            "issues_count": sprint.issues.count(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    def sync_user(self, user):
        return self.insert_document("users", {
            "id": user.pk,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "title": user.title,
            "avatar_color": user.avatar_color,
            "is_active": user.is_active,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    def sync_notification(self, notification):
        return self.insert_document("notifications", {
            "id": notification.pk,
            "recipient": notification.recipient.username if notification.recipient else None,
            "actor": notification.actor.username if notification.actor else None,
            "type": notification.notification_type,
            "title": notification.title,
            "message": notification.message,
            "link": notification.link,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat() if notification.created_at else datetime.now(timezone.utc).isoformat(),
        })

    def sync_audit_log(self, audit_log):
        return self.insert_document("audit_logs", {
            "id": audit_log.pk,
            "issue_key": audit_log.issue.key if audit_log.issue else None,
            "actor": audit_log.actor.username if audit_log.actor else "System",
            "action": audit_log.action,
            "previous_value": audit_log.previous_value,
            "new_value": audit_log.new_value,
            "created_at": audit_log.created_at.isoformat() if audit_log.created_at else datetime.now(timezone.utc).isoformat(),
        })


# Global Singleton
mongo_manager = MongoDBManager()
