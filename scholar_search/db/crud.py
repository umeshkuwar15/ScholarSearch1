
import json
from datetime import datetime, timezone
from typing import Optional, List

from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .models import User, Paper, SearchHistory, Favorite, Feedback

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(
    session: Session,
    username: str,
    email: str,
    password: str,
    full_name: str = "",
    institution: str = "",
) -> User:
    hashed = pwd_context.hash(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed,
        full_name=full_name,
        institution=institution,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def get_user_by_username(session: Session, username: str) -> Optional[User]:
    return session.query(User).filter(User.username == username).first()

def get_user_by_email(session: Session, email: str) -> Optional[User]:
    return session.query(User).filter(User.email == email).first()

def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    return session.query(User).filter(User.id == user_id).first()

def authenticate_user(session: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(session, username)
    if not user:
        return None
    if not pwd_context.verify(password, user.hashed_password):
        return None
    return user

def save_or_get_paper(session: Session, article_dict: dict) -> Paper:
    source = article_dict.get("source", "")
    source_id = article_dict.get("source_id", "")

    if source and source_id:
        existing = session.query(Paper).filter(
            Paper.source == source,
            Paper.source_id == source_id,
        ).first()
        if existing:
            return existing

    paper = Paper(
        title=article_dict.get("title", ""),
        authors=json.dumps(article_dict.get("authors", [])),
        year=article_dict.get("year"),
        abstract=article_dict.get("abstract", ""),
        source=source,
        source_id=source_id,
        doi=article_dict.get("doi", ""),
        url=article_dict.get("url", ""),
        journal=article_dict.get("journal", ""),
        citation_count=article_dict.get("citation_count", 0),
        keywords=json.dumps(article_dict.get("keywords", [])),
    )
    session.add(paper)
    session.commit()
    session.refresh(paper)
    return paper

def get_recent_papers(session: Session, limit: int = 20) -> List[Paper]:
    return session.query(Paper).order_by(desc(Paper.created_at)).limit(limit).all()

def save_search_history(
    session: Session,
    user_id: int,
    query: str = "",
    author: str = "",
    source: str = "all",
    num_results: int = 10,
    page: int = 1,
    total_found: int = 0,
) -> SearchHistory:
    entry = SearchHistory(
        user_id=user_id,
        query=query,
        author=author,
        source=source,
        num_results=num_results,
        page=page,
        total_found=total_found,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry

def get_user_search_history(
    session: Session,
    user_id: int,
    limit: int = 50,
) -> List[SearchHistory]:
    return (
        session.query(SearchHistory)
        .filter(SearchHistory.user_id == user_id)
        .order_by(desc(SearchHistory.searched_at))
        .limit(limit)
        .all()
    )

def add_favorite(
    session: Session,
    user_id: int,
    paper_id: int,
    notes: str = "",
) -> Favorite:
    existing = (
        session.query(Favorite)
        .filter(Favorite.user_id == user_id, Favorite.paper_id == paper_id)
        .first()
    )
    if existing:
        return existing

    fav = Favorite(user_id=user_id, paper_id=paper_id, notes=notes)
    session.add(fav)
    session.commit()
    session.refresh(fav)
    return fav

def remove_favorite(session: Session, user_id: int, paper_id: int) -> bool:
    fav = (
        session.query(Favorite)
        .filter(Favorite.user_id == user_id, Favorite.paper_id == paper_id)
        .first()
    )
    if fav:
        session.delete(fav)
        session.commit()
        return True
    return False

def get_user_favorites(session: Session, user_id: int) -> List[Favorite]:
    return (
        session.query(Favorite)
        .filter(Favorite.user_id == user_id)
        .order_by(desc(Favorite.created_at))
        .all()
    )

def is_favorite(session: Session, user_id: int, paper_id: int) -> bool:
    return (
        session.query(Favorite)
        .filter(Favorite.user_id == user_id, Favorite.paper_id == paper_id)
        .first()
    ) is not None

def add_feedback(
    session: Session,
    user_id: int,
    paper_id: int,
    rating: int = 0,
    comment: str = "",
    is_public: bool = False,
) -> Feedback:
    existing = (
        session.query(Feedback)
        .filter(Feedback.user_id == user_id, Feedback.paper_id == paper_id)
        .first()
    )
    if existing:
        existing.rating = rating
        existing.comment = comment
        existing.is_public = is_public
        existing.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(existing)
        return existing

    fb = Feedback(
        user_id=user_id,
        paper_id=paper_id,
        rating=rating,
        comment=comment,
        is_public=is_public,
    )
    session.add(fb)
    session.commit()
    session.refresh(fb)
    return fb

def get_paper_feedback(session: Session, paper_id: int) -> List[Feedback]:
    return (
        session.query(Feedback)
        .filter(Feedback.paper_id == paper_id, Feedback.is_public == True)
        .order_by(desc(Feedback.created_at))
        .all()
    )
