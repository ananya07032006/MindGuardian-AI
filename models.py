"""
MindGuardian AI — SQLAlchemy Models

Tables
------
users           — registered accounts
mood_entries    — one mood log per session
chat_sessions   — groups messages into a conversation
chat_messages   — individual turns inside a chat session
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from app import db, login_manager


# ---------------------------------------------------------------------------
# Flask-Login user loader
# ---------------------------------------------------------------------------

@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64),  unique=True, nullable=False, index=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    mood_entries  = db.relationship("MoodEntry",   backref="user", lazy="dynamic", cascade="all, delete-orphan")
    chat_sessions = db.relationship("ChatSession", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"


# ---------------------------------------------------------------------------
# Mood Entry
# ---------------------------------------------------------------------------

MOOD_CHOICES = ["great", "good", "okay", "bad", "terrible"]

EMOTION_LABELS = [
    "joy", "sadness", "anger", "fear",
    "disgust", "surprise", "neutral",
]

class MoodEntry(db.Model):
    __tablename__ = "mood_entries"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # User-selected mood (1 = terrible … 5 = great)
    mood       = db.Column(db.String(16), nullable=False)       # one of MOOD_CHOICES
    mood_score = db.Column(db.Integer,   nullable=False)        # 1–5

    # Optional free-text journal note
    note       = db.Column(db.Text, nullable=True)

    # ML-detected emotion from the note (may be None if no note provided)
    detected_emotion       = db.Column(db.String(32), nullable=True)
    emotion_confidence     = db.Column(db.Float,      nullable=True)

    # Suicide / crisis risk flag from the note
    risk_level             = db.Column(db.String(16), nullable=True)  # low / medium / high
    risk_confidence        = db.Column(db.Float,      nullable=True)

    logged_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def mood_score_from_label(self) -> int:
        """Return numeric score 1–5 derived from the stored mood label."""
        return MOOD_CHOICES[::-1].index(self.mood) + 1 if self.mood in MOOD_CHOICES else 3

    def __repr__(self) -> str:
        return f"<MoodEntry user={self.user_id} mood={self.mood!r} at={self.logged_at}>"


# ---------------------------------------------------------------------------
# Chat Session
# ---------------------------------------------------------------------------

class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title      = db.Column(db.String(120), nullable=False, default="New conversation")
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at   = db.Column(db.DateTime, nullable=True)

    messages   = db.relationship(
        "ChatMessage",
        backref="session",
        lazy="dynamic",
        order_by="ChatMessage.sent_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} user={self.user_id}>"


# ---------------------------------------------------------------------------
# Chat Message
# ---------------------------------------------------------------------------

class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id         = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=False, index=True)

    role       = db.Column(db.String(10), nullable=False)   # "user" | "bot"
    content    = db.Column(db.Text,       nullable=False)

    # ML metadata — populated only for user messages
    detected_emotion   = db.Column(db.String(32), nullable=True)
    emotion_confidence = db.Column(db.Float,      nullable=True)
    risk_level         = db.Column(db.String(16), nullable=True)
    risk_confidence    = db.Column(db.Float,      nullable=True)

    sent_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self) -> str:
        return f"<ChatMessage session={self.session_id} role={self.role!r}>"
