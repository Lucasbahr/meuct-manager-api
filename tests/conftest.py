import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient

from app.main import app
from app.db.base import Base
from app.db.deps import get_db
from app.services.user_service import create_user

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def upload_dir_tmp(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    yield


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()

    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    try:
        transaction.rollback()
    except Exception:
        pass
    connection.close()


@pytest.fixture(autouse=True)
def ensure_default_gym(db):
    from app.models.gym import Gym

    if db.query(Gym).filter(Gym.id == 1).first() is None:
        db.add(Gym(id=1, name="Test Gym"))
        db.commit()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def user(db):
    return create_user(
        db=db, email="user@test.com", password="123456", is_verified=True
    )


@pytest.fixture
def admin_user(db):
    return create_user(
        db=db,
        email="admin@test.com",
        password="123456",
        role="ADMIN_ACADEMIA",
        is_verified=True,
    )


@pytest.fixture
def user_token(client, user):
    response = client.post(
        "/auth/login", json={"email": "user@test.com", "password": "123456"}
    )

    assert response.status_code == 200, response.text

    return response.json()["data"]["access_token"]


@pytest.fixture
def admin_token(client, admin_user):
    response = client.post(
        "/auth/login", json={"email": "admin@test.com", "password": "123456"}
    )

    assert response.status_code == 200, response.text

    return response.json()["data"]["access_token"]
