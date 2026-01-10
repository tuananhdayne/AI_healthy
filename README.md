🩺 Vietnamese Health Consultation Chatbot

A Vietnamese health consultation chatbot built with intent classification + Retrieval-Augmented Generation (RAG) to provide safe, guided, and non-diagnostic health advice.
The system focuses on intent routing, ambiguity handling, and controlled response generation rather than direct medical diagnosis.

📌 Key Features

🔍 Intent Classification (PhoBERT)
Classifies user queries into health-related intents (symptoms, nutrition, exercise, stress, others) to route the conversation correctly.

🧠 Top-2 Intent & Ambiguity Handling
Uses top-2 intent probabilities to detect ambiguous queries and trigger clarification (pending) instead of answering prematurely.

🔗 RAG Pipeline (SBERT + FAISS)
Retrieves relevant health knowledge passages before generating responses to reduce hallucination.

🤖 LLM-based Response Generation (Gemini)
Generates natural language responses grounded on retrieved context.

🛡️ Safety-Oriented Design

No diagnosis or prescription

Clarification for unclear inputs

Warning and recommendation to seek medical professionals in risky cases

👤 User Health Profile Management
Stores basic health information to personalize suggestions.

⏰ Medicine Reminder System
Allows users to create and manage medication reminders.

🏗️ System Architecture
User
 ↓
Angular Frontend
 ↓
FastAPI Backend
 ├─ Intent Classification (PhoBERT)
 ├─ Ambiguity & Intent Lock Logic
 ├─ RAG Controller
 │   ├─ SBERT Embedding
 │   ├─ FAISS Vector Search
 │   └─ Knowledge Base
 ├─ Gemini LLM
 └─ Firebase Firestore

🧰 Technologies Used
Backend

Python

FastAPI

Uvicorn

PyTorch

Transformers (Hugging Face)

AI & NLP

PhoBERT – Vietnamese intent classification

Sentence-BERT (SBERT) – Semantic embedding

FAISS – Vector similarity search

RAG (Retrieval-Augmented Generation)

Google Gemini – Large Language Model

Frontend

Angular

TypeScript

Database & Services

Firebase Firestore

Firebase Authentication

🚀 Getting Started
1️⃣ Clone the Repository
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

2️⃣ Backend Setup
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

3️⃣ Frontend Setup
cd frontend
npm install
ng serve

4️⃣ Environment Configuration

Create a .env file for backend:

GEMINI_API_KEY=your_api_key
FIREBASE_CREDENTIALS=path_to_credentials.json

⚠️ Disclaimer

This chatbot does not provide medical diagnosis or treatment.
All responses are for informational and supportive purposes only.
Users should consult qualified healthcare professionals for medical decisions.

📈 Future Improvements

Expand health knowledge base

Improve multi-turn context handling

Optimize model loading and response latency

Add mobile and voice interfaces

Introduce quantitative evaluation metrics

👨‍💻 Authors

Developed as part of an academic project on AI-powered health consultation systems.

📄 License

This project is for educational and research purposes.
