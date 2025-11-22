"""
FastAPI server để đưa chatbot Python lên web.
Chạy: uvicorn api_server:app --reload --port 8000
"""

import os
import sys
import uuid
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ============================
# BIẾN TRẠNG THÁI MODELS
# ============================
_models_ready = False
_models_loading = False
_models_error: Optional[str] = None
_reset_conversation = None
_run_chat_pipeline = None


def _parse_allowed_origins(value: Optional[str]) -> List[str]:
    if not value:
        return ["*"]
    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    return origins or ["*"]


app = FastAPI(
    title="HealthyAI Chatbot API",
    version="1.0.0",
    description="REST API cho chatbot y tế (Intent + RAG + Gemini)."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(os.environ.get("ALLOWED_ORIGINS")),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================
# LOAD MODELS KHI SERVER KHỞI ĐỘNG
# ============================
@app.on_event("startup")
async def load_models():
    """Load tất cả models khi server khởi động - từng bước để tránh quá tải"""
    global _models_ready, _models_loading, _models_error
    global _reset_conversation, _run_chat_pipeline
    
    if _models_ready:
        return
    
    _models_loading = True
    _models_error = None
    
    print("\n" + "="*60)
    print("🚀 ĐANG KHỞI ĐỘNG SERVER VÀ LOAD MODELS...")
    print("="*60 + "\n")
    
    start_time = time.time()
    step_times = {}
    
    try:
        # Bước 1: Import các module cơ bản (không load models)
        print("[1/5] Đang import các module cơ bản...")
        step_start = time.time()
        from app.response_layer import need_more_info, build_clarification_question
        from app.symptom_extractor import extract_symptoms
        from app.risk_estimator import estimate_risk
        step_times["import_modules"] = time.time() - step_start
        print(f"      ✅ Hoàn thành ({step_times['import_modules']:.2f}s)\n")
        
        # Bước 2: Load Intent Classifier (PhoBERT) - thường nhẹ nhất
        print("[2/5] Đang load Intent Classifier (PhoBERT)...")
        print("      ⏳ Có thể mất 30-60 giây...")
        step_start = time.time()
        try:
            from intent.intent_classifier import IntentClassifier
            intent_model_path = r"D:\CHAT BOT TTCS\model\phobert_intent_model_v5"
            intent_classifier = IntentClassifier(intent_model_path)
            step_times["intent"] = time.time() - step_start
            print(f"      ✅ Intent Classifier đã load ({step_times['intent']:.2f}s)\n")
        except Exception as e:
            raise Exception(f"Lỗi khi load Intent Classifier: {str(e)}")
        
        # Bước 3: Load RAG Retriever (FAISS + SentenceTransformer)
        print("[3/5] Đang load RAG Retriever (FAISS + SentenceTransformer)...")
        print("      ⏳ Có thể mất 1-2 phút...")
        step_start = time.time()
        try:
            from rag.retriever import Retriever
            rag_path = r"D:\CHAT BOT TTCS\rag"
            retriever = Retriever(rag_path)
            step_times["rag"] = time.time() - step_start
            print(f"      ✅ RAG Retriever đã load ({step_times['rag']:.2f}s)\n")
        except Exception as e:
            raise Exception(f"Lỗi khi load RAG Retriever: {str(e)}")
        
        # Bước 4: Kiểm tra Gemini API (không cần load model)
        print("[4/5] Đang kiểm tra Gemini API...")
        print("      ⚡ Sử dụng Gemini API - nhanh và không cần load model nặng")
        step_start = time.time()
        try:
            from generator.gemini_generator import _get_model
            model = _get_model()  # Test connection
            step_times["gemini"] = time.time() - step_start
            print(f"      ✅ Gemini API đã sẵn sàng ({step_times['gemini']:.2f}s)\n")
        except Exception as e:
            print(f"      ⚠️  Cảnh báo: {str(e)}")
            print("      Hệ thống vẫn sẽ hoạt động nhưng có thể gặp lỗi khi generate")
            step_times["gemini"] = time.time() - step_start
            print(f"      ⏱️  Thời gian: {step_times['gemini']:.2f}s\n")
        
        # Bước 5: Gán models vào chatbot module và test
        print("[5/5] Đang khởi tạo chatbot pipeline và kiểm tra...")
        step_start = time.time()
        try:
            # Import chatbot module
            import chatbot
            
            # Gán models đã load vào chatbot module (tránh load lại)
            chatbot.intent_classifier = intent_classifier
            chatbot.retriever = retriever
            chatbot._models_initialized = True
            
            # Import functions
            from chatbot import reset_conversation, run_chat_pipeline
            _reset_conversation = reset_conversation
            _run_chat_pipeline = run_chat_pipeline
            
            # Test với câu đơn giản
            print("      ⏳ Đang test pipeline...")
            test_response = run_chat_pipeline("xin chào", session_id="startup_test")
            step_times["pipeline"] = time.time() - step_start
            print(f"      ✅ Pipeline hoạt động tốt ({step_times['pipeline']:.2f}s)\n")
        except Exception as e:
            raise Exception(f"Lỗi khi khởi tạo pipeline: {str(e)}")
        
        elapsed = time.time() - start_time
        
        _models_ready = True
        _models_loading = False
        
        print("\n" + "="*60)
        print("✅ TẤT CẢ MODELS ĐÃ SẴN SÀNG!")
        print(f"⏱️  Tổng thời gian: {elapsed:.2f} giây ({elapsed/60:.1f} phút)")
        print("\n📊 Chi tiết:")
        for step, duration in step_times.items():
            print(f"   - {step}: {duration:.2f}s")
        print("="*60 + "\n")
        
    except MemoryError as e:
        _models_loading = False
        _models_ready = False
        _models_error = f"Không đủ RAM: {str(e)}"
        
        elapsed = time.time() - start_time
        
        print("\n" + "="*60)
        print("❌ LỖI: KHÔNG ĐỦ BỘ NHỚ!")
        print(f"   {_models_error}")
        print(f"⏱️  Thời gian trước khi lỗi: {elapsed:.2f} giây")
        print("\n💡 Gợi ý:")
        print("   - Đóng các ứng dụng khác để giải phóng RAM")
        print("   - Sử dụng GPU nếu có")
        print("   - Giảm batch size hoặc sử dụng model nhẹ hơn")
        print("="*60 + "\n")
        
        import traceback
        traceback.print_exc()
        
    except Exception as e:
        _models_loading = False
        _models_ready = False
        _models_error = str(e)
        
        elapsed = time.time() - start_time
        
        print("\n" + "="*60)
        print("❌ LỖI KHI LOAD MODELS!")
        print(f"   Chi tiết: {_models_error}")
        print(f"⏱️  Thời gian trước khi lỗi: {elapsed:.2f} giây")
        print("="*60 + "\n")
        
        import traceback
        traceback.print_exc()


# ============================
# REQUEST/RESPONSE MODELS
# ============================
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: Optional[str]
    intent_confidence: float
    symptoms: Dict[str, Any]
    risk: Optional[str]
    clarification_needed: bool
    clarification_question: Optional[str]
    sources: List[Dict[str, Any]]
    stage: str


class ResetRequest(BaseModel):
    session_id: str


# ============================
# MEDICINE REMINDER MODELS
# ============================
class MedicineReminderRequest(BaseModel):
    user_id: str
    user_email: str
    medicine_name: str
    time: str  # Format: "HH:MM" hoặc "HH:MM:SS"
    repeat_type: str  # "daily", "weekly", "once"
    weekday: Optional[int] = None  # 0-6 cho weekly (0=Monday)
    start_date: Optional[str] = None  # ISO format
    end_date: Optional[str] = None  # ISO format
    notes: Optional[str] = None


class MedicineReminderResponse(BaseModel):
    id: str
    user_id: str
    medicine_name: str
    time: str
    repeat_type: str
    weekday: Optional[int]
    start_date: Optional[str]
    end_date: Optional[str]
    notes: Optional[str]
    created_at: str
    is_active: bool


# ============================
# API ENDPOINTS
# ============================
@app.get("/health")
async def healthcheck():
    return {"status": "ok"}


@app.get("/ready")
async def ready_check():
    """Kiểm tra xem models đã load xong chưa"""
    if _models_ready:
        return {
            "ready": True,
            "status": "Models đã sẵn sàng",
            "error": None
        }
    elif _models_loading:
        return {
            "ready": False,
            "status": "Models đang tải, vui lòng đợi...",
            "error": None
        }
    else:
        return {
            "ready": False,
            "status": "Models chưa sẵn sàng",
            "error": _models_error or "Chưa khởi động"
        }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    if not _models_ready:
        if _models_loading:
            raise HTTPException(
                status_code=503,
                detail="Models đang tải, vui lòng đợi thêm vài phút và thử lại."
            )
        else:
            error_msg = _models_error or "Models chưa được load"
            raise HTTPException(
                status_code=503,
                detail=f"Models chưa sẵn sàng: {error_msg}"
            )
    
    if not _run_chat_pipeline:
        raise HTTPException(
            status_code=503,
            detail="Chat pipeline chưa được khởi tạo"
        )
    
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    try:
        session_id = payload.session_id or str(uuid.uuid4())
        response = _run_chat_pipeline(payload.message, session_id=session_id)
        response["session_id"] = session_id
        return response
    except Exception as e:
        print(f"❌ Lỗi khi xử lý chat: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xử lý: {str(e)}"
        )


@app.post("/api/chat/reset")
async def reset(payload: ResetRequest):
    if not _reset_conversation:
        raise HTTPException(
            status_code=503,
            detail="Models chưa sẵn sàng"
        )
    _reset_conversation(payload.session_id)
    return {"session_id": payload.session_id, "status": "reset"}


# ============================
# MEDICINE REMINDER ENDPOINTS
# ============================
@app.post("/api/medicine-reminders", response_model=MedicineReminderResponse)
async def create_reminder(reminder: MedicineReminderRequest):
    """Tạo lịch nhắc nhở uống thuốc mới"""
    try:
        # Parse time
        time_parts = reminder.time.split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        
        # Tạo reminder ID
        reminder_id = str(uuid.uuid4())
        
        # Tính toán next reminder time
        now = datetime.now()
        reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Nếu thời gian đã qua trong ngày hôm nay, set cho ngày mai
        if reminder_time < now:
            reminder_time += timedelta(days=1)
        
        reminder_data = {
            "id": reminder_id,
            "user_id": reminder.user_id,
            "user_email": reminder.user_email,
            "medicine_name": reminder.medicine_name,
            "time": reminder.time,
            "repeat_type": reminder.repeat_type,
            "weekday": reminder.weekday,
            "start_date": reminder.start_date,
            "end_date": reminder.end_date,
            "notes": reminder.notes,
            "created_at": datetime.now().isoformat(),
            "is_active": True,
            "next_reminder_time": reminder_time.isoformat(),
            "last_sent": None
        }
        
        # TODO: Lưu vào database (Firestore hoặc SQL)
        # Tạm thời lưu vào memory (sẽ mất khi restart server)
        if not hasattr(app.state, 'medicine_reminders'):
            app.state.medicine_reminders = {}
        app.state.medicine_reminders[reminder_id] = reminder_data
        
        return MedicineReminderResponse(**reminder_data)
        
    except Exception as e:
        print(f"❌ Lỗi khi tạo reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/medicine-reminders/{user_id}", response_model=List[MedicineReminderResponse])
async def get_reminders(user_id: str):
    """Lấy danh sách lịch nhắc nhở của user"""
    try:
        if not hasattr(app.state, 'medicine_reminders'):
            return []
        
        user_reminders = [
            MedicineReminderResponse(**r)
            for r in app.state.medicine_reminders.values()
            if r["user_id"] == user_id and r.get("is_active", True)
        ]
        
        return user_reminders
    except Exception as e:
        print(f"❌ Lỗi khi lấy reminders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/medicine-reminders/{reminder_id}")
async def delete_reminder(reminder_id: str):
    """Xóa lịch nhắc nhở"""
    try:
        if hasattr(app.state, 'medicine_reminders'):
            if reminder_id in app.state.medicine_reminders:
                app.state.medicine_reminders[reminder_id]["is_active"] = False
                return {"status": "deleted", "id": reminder_id}
        raise HTTPException(status_code=404, detail="Reminder not found")
    except Exception as e:
        print(f"❌ Lỗi khi xóa reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/medicine-reminders/{reminder_id}/check")
async def check_and_send_reminders():
    """Kiểm tra và gửi thông báo nhắc nhở (gọi định kỳ)"""
    try:
        if not hasattr(app.state, 'medicine_reminders'):
            return {"sent": 0}
        
        now = datetime.now()
        sent_count = 0
        
        for reminder_id, reminder in app.state.medicine_reminders.items():
            if not reminder.get("is_active", True):
                continue
            
            # Parse next reminder time
            next_time_str = reminder.get("next_reminder_time")
            if not next_time_str:
                continue
            
            next_time = datetime.fromisoformat(next_time_str)
            
            # Kiểm tra xem đã đến giờ chưa (trong vòng 5 phút)
            time_diff = (now - next_time).total_seconds()
            if 0 <= time_diff <= 300:  # 5 phút
                # Gửi thông báo
                await send_reminder_notification(reminder)
                
                # Cập nhật next reminder time
                if reminder["repeat_type"] == "daily":
                    next_time += timedelta(days=1)
                elif reminder["repeat_type"] == "weekly":
                    next_time += timedelta(days=7)
                else:  # once
                    reminder["is_active"] = False
                    continue
                
                reminder["next_reminder_time"] = next_time.isoformat()
                reminder["last_sent"] = now.isoformat()
                sent_count += 1
        
        return {"sent": sent_count, "checked_at": now.isoformat()}
        
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra reminders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def send_reminder_notification(reminder: Dict[str, Any]):
    """Gửi thông báo nhắc nhở (web notification hoặc email)"""
    try:
        message = f"🔔 Nhắc nhở: Đã đến giờ uống thuốc {reminder['medicine_name']} ({reminder['time']})"
        if reminder.get('notes'):
            message += f"\nGhi chú: {reminder['notes']}"
        
        print(f"📧 Gửi thông báo đến {reminder['user_email']}: {message}")
        
        # Gửi email qua Firebase Functions
        try:
            import requests
            firebase_function_url = "https://us-central1-giadienweb.cloudfunctions.net/sendMedicineReminder"
            response = requests.post(
                firebase_function_url,
                json={
                    "email": reminder['user_email'],
                    "medicine_name": reminder['medicine_name'],
                    "time": reminder['time'],
                    "message": message
                },
                timeout=10
            )
            if response.status_code == 200:
                print(f"✅ Đã gửi email thành công đến {reminder['user_email']}")
            else:
                print(f"⚠️ Không thể gửi email: {response.status_code}")
        except Exception as email_error:
            print(f"⚠️ Lỗi khi gửi email: {email_error}")
            # Vẫn tiếp tục, không throw error
        
        # TODO: Gửi web push notification nếu user đã enable
        
    except Exception as e:
        print(f"❌ Lỗi khi gửi thông báo: {e}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "0") in {"1", "true", "True"}
    uvicorn.run("api_server:app", host="0.0.0.0", port=port, reload=reload)
