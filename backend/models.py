from sqlalchemy import Column, String, Text, Boolean, DateTime, Float, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from database import Base
from pydantic import BaseModel, field_validator
from typing import Optional, List, Literal
from datetime import datetime
import uuid


class SystemSetting(Base):
    """Key-value store for runtime-configurable settings (e.g. active AI provider)."""
    __tablename__ = "system_settings"
    key        = Column(String(100), primary_key=True)
    value      = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── SQLAlchemy ORM Models (DB Tables) ───────────────────────────

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title      = Column(String(500), nullable=False)
    content    = Column(Text, nullable=False)
    category   = Column(String(100), default="general")
    tags       = Column(JSON, default=list)
    source     = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FAQ(Base):
    __tablename__ = "faqs"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question   = Column(Text, nullable=False)
    answer     = Column(Text, nullable=False)
    category   = Column(String(100), default="general")
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), unique=True, index=True)
    messages   = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UnansweredQuestion(Base):
    __tablename__ = "unanswered_questions"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question       = Column(Text, nullable=False)
    session_id     = Column(String(100))
    classification = Column(String(50), default="general_inquiry")
    status         = Column(String(20), default="pending")
    admin_note     = Column(Text, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Pydantic Schemas (API) ───────────────────────────────────────

class KnowledgeBaseCreate(BaseModel):
    title: str
    content: str
    category: str = "general"
    tags: List[str] = []
    source: Optional[str] = None

class KnowledgeBaseUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None

class KnowledgeBaseDoc(BaseModel):
    id: str
    title: str
    content: str
    category: str
    tags: List[str]
    source: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class FAQCreate(BaseModel):
    question: str
    answer: str
    category: str = "general"
    is_active: bool = True

class FAQUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None

class FAQDoc(BaseModel):
    id: str
    question: str
    answer: str
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: List[ChatMessage] = []

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Message cannot be empty')
        if len(v) > 2000:
            raise ValueError('Message too long (max 2000 characters)')
        return v

    @field_validator('history')
    @classmethod
    def limit_history(cls, v: list) -> list:
        return v[-20:] if len(v) > 20 else v

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    classification: str
    source: Literal["knowledge_base", "faq", "ai_general", "fallback"]
    confidence: float = 1.0
    references: List[str] = []


class UnansweredQuestionSchema(BaseModel):
    id: str
    question: str
    session_id: str
    classification: str
    status: str
    admin_note: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}

class UnansweredUpdate(BaseModel):
    status: Optional[Literal["pending", "reviewed", "answered"]] = None
    admin_note: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminStats(BaseModel):
    total_conversations: int
    total_messages: int
    unanswered_count: int
    faq_count: int
    knowledge_count: int
    classification_breakdown: dict
    top_categories: List[dict]


# ─── Company Table ────────────────────────────────────────────────

class Company(Base):
    __tablename__ = "companies"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol      = Column(String(20), unique=True, index=True, nullable=False)
    name        = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    sector      = Column(String(200), nullable=True)
    website     = Column(String(500), nullable=True)
    founded     = Column(String(50), nullable=True)
    employees   = Column(String(50), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Company Pydantic Schemas ─────────────────────────────────────

class CompanyCreate(BaseModel):
    symbol: str
    name: str
    description: Optional[str] = None
    sector: Optional[str] = None
    website: Optional[str] = None
    founded: Optional[str] = None
    employees: Optional[str] = None

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    website: Optional[str] = None
    founded: Optional[str] = None
    employees: Optional[str] = None

class CompanyDoc(BaseModel):
    id: str
    symbol: str
    name: str
    description: Optional[str]
    sector: Optional[str]
    website: Optional[str]
    founded: Optional[str]
    employees: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ─── Dynamic API Endpoint ─────────────────────────────────────────

class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name         = Column(String(200), nullable=False)
    description  = Column(Text, nullable=True)
    url          = Column(String(1000), nullable=False)
    method       = Column(String(10), default="GET")   # GET or POST
    body         = Column(JSON, nullable=True)          # POST body template
    headers      = Column(JSON, default=dict)           # Extra headers
    keywords_en  = Column(JSON, default=list)           # English trigger keywords
    keywords_ar  = Column(JSON, default=list)           # Arabic trigger keywords
    category     = Column(String(100), default="general")
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── Pydantic schemas ─────────────────────────────────────────────

class ApiEndpointCreate(BaseModel):
    name: str
    description: Optional[str] = None
    url: str
    method: str = "GET"
    body: Optional[dict] = None
    headers: Optional[dict] = None
    keywords_en: List[str] = []
    keywords_ar: List[str] = []
    category: str = "general"
    is_active: bool = True

class ApiEndpointUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    body: Optional[dict] = None
    headers: Optional[dict] = None
    keywords_en: Optional[List[str]] = None
    keywords_ar: Optional[List[str]] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None

class ApiEndpointDoc(BaseModel):
    id: str
    name: str
    description: Optional[str]
    url: str
    method: str
    body: Optional[dict]
    headers: Optional[dict]
    keywords_en: List[str]
    keywords_ar: List[str]
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ─── AI Provider Settings ─────────────────────────────────────────

class AIProviderConfig(BaseModel):
    provider: Literal["ollama", "deepseek"] = "ollama"
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com/v1"
