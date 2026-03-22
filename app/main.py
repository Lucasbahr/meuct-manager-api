from fastapi import FastAPI, HTTPException
from app.routes.auth_routes import router as auth_router
from app.routes.student_routes import router as student_router
from app.routes.checkin_routes import router as checkin_router
from app.routes.health import router as health_router
from app.core.exceptions import http_exception_handler

app = FastAPI(title="MeuCT Manager API")

app.include_router(health_router)

app.add_exception_handler(HTTPException, http_exception_handler)

app.include_router(auth_router)

app.include_router(student_router)

app.include_router(checkin_router)
