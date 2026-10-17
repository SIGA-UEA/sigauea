from fastapi import APIRouter, FastAPI

from app.erros import registrar_tratadores
from app.routes import areas, auth, catalogo, health, perfil, tccs, turmas, usuarios

app = FastAPI(
    title="SIGA UEA API",
    description="API para gestão de Trabalhos de Conclusão de Curso da UEA.",
    version="0.1.0",
)
registrar_tratadores(app)

app.include_router(health.router)

# Todas as rotas de negócio ficam sob /api/v1 (contrato das fichas das histórias).
v1 = APIRouter(prefix="/api/v1")
v1.include_router(auth.router)
v1.include_router(perfil.router)  # antes de usuarios: /usuarios/me não é /usuarios/{id}
v1.include_router(usuarios.router)
v1.include_router(areas.router)  # antes de catalogo: /areas/gestao não é a lista simples
v1.include_router(catalogo.router)
v1.include_router(turmas.router)
v1.include_router(tccs.router)  # /tccs/formulario antes de /tccs/{id} (ordem no arquivo)
app.include_router(v1)
