from app.db.deps import get_db


def test_get_db():
    gen = get_db()
    db = next(gen)

    assert db is not None

    try:
        next(gen)
    except StopIteration:
        pass
