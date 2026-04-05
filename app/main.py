from fastapi import FastAPI, HTTPException
from app.routes.auth_routes import router as auth_router
from app.routes.student_routes import router as student_router
from app.routes.checkin_routes import router as checkin_router
from app.routes.feed_routes import router as feed_router
from app.routes.admin_routes import router as admin_router
from app.routes.health import router as health_router
from app.core.exceptions import http_exception_handler
from app.db.session import SessionLocal
from app.scripts.create_admin import ensure_admin_exists
app = FastAPI(title="MeuCT Manager API")





@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        ensure_admin_exists(db)
    except Exception as e:
        print(f"⚠️ Falha no startup: {e}")
    finally:
        db.close()

app.include_router(health_router)

app.add_exception_handler(HTTPException, http_exception_handler)

app.include_router(auth_router)

app.include_router(student_router)

app.include_router(checkin_router)

app.include_router(feed_router)

app.include_router(admin_router)
