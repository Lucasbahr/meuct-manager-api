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
    from decimal import Decimal

    from app.models.graduation import Graduation
    from app.models.gym import Gym
    from app.models.modality import Modality
    from app.models.tenant_config import TenantConfig

    if db.query(Gym).filter(Gym.id == 1).first() is None:
        db.add(Gym(id=1, name="Test Gym", slug="test-gym"))
        db.commit()

    if db.query(TenantConfig).filter(TenantConfig.gym_id == 1).first() is None:
        db.add(TenantConfig(gym_id=1))
        db.commit()

    m = db.query(Modality).filter(Modality.name == "Muay Thai").first()
    if not m:
        m = Modality(name="Muay Thai")
        db.add(m)
        db.flush()
    has_g = (
        db.query(Graduation)
        .filter(Graduation.gym_id == 1, Graduation.modality_id == m.id)
        .first()
    )
    if not has_g:
        db.add(
            Graduation(
                gym_id=1,
                modality_id=m.id,
                name="Branca",
                level=1,
                required_hours=Decimal("10"),
            )
        )
        db.add(
            Graduation(
                gym_id=1,
                modality_id=m.id,
                name="Azul",
                level=2,
                required_hours=Decimal("20"),
            )
        )
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
