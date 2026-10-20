

import pytest
import json
from datetime import datetime, timezone

from scholar_search.db import (
    get_session,
    create_user,
    get_user_by_username,
    get_user_by_email,
    authenticate_user,
    save_or_get_paper,
    save_search_history,
    get_user_search_history,
    add_favorite,
    remove_favorite,
    get_user_favorites,
    is_favorite,
    add_feedback,
    get_paper_feedback,
    User,
    Paper,
    SearchHistory,
    Favorite,
    Feedback,
)

@pytest.fixture(autouse=True)
def setup_db():
    import scholar_search.db.database as db_module
    test_engine = db_module.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    db_module.engine = test_engine
    db_module.SessionLocal = db_module.sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    db_module.Base.metadata.create_all(bind=test_engine)
    yield
    test_engine.dispose()

def get_test_session():
    return get_session()

class TestUserCRUD:

    def test_create_user(self):
        session = get_test_session()
        try:
            user = create_user(
                session=session,
                username="testuser",
                email="test@example.com",
                password="secret123",
                full_name="Test User",
                institution="Test University",
            )
            assert user.id is not None
            assert user.username == "testuser"
            assert user.email == "test@example.com"
            assert user.full_name == "Test User"
            assert user.institution == "Test University"
            assert user.is_active is True
        finally:
            session.close()

    def test_get_user_by_username(self):
        session = get_test_session()
        try:
            create_user(session, "alice", "alice@test.com", "pass")
            user = get_user_by_username(session, "alice")
            assert user is not None
            assert user.username == "alice"

            not_found = get_user_by_username(session, "nonexistent")
            assert not_found is None
        finally:
            session.close()

    def test_get_user_by_email(self):
        session = get_test_session()
        try:
            create_user(session, "bob", "bob@test.com", "pass")
            user = get_user_by_email(session, "bob@test.com")
            assert user is not None
            assert user.email == "bob@test.com"

            not_found = get_user_by_email(session, "no@test.com")
            assert not_found is None
        finally:
            session.close()

    def test_authenticate_user_success(self):
        session = get_test_session()
        try:
            create_user(session, "charlie", "charlie@test.com", "correct_password")
            user = authenticate_user(session, "charlie", "correct_password")
            assert user is not None
            assert user.username == "charlie"
        finally:
            session.close()

    def test_authenticate_user_failure(self):
        session = get_test_session()
        try:
            create_user(session, "dave", "dave@test.com", "real_pass")
            user = authenticate_user(session, "dave", "wrong_pass")
            assert user is None
        finally:
            session.close()

    def test_authenticate_user_not_found(self):
        session = get_test_session()
        try:
            user = authenticate_user(session, "ghost", "any_pass")
            assert user is None
        finally:
            session.close()

    def test_duplicate_username_fails(self):
        session = get_test_session()
        try:
            create_user(session, "unique", "a@test.com", "pass")
            with pytest.raises(Exception):
                create_user(session, "unique", "b@test.com", "pass2")
        finally:
            session.close()

class TestPaperCRUD:

    def test_save_new_paper(self):
        session = get_test_session()
        try:
            article = {
                "title": "Deep Learning Advances",
                "authors": ["Alice", "Bob"],
                "year": 2024,
                "abstract": "A paper about deep learning.",
                "source": "arXiv",
                "source_id": "2401.00001",
                "doi": "10.1234/test",
                "url": "https://arxiv.org/abs/2401.00001",
                "journal": "",
                "citation_count": 10,
                "keywords": ["deep learning", "AI"],
            }
            paper = save_or_get_paper(session, article)
            assert paper.id is not None
            assert paper.title == "Deep Learning Advances"
            assert json.loads(paper.authors) == ["Alice", "Bob"]
            assert paper.year == 2024
            assert paper.source == "arXiv"
        finally:
            session.close()

    def test_get_existing_paper_by_source(self):
        session = get_test_session()
        try:
            article = {
                "title": "Original Title",
                "authors": ["Author1"],
                "year": 2023,
                "abstract": "Abstract",
                "source": "CrossRef",
                "source_id": "10.1000/test",
            }
            paper1 = save_or_get_paper(session, article)

            article2 = {
                "title": "Different Title",
                "authors": ["Author2"],
                "year": 2024,
                "abstract": "Different abstract",
                "source": "CrossRef",
                "source_id": "10.1000/test",
            }
            paper2 = save_or_get_paper(session, article2)

            assert paper1.id == paper2.id
        finally:
            session.close()

