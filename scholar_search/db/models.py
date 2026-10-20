
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(150), default="")
    institution = Column(String(200), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    search_history = relationship("SearchHistory", back_populates="user",
                                  cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user",
                             cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="user",
                             cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "institution": self.institution,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    authors = Column(Text, default="")
    year = Column(Integer, nullable=True)
    abstract = Column(Text, default="")
    source = Column(String(50), default="")
    source_id = Column(String(200), default="")
    doi = Column(String(200), default="")
    url = Column(String(500), default="")
    journal = Column(String(300), default="")
    citation_count = Column(Integer, default=0)
    keywords = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    favorites = relationship("Favorite", back_populates="paper",
                             cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="paper",
                             cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_paper_source_id", "source", "source_id"),
    )

    def __repr__(self):
        return f"<Paper(id={self.id}, title='{self.title[:50]}...')>"

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "title": self.title,
            "authors": json.loads(self.authors) if self.authors else [],
            "year": self.year,
            "abstract": self.abstract,
            "source": self.source,
            "source_id": self.source_id,
            "doi": self.doi,
            "url": self.url,
            "journal": self.journal,
            "citation_count": self.citation_count,
            "keywords": json.loads(self.keywords) if self.keywords else [],
        }

class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query = Column(String(300), default="")
    author = Column(String(200), default="")
    source = Column(String(50), default="all")
    num_results = Column(Integer, default=10)
    page = Column(Integer, default=1)
    total_found = Column(Integer, default=0)
    searched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="search_history")

    __table_args__ = (
        Index("idx_search_history_user", "user_id", "searched_at"),
    )

    def __repr__(self):
        return f"<SearchHistory(id={self.id}, query='{self.query}', user_id={self.user_id})>"

    def to_dict(self):
        return {
            "id": self.id,
            "query": self.query,
            "author": self.author,
            "source": self.source,
            "num_results": self.num_results,
            "total_found": self.total_found,
            "searched_at": self.searched_at.isoformat() if self.searched_at else None,
        }

class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="favorites")
    paper = relationship("Paper", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "paper_id", name="uq_user_paper_favorite"),
    )

    def __repr__(self):
        return f"<Favorite(user_id={self.user_id}, paper_id={self.paper_id})>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "paper_id": self.paper_id,
            "paper": self.paper.to_dict() if self.paper else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, default=0)
    comment = Column(Text, default="")
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="feedbacks")
    paper = relationship("Paper", back_populates="feedbacks")

    __table_args__ = (
        UniqueConstraint("user_id", "paper_id", name="uq_user_paper_feedback"),
    )

    def __repr__(self):
        return f"<Feedback(user_id={self.user_id}, paper_id={self.paper_id}, rating={self.rating})>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "paper_id": self.paper_id,
            "rating": self.rating,
            "comment": self.comment,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "username": self.user.username if self.user else None,
        }
