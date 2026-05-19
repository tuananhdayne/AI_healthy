"""
Firestore service để lưu conversations và medicine reminders
"""
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Global Firestore client
_db: Optional[firestore.Client] = None


def initialize_firestore():
    """Khởi tạo Firestore client với project giadienweb"""
    global _db
    
    if _db is not None:
        return _db
    
    try:
        # Kiểm tra xem đã initialize chưa
        if not firebase_admin._apps:
            # Tìm service account key file
            service_account_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")
            if not service_account_path:
                # Thử các đường dẫn mặc định
                possible_paths = [
                    "serviceAccountKey.json",
                    "firebase-service-account.json",
                    os.path.join(os.path.dirname(__file__), "serviceAccountKey.json"),
                    os.path.join(os.path.dirname(__file__), "AI-Web", "serviceAccountKey.json"),
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        service_account_path = path
                        break

            if service_account_path and os.path.exists(service_account_path):
                print(f"[firestore] Using service account: {service_account_path}")
                try:
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred, {
                        'projectId': 'giadienweb'
                    })
                except AttributeError as attr_error:
                    # Xử lý lỗi DEFAULT_UNIVERSE_DOMAIN
                    if "DEFAULT_UNIVERSE_DOMAIN" in str(attr_error):
                        try:
                            import google.auth.credentials
                            if not hasattr(google.auth.credentials, 'DEFAULT_UNIVERSE_DOMAIN'):
                                google.auth.credentials.DEFAULT_UNIVERSE_DOMAIN = 'googleapis.com'
                        except:
                            pass
                        cred = credentials.Certificate(service_account_path)
                        firebase_admin.initialize_app(cred, {
                            'projectId': 'giadienweb'
                        })
                    else:
                        raise
            else:
                print("[firestore] No service account file found, trying default credentials")
                # Sử dụng default credentials với project ID cụ thể
                try:
                    firebase_admin.initialize_app(options={
                        'projectId': 'giadienweb'
                    })
                except AttributeError as attr_error:
                    if "DEFAULT_UNIVERSE_DOMAIN" in str(attr_error):
                        try:
                            import google.auth.credentials
                            if not hasattr(google.auth.credentials, 'DEFAULT_UNIVERSE_DOMAIN'):
                                google.auth.credentials.DEFAULT_UNIVERSE_DOMAIN = 'googleapis.com'
                        except:
                            pass
                        firebase_admin.initialize_app(options={
                            'projectId': 'giadienweb'
                        })
                    else:
                        raise
                except Exception:
                    # Nếu không có default credentials, thử không chỉ định project
                    try:
                        firebase_admin.initialize_app()
                    except AttributeError as attr_error:
                        if "DEFAULT_UNIVERSE_DOMAIN" in str(attr_error):
                            try:
                                import google.auth.credentials
                                if not hasattr(google.auth.credentials, 'DEFAULT_UNIVERSE_DOMAIN'):
                                    google.auth.credentials.DEFAULT_UNIVERSE_DOMAIN = 'googleapis.com'
                            except:
                                pass
                            firebase_admin.initialize_app()
                        else:
                            raise
        
        _db = firestore.client()
        print(f"[firestore] Client initialized. Project: {_db.project}")
        return _db
        
    except Exception as e:
        print(f"[firestore] Failed to initialize: {e}")
        # Frontend đã lưu trực tiếp, backend không cần Firestore
        return None


def get_db() -> Optional[firestore.Client]:
    """Lấy Firestore client"""
    if _db is None:
        return initialize_firestore()
    return _db


# ============================
# CONVERSATION OPERATIONS
# ============================

