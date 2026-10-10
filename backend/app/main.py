from fastapi import FastAPI

from app.routes import health, users

app = FastAPI(
    title="SIGA UEA API",
    description="API para gestão de Trabalhos de Conclusão de Curso da UEA.",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(users.router)
