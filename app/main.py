from fastapi import FastAPI, HTTPException
from app.routes.auth_routes import router as auth_router
from app.routes.student_routes import router as student_router
from app.routes.checkin_routes import router as checkin_router
from app.routes.feed_routes import router as feed_router
from app.routes.admin_routes import router as admin_router
from app.routes.health import router as health_router
from app.routes.gym_routes import router as gym_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.training_routes import router as training_router
from app.routes.marketplace_routes import router as marketplace_router
from app.routes.stock_routes import router as stock_router
from app.routes.membership_routes import router as membership_router
from app.routes.reports_routes import router as reports_router
from app.routes.student_modality_routes import router as student_modality_router
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

app.include_router(gym_router)

app.include_router(auth_router)

app.include_router(student_router)

app.include_router(checkin_router)

app.include_router(feed_router)

app.include_router(admin_router)

app.include_router(dashboard_router)

app.include_router(training_router)

app.include_router(marketplace_router)

app.include_router(stock_router)

app.include_router(membership_router)

app.include_router(reports_router)

app.include_router(student_modality_router)