def save_chat_message(
    user_id: str,
    user_email: str,
    session_id: str,
    message_text: str,
    role: str,  # 'user' or 'assistant'
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Lưu một message vào Firestore
    
    Returns:
        Message ID nếu thành công, None nếu lỗi
    """
    try:
        db = get_db()
        if db is None:
            return None
        
        message_data = {
            "userId": user_id,
            "userEmail": user_email,
            "sessionId": session_id,
            "text": message_text,
            "role": role,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }
        
        if role == "assistant":
            message_data["aiResponse"] = message_text
        
        if metadata:
            message_data["metadata"] = metadata
        
        doc_ref = db.collection("messages").add(message_data)
        message_id = doc_ref[1].id
        return message_id
        
    except Exception:
        return None


def save_chat_session(
    user_id: str,
    user_email: str,
    session_id: str,
    title: Optional[str] = None
) -> Optional[str]:
    """
    Lưu hoặc cập nhật chat session vào Firestore
    
    Returns:
        Session ID nếu thành công, None nếu lỗi
    """
    try:
        db = get_db()
        if db is None:
            return None
        
        # Kiểm tra xem session đã tồn tại chưa
        sessions_ref = db.collection("chatSessions")
        query = sessions_ref.where("sessionId", "==", session_id).where("userId", "==", user_id).limit(1)
        docs = query.get()
        
        session_data = {
            "userId": user_id,
            "userEmail": user_email,
            "sessionId": session_id,
            "title": title or f"Chat session {session_id[:8]}",
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
        
        if docs:
            # Cập nhật session hiện có
            doc_ref = docs[0].reference
            doc_ref.update(session_data)
        else:
            # Tạo session mới
            session_data["createdAt"] = firestore.SERVER_TIMESTAMP
            sessions_ref.add(session_data)
        
        return session_id
        
    except Exception:
        return None


def load_chat_history(user_id: Optional[str], session_id: str, limit: int = 2) -> List[tuple]:
    """Đọc lịch sử chat (user/assistant) từ Firestore và trả về các cặp (user, bot).

    - Lọc theo sessionId (và userId nếu có)
    - Sắp xếp theo timestamp tăng dần
    - Ghép cặp theo role: ưu tiên user → assistant; nếu thiếu user thì vẫn giữ assistant
    - Trả về tối đa `limit` cặp gần nhất
    """
    try:
        db = get_db()
        if db is None:
            print("[firestore] No DB client. Cannot load history.")
            return []

        messages_ref = db.collection("messages")
        # Bắt buộc theo sessionId; userId là tùy chọn để tăng chính xác nếu front gửi kèm
        query_obj = messages_ref.where("sessionId", "==", session_id)
        if user_id:
            query_obj = query_obj.where("userId", "==", user_id)

        # Không order_by trên Firestore (giống frontend): lấy tất cả, sau đó sort trong Python
        docs = list(query_obj.stream())
        print(f"[firestore] Loaded {len(docs)} raw docs for session={session_id} user_id={user_id}")
        if docs:
            sample = []
            for d in docs[:5]:
                data = d.to_dict() or {}
                sample.append({
                    "role": data.get("role"),
                    "text": (data.get("text") or "")[:60],
                    "aiResponse": (data.get("aiResponse") or "")[:60],
                    "timestamp": str(data.get("timestamp")),
                })
            print(f"[firestore] Sample docs: {sample}")
        history: List[tuple] = []
        pending_users: List[str] = []

        # Sort docs giống frontend: theo timestamp tăng dần (nếu thiếu timestamp thì giữ nguyên thứ tự Firestore)
        def _get_ts(doc):
            data = doc.to_dict() or {}
            ts = data.get("timestamp")
            try:
                return ts.to_datetime() if hasattr(ts, "to_datetime") else ts
            except Exception:
                return ts

        docs = sorted(docs, key=lambda d: (_get_ts(d) or 0))

        for doc in docs:
            data = doc.to_dict() or {}
            role = data.get("role")
            # Suy luận role nếu thiếu giống frontend: nếu có aiResponse thì assistant, ngược lại user
            if not role:
                role = "assistant" if data.get("aiResponse") else "user"

            # Frontend lưu aiResponse cho assistant, text cho user; ưu tiên text rồi aiResponse
            text = data.get("text") or data.get("aiResponse")
            if not text:
                continue

            if role == "user":
                pending_users.append(text)
            elif role == "assistant":
                user_text = pending_users.pop(0) if pending_users else None
                history.append((user_text, text))
            else:
                continue

        # chỉ giữ tối đa `limit` cặp gần nhất
        if len(history) > limit:
              history = history[-limit:]
        return history

    except Exception:
        return []


# ============================
# MEDICINE REMINDER OPERATIONS
# ============================

def save_medicine_reminder(reminder_data: Dict[str, Any]) -> Optional[str]:
    """
    Lưu medicine reminder vào Firestore
    
    Returns:
        Reminder ID nếu thành công, None nếu lỗi
    """
    try:
        db = get_db()
        if db is None:
            return None
        
        # Chuyển đổi datetime sang Firestore Timestamp
        firestore_data = reminder_data.copy()
        if "created_at" in firestore_data and isinstance(firestore_data["created_at"], str):
            firestore_data["createdAt"] = firestore.SERVER_TIMESTAMP
            del firestore_data["created_at"]
        else:
            firestore_data["createdAt"] = firestore.SERVER_TIMESTAMP
        
        if "next_reminder_time" in firestore_data and isinstance(firestore_data["next_reminder_time"], str):
            try:
                dt = datetime.fromisoformat(firestore_data["next_reminder_time"])
                firestore_data["nextReminderTime"] = firestore.Timestamp.from_datetime(dt)
            except:
                pass
            del firestore_data["next_reminder_time"]
        
        if "last_sent" in firestore_data and firestore_data["last_sent"]:
            try:
                if isinstance(firestore_data["last_sent"], str):
                    dt = datetime.fromisoformat(firestore_data["last_sent"])
                    firestore_data["lastSent"] = firestore.Timestamp.from_datetime(dt)
                else:
                    firestore_data["lastSent"] = firestore.SERVER_TIMESTAMP
            except:
                pass
            del firestore_data["last_sent"]
        
        # Đổi tên các field sang camelCase
        field_mapping = {
            "user_id": "userId",
            "user_email": "userEmail",
            "medicine_name": "medicineName",
            "repeat_type": "repeatType",
            "start_date": "startDate",
            "end_date": "endDate",
            "is_active": "isActive",
        }
        
        for old_key, new_key in field_mapping.items():
            if old_key in firestore_data:
                firestore_data[new_key] = firestore_data.pop(old_key)
        
        # Nếu có id, cập nhật document đó, nếu không thì tạo mới
        if "id" in firestore_data:
            reminder_id = firestore_data.pop("id")
            doc_ref = db.collection("medicineReminders").document(reminder_id)
            doc_ref.set(firestore_data, merge=True)
        else:
            doc_ref = db.collection("medicineReminders").add(firestore_data)
            reminder_id = doc_ref[1].id
        
        return reminder_id
        
    except Exception:
        return None


def get_medicine_reminders(user_id: str) -> List[Dict[str, Any]]:
    """Lấy danh sách medicine reminders của user"""
    try:
        db = get_db()
        if db is None:
            return []
        
        reminders_ref = db.collection("medicineReminders")
        query = reminders_ref.where("userId", "==", user_id).where("isActive", "==", True)
        docs = query.stream()
        
        reminders = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            reminders.append(data)
        
        return reminders
        
    except Exception:
        return []


def get_health_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Lấy health profile của user từ Firestore
    Path: users/{user_id}/healthProfile/profile
    """
    try:
        db = get_db()
        if db is None:
            return None
        
        doc_ref = db.collection('users').document(user_id).collection('healthProfile').document('profile')
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            return {
                'tuoi': data.get('tuoi'),
                'chieuCao': data.get('chieuCao'),
                'canNang': data.get('canNang'),
                'mucVanDong': data.get('mucVanDong'),
                'gioiTinh': data.get('gioiTinh', 'khac')
            }
        return None
    except Exception:
        return None

def delete_medicine_reminder(reminder_id: str) -> bool:
    """Xóa hoặc deactivate medicine reminder"""
    try:
        db = get_db()
        if db is None:
            return False
        
        doc_ref = db.collection("medicineReminders").document(reminder_id)
        doc_ref.update({"isActive": False})
        return True
        
    except Exception:
        return False

