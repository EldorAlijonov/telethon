from datetime import timedelta
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from app.database import Database
from app.services.keyword_service import KeywordService
from app.services.monitor_service import MonitorService
from app.services.user_service import UserService
from app.utils import DT_FORMAT, now_dt


def make_services():
    base_dir = Path(".test-tmp") / uuid4().hex
    base_dir.mkdir(parents=True, exist_ok=True)
    db = Database(str(base_dir / "test.db"))
    services = db, UserService(db), KeywordService(db, ["Ish", " ish ", "Vakansiya"]), MonitorService(db)
    return base_dir, services


def test_user_lifecycle_and_expiration():
    base_dir, services = make_services()
    db, users, keywords, monitor = services

    try:
        users.create_or_update_user(100, "Ali", "ali", "+998901234567")
        user = users.get_user_by_tg_id(100)
        assert user is not None
        assert user["status"] == "pending"
        assert not users.is_user_allowed(100)

        assert users.approve_user(100)
        assert users.is_user_allowed(100)
        assert keywords.get_keywords(100) == ["ish", "vakansiya"]

        monitor.set_enabled(100, True)
        users.save_telethon_session(100, "+998901234567", "session")
        assert monitor.is_enabled(100)
        assert users.has_telethon_session(100)

        expired_at = (now_dt() - timedelta(days=1)).strftime(DT_FORMAT)
        with db.connect() as conn:
            conn.execute("UPDATE users SET expires_at = ? WHERE tg_id = ?", (expired_at, 100))

        assert not users.is_user_allowed(100)
        expired_user = users.get_user_by_tg_id(100)
        assert expired_user is not None
        assert expired_user["status"] == "expired"
        assert not users.has_telethon_session(100)
        assert not monitor.is_enabled(100)
    finally:
        rmtree(base_dir, ignore_errors=True)


def test_keyword_crud_normalizes_duplicates():
    base_dir, services = make_services()
    _, _, keywords, _ = services

    try:
        assert keywords.ensure_default_keywords(200) == 2
        assert keywords.ensure_default_keywords(200) == 0
        assert keywords.get_keywords(200) == ["ish", "vakansiya"]

        success, message = keywords.add_keyword(200, " Xizmat ")
        assert success
        assert "qo" in message

        success, message = keywords.add_keyword(200, "xizmat")
        assert not success
        assert "mavjud" in message

        success, message = keywords.edit_keyword(200, "xizmat", "Buyurtma")
        assert success
        assert "yangilandi" in message
        assert "buyurtma" in keywords.get_keywords(200)

        assert keywords.delete_keyword(200, "buyurtma")
        assert "buyurtma" not in keywords.get_keywords(200)
    finally:
        rmtree(base_dir, ignore_errors=True)
