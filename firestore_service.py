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
                try:
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred, {
                        'projectId': 'giadienweb'  # Sử dụng project ID của dự án
                    })
                    print("✅ Firebase Admin đã khởi tạo với service account key (project: giadienweb)")
                except AttributeError as attr_error:
                    # Xử lý lỗi DEFAULT_UNIVERSE_DOMAIN
                    if "DEFAULT_UNIVERSE_DOMAIN" in str(attr_error):
                        print("⚠️ Gặp lỗi version compatibility, thử cách khác...")
                        # Thử với monkey patch để fix lỗi
                        try:
                            import google.auth.credentials
                            if not hasattr(google.auth.credentials, 'DEFAULT_UNIVERSE_DOMAIN'):
                                google.auth.credentials.DEFAULT_UNIVERSE_DOMAIN = 'googleapis.com'
                        except:
                            pass
                        # Thử lại
                        cred = credentials.Certificate(service_account_path)
                        firebase_admin.initialize_app(cred, {
                            'projectId': 'giadienweb'
                        })
                        print("✅ Firebase Admin đã khởi tạo với service account key (project: giadienweb) - sau khi fix compatibility")
                    else:
                        raise
            else:
                # Sử dụng default credentials với project ID cụ thể
                try:
                    firebase_admin.initialize_app(options={
                        'projectId': 'giadienweb'  # Sử dụng project ID của dự án
                    })
                    print("✅ Firebase Admin đã khởi tạo với default credentials (project: giadienweb)")
                except AttributeError as attr_error:
                    # Xử lý lỗi DEFAULT_UNIVERSE_DOMAIN
                    if "DEFAULT_UNIVERSE_DOMAIN" in str(attr_error):
                        print("⚠️ Gặp lỗi version compatibility, thử cách khác...")
                        try:
                            import google.auth.credentials
                            if not hasattr(google.auth.credentials, 'DEFAULT_UNIVERSE_DOMAIN'):
                                google.auth.credentials.DEFAULT_UNIVERSE_DOMAIN = 'googleapis.com'
                        except:
                            pass
                        firebase_admin.initialize_app(options={
                            'projectId': 'giadienweb'
                        })
                        print("✅ Firebase Admin đã khởi tạo với default credentials (project: giadienweb) - sau khi fix compatibility")
                    else:
                        raise
                except Exception as default_error:
                    # Nếu không có default credentials, thử không chỉ định project
                    try:
                        firebase_admin.initialize_app()
                        print("✅ Firebase Admin đã khởi tạo (sử dụng default project)")
                    except AttributeError as attr_error:
                        if "DEFAULT_UNIVERSE_DOMAIN" in str(attr_error):
                            print("⚠️ Gặp lỗi version compatibility, thử cách khác...")
                            try:
                                import google.auth.credentials
                                if not hasattr(google.auth.credentials, 'DEFAULT_UNIVERSE_DOMAIN'):
                                    google.auth.credentials.DEFAULT_UNIVERSE_DOMAIN = 'googleapis.com'
                            except:
                                pass
                            firebase_admin.initialize_app()
                            print("✅ Firebase Admin đã khởi tạo (sử dụng default project) - sau khi fix compatibility")
                        else:
                            raise
        
        _db = firestore.client()
        print("✅ Firestore client đã sẵn sàng (project: giadienweb)")
        return _db
        
    except Exception as e:
        error_msg = str(e)
        if "DEFAULT_UNIVERSE_DOMAIN" in error_msg:
            print(f"⚠️ Lỗi version compatibility với google-auth: {error_msg}")
            print("   💡 Thử chạy: pip install --upgrade google-auth google-auth-httplib2")
        else:
            print(f"⚠️ Không thể khởi tạo Firestore: {e}")
        print("   Hệ thống vẫn hoạt động nhưng không lưu vào Firestore")
        print("   💡 Gợi ý: Tạo service account key từ Firebase Console và đặt tên 'serviceAccountKey.json'")
        import traceback
        traceback.print_exc()
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
        
        print(f"💾 Đã lưu message vào Firestore: {message_id[:8]}...")
        return message_id
        
    except Exception as e:
        print(f"❌ Lỗi khi lưu message vào Firestore: {e}")
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
            print(f"💾 Đã cập nhật session trong Firestore: {session_id[:8]}...")
        else:
            # Tạo session mới
            session_data["createdAt"] = firestore.SERVER_TIMESTAMP
            doc_ref = sessions_ref.add(session_data)
            print(f"💾 Đã tạo session mới trong Firestore: {session_id[:8]}...")
        
        return session_id
        
    except Exception as e:
        print(f"❌ Lỗi khi lưu session vào Firestore: {e}")
        return None


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
        
        print(f"💾 Đã lưu medicine reminder vào Firestore: {reminder_id[:8]}...")
        return reminder_id
        
    except Exception as e:
        print(f"❌ Lỗi khi lưu medicine reminder vào Firestore: {e}")
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
        
    except Exception as e:
        print(f"❌ Lỗi khi lấy medicine reminders từ Firestore: {e}")
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
    except Exception as e:
        print(f"❌ Lỗi khi lấy health profile: {e}")
        import traceback
        traceback.print_exc()
        return None

def delete_medicine_reminder(reminder_id: str) -> bool:
    """Xóa hoặc deactivate medicine reminder"""
    try:
        db = get_db()
        if db is None:
            return False
        
        doc_ref = db.collection("medicineReminders").document(reminder_id)
        doc_ref.update({"isActive": False})
        
        print(f"💾 Đã xóa medicine reminder trong Firestore: {reminder_id[:8]}...")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi xóa medicine reminder từ Firestore: {e}")
        return False

