import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scholar_search.db.database import SessionLocal, init_db
from scholar_search.db.models import Paper

init_db()

session = SessionLocal()

papers = session.query(Paper).all()

if not papers:
    print("No data found ❌")
else:
    for paper in papers:
        print("ID:", paper.id)
        print("Title:", paper.title)
        print("Author:", paper.authors)
        print("-" * 40)

session.close()
