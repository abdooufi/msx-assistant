# MSX Smart Assistant

AI-powered customer support assistant for [MSX.om](https://www.msx.om)

**Stack:** React + Python FastAPI + PostgreSQL + LocalAI

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11
- Node.js 18+
- PostgreSQL running on port 5432
- LocalAI running on port 8080

### 1. Backend Setup

```powershell
cd backend

# Create and activate venv
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env file
copy .env.example .env
# Edit .env with your settings

# Seed database
python seed.py

# Start backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 2. Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

### 3. Access

| Page | URL |
|---|---|
| Chat | http://localhost:5173 |
| Admin | http://localhost:5173/admin |
| API Docs | http://localhost:8001/docs |

Admin login: `admin` / `changeme123`

---

## ⚙️ Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://postgres:root@localhost:5432/Chatboot
LOCALAI_BASE_URL=http://localhost:8080/v1
LOCALAI_MODEL=meta-llama-3.1-8b-instruct:grammar-functioncall
LOCALAI_TIMEOUT=60
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

---

## 📁 Project Structure

```
msx-assistant/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings from .env
│   ├── database.py          # PostgreSQL connection
│   ├── models.py            # SQLAlchemy + Pydantic models
│   ├── auth.py              # JWT authentication
│   ├── seed.py              # Sample data seeder
│   ├── routes/
│   │   ├── chat.py          # Chat endpoint
│   │   ├── faq.py           # FAQ CRUD
│   │   ├── knowledge.py     # Knowledge base CRUD
│   │   ├── admin.py         # Dashboard stats
│   │   ├── unanswered.py    # Unanswered questions
│   │   └── auth.py          # Login endpoint
│   └── services/
│       ├── localai.py       # LocalAI API integration
│       └── retrieval.py     # Knowledge search
└── frontend/
    └── src/
        ├── pages/
        │   ├── ChatPage.jsx         # Customer chat UI
        │   ├── AdminLogin.jsx       # Admin login
        │   ├── AdminLayout.jsx      # Admin sidebar
        │   ├── Dashboard.jsx        # Stats dashboard
        │   ├── FAQManager.jsx       # Manage FAQs
        │   ├── KnowledgeManager.jsx # Manage KB articles
        │   └── UnansweredPage.jsx   # Review unanswered
        ├── api/index.js             # API client
        └── context/AuthContext.jsx  # Auth state
```
