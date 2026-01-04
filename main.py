#!/usr/bin/env python3
"""
Application FastAPI centrale - Home Serveur
Port 5000 - Accessible via VPN WireGuard
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
import secrets

# Importer les routers des services
from services.wifi import router as wifi_router
from services.monetariat import router as monetariat_router

# Configuration
app = FastAPI(
    title="Home Serveur",
    description="Serveur personnel - Monitoring & Services",
    version="1.0.0"
)

# Générer une clé secrète pour les sessions (à externaliser en production)
SECRET_KEY = secrets.token_urlsafe(32)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Inclure les routers des services
app.include_router(wifi_router.router, prefix="/wifi", tags=["WiFi Monitor"])
app.include_router(monetariat_router.router, prefix="/monetariat", tags=["Monétariat"])

@app.get("/", response_class=HTMLResponse)
async def home():
    """Page d'accueil - Liste des services"""
    html_path = Path(__file__).parent / "templates" / "home" / "index.html"
    return FileResponse(html_path)

if __name__ == "__main__": 
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)