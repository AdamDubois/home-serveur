#!/usr/bin/env python3
"""
Service d'authentification pour Monétariat
"""

import os
from passlib.context import CryptContext
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse

# Configuration du hachage de mot de passe avec bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Mot de passe par défaut: admin123
# Hash généré avec bcrypt
# En production, définir MONETARIAT_PASSWORD_HASH dans les variables d'environnement
DEFAULT_PASSWORD_HASH = os.getenv(
    "MONETARIAT_PASSWORD_HASH",
    "$2b$12$HPiI9EX3bPAB5n1GrjglRO1RfH095ybG2OEpiI2zB6S08RPdjHD92"  # admin123
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si le mot de passe en clair correspond au hash
    
    Args:
        plain_password: Mot de passe en clair
        hashed_password: Hash du mot de passe
    
    Returns:
        True si le mot de passe correspond, False sinon
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Génère un hash bcrypt du mot de passe
    
    Args:
        password: Mot de passe en clair
    
    Returns:
        Hash du mot de passe
    """
    return pwd_context.hash(password)

def check_authentication(request: Request) -> bool:
    """
    Vérifie si l'utilisateur est authentifié via la session
    
    Args:
        request: Requête FastAPI
    
    Returns:
        True si authentifié, False sinon
    """
    return request.session.get("authenticated", False)

async def require_authentication(request: Request):
    """
    Dépendance FastAPI pour protéger les routes
    Redirige vers /monetariat/login si non authentifié
    
    Args:
        request: Requête FastAPI
    
    Raises:
        HTTPException: Si non authentifié, redirige vers login
    """
    if not check_authentication(request):
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/monetariat/login"}
        )