class TestSearchHistoryCRUD:

    def test_save_and_retrieve_history(self):
        session = get_test_session()
        try:
            user = create_user(session, "histuser", "hist@test.com", "pass")

            save_search_history(session, user.id, query="machine learning", source="all", total_found=50)
            save_search_history(session, user.id, author="Einstein", source="arxiv", total_found=10)

            history = get_user_search_history(session, user.id)
            assert len(history) == 2
            assert history[0].query == "machine learning" or history[0].author == "Einstein"
        finally:
            session.close()

    def test_history_ordering(self):
        session = get_test_session()
        try:
            user = create_user(session, "orderuser", "order@test.com", "pass")
            save_search_history(session, user.id, query="first")
            import time
            time.sleep(0.01)
            save_search_history(session, user.id, query="second")

            history = get_user_search_history(session, user.id)
            assert len(history) == 2
            assert history[0].query == "second"
        finally:
            session.close()

class TestFavoriteCRUD:

    def test_add_favorite(self):
        session = get_test_session()
        try:
            user = create_user(session, "favuser", "fav@test.com", "pass")
            paper = save_or_get_paper(session, {
                "title": "Favorite Paper",
                "authors": ["Author"],
                "source": "arXiv",
                "source_id": "2401.99999",
            })

            fav = add_favorite(session, user.id, paper.id, notes="Great paper!")
            assert fav.id is not None
            assert fav.notes == "Great paper!"
        finally:
            session.close()

    def test_remove_favorite(self):
        session = get_test_session()
        try:
            user = create_user(session, "rmuser", "rm@test.com", "pass")
            paper = save_or_get_paper(session, {
                "title": "To Remove", "authors": ["A"], "source": "arXiv", "source_id": "rm.1",
            })
            add_favorite(session, user.id, paper.id)

            removed = remove_favorite(session, user.id, paper.id)
            assert removed is True

            assert is_favorite(session, user.id, paper.id) is False
        finally:
            session.close()

    def test_get_user_favorites(self):
        session = get_test_session()
        try:
            user = create_user(session, "listuser", "list@test.com", "pass")
            paper1 = save_or_get_paper(session, {
                "title": "Paper 1", "authors": ["A"], "source": "arXiv", "source_id": "l1",
            })
            paper2 = save_or_get_paper(session, {
                "title": "Paper 2", "authors": ["B"], "source": "CrossRef", "source_id": "l2",
            })
            add_favorite(session, user.id, paper1.id)
            add_favorite(session, user.id, paper2.id)

            favs = get_user_favorites(session, user.id)
            assert len(favs) == 2
        finally:
            session.close()

    def test_is_favorite(self):
        session = get_test_session()
        try:
            user = create_user(session, "checkuser", "check@test.com", "pass")
            paper = save_or_get_paper(session, {
                "title": "Check Paper", "authors": ["C"], "source": "arXiv", "source_id": "c1",
            })

            assert is_favorite(session, user.id, paper.id) is False
            add_favorite(session, user.id, paper.id)
            assert is_favorite(session, user.id, paper.id) is True
        finally:
            session.close()

class TestFeedbackCRUD:

    def test_add_feedback(self):
        session = get_test_session()
        try:
            user = create_user(session, "fbuser", "fb@test.com", "pass")
            paper = save_or_get_paper(session, {
                "title": "Rated Paper", "authors": ["R"], "source": "arXiv", "source_id": "r1",
            })

            fb = add_feedback(session, user.id, paper.id, rating=4, comment="Good paper!", is_public=True)
            assert fb.id is not None
            assert fb.rating == 4
            assert fb.comment == "Good paper!"
            assert fb.is_public is True
        finally:
            session.close()

    def test_update_existing_feedback(self):
        session = get_test_session()
        try:
            user = create_user(session, "upduser", "upd@test.com", "pass")
            paper = save_or_get_paper(session, {
                "title": "Update Paper", "authors": ["U"], "source": "arXiv", "source_id": "u1",
            })

            fb1 = add_feedback(session, user.id, paper.id, rating=2, comment="Meh")
            fb2 = add_feedback(session, user.id, paper.id, rating=5, comment="Excellent!")

            assert fb1.id == fb2.id
            assert fb2.rating == 5
            assert fb2.comment == "Excellent!"
        finally:
            session.close()

    def test_get_public_feedback(self):
        session = get_test_session()
        try:
            user1 = create_user(session, "pubuser1", "p1@test.com", "pass")
            user2 = create_user(session, "pubuser2", "p2@test.com", "pass")
            paper = save_or_get_paper(session, {
                "title": "Public Paper", "authors": ["P"], "source": "arXiv", "source_id": "p1",
            })

            add_feedback(session, user1.id, paper.id, rating=5, comment="Public!", is_public=True)
            add_feedback(session, user2.id, paper.id, rating=3, comment="Private!", is_public=False)

            feedbacks = get_paper_feedback(session, paper.id)
            assert len(feedbacks) == 1
            assert feedbacks[0].comment == "Public!"
        finally:
            session.close()
