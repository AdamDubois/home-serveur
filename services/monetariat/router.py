#!/usr/bin/env python3
"""
Routes FastAPI pour Monétariat
"""

from fastapi import APIRouter, Request, UploadFile, File, Depends, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
import csv
import io
from datetime import datetime

from . import database as db
from . import auth

# Configuration
router = APIRouter()
BASE_DIR = Path(__file__).parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Initialiser la DB au démarrage
db.init_db()

# Models Pydantic
class NewCategory(BaseModel):
    nom: str
    type: str

class NewTransaction(BaseModel):
    date: str
    compte_id: int
    montant: float
    categorie_id: Optional[int] = None
    description: Optional[str] = None
    necessite: Optional[str] = None
    necessity_level:  Optional[str] = None
    mode_paiement_id:  Optional[int] = None
    type: str
    compte_destination_id:  Optional[int] = None
    subscription_id: Optional[int] = None

# ============ AUTHENTICATION ROUTES ============

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Page de connexion"""
    # Si déjà authentifié, rediriger vers le dashboard
    if auth.check_authentication(request):
        return RedirectResponse(url="/monetariat/", status_code=302)
    
    html_path = BASE_DIR / "templates" / "monetariat" / "login.html"
    return FileResponse(html_path)

@router.post("/login")
async def login(request: Request, password: str = Form(...)):
    """Traitement de la connexion"""
    # Vérifier le mot de passe
    if auth.verify_password(password, auth.DEFAULT_PASSWORD_HASH):
        # Créer la session
        request.session["authenticated"] = True
        return RedirectResponse(url="/monetariat/", status_code=302)
    else:
        # Mot de passe incorrect - retourner la page de login avec erreur
        return templates.TemplateResponse(
            "monetariat/login.html",
            {
                "request": request,
                "error": "Mot de passe incorrect"
            },
            status_code=401
        )

@router.get("/logout")
async def logout(request: Request):
    """Déconnexion"""
    request.session.clear()
    return RedirectResponse(url="/monetariat/login", status_code=302)

# ============ PROTECTED ROUTES ============

@router.get("/", response_class=HTMLResponse)
async def monetariat_dashboard(request: Request):
    """Dashboard principal - Vue d'ensemble"""
    # Vérifier l'authentification et rediriger si nécessaire
    if not auth.check_authentication(request):
        return RedirectResponse(url="/monetariat/login", status_code=302)
    
    html_path = BASE_DIR / "templates" / "monetariat" / "dashboard.html"
    return FileResponse(html_path)

@router.get("/form", response_class=HTMLResponse)
async def monetariat_form(request: Request):
    """Formulaire d'ajout de transaction"""
    # Vérifier l'authentification et rediriger si nécessaire
    if not auth.check_authentication(request):
        return RedirectResponse(url="/monetariat/login", status_code=302)
    
    html_path = BASE_DIR / "templates" / "monetariat" / "form.html"
    return FileResponse(html_path)

@router.get("/settings", response_class=HTMLResponse)
async def monetariat_settings(request: Request):
    """Page de paramètres des comptes"""
    # Vérifier l'authentification et rediriger si nécessaire
    if not auth.check_authentication(request):
        return RedirectResponse(url="/monetariat/login", status_code=302)
    
    html_path = BASE_DIR / "templates" / "monetariat" / "settings.html"
    return FileResponse(html_path)

@router.get("/import", response_class=HTMLResponse)
async def monetariat_import(request: Request):
    """Page d'import CSV"""
    # Vérifier l'authentification et rediriger si nécessaire
    if not auth.check_authentication(request):
        return RedirectResponse(url="/monetariat/login", status_code=302)
    
    html_path = BASE_DIR / "templates" / "monetariat" / "import.html"
    return FileResponse(html_path)

@router.get("/compte/{account_id}", response_class=HTMLResponse)
async def monetariat_compte(request: Request, account_id: int):
    """Page des transactions d'un compte"""
    # Vérifier l'authentification et rediriger si nécessaire
    if not auth.check_authentication(request):
        return RedirectResponse(url="/monetariat/login", status_code=302)
    
    html_path = BASE_DIR / "templates" / "monetariat" / "compte.html"
    return FileResponse(html_path)

# API Routes
@router.get("/api/accounts")
async def api_get_accounts(_: None = Depends(auth.require_authentication)):
    """Récupère tous les comptes"""
    return db.get_all_accounts()

@router.get("/api/categories/{cat_type}")
async def api_get_categories(cat_type: str, _: None = Depends(auth.require_authentication)):
    """Récupère les catégories par type (depense/revenu) triées avec Autres à la fin"""
    return db.get_categories_sorted(cat_type)

@router.get("/api/payment-methods")
async def api_get_payment_methods(_: None = Depends(auth.require_authentication)):
    """Récupère tous les modes de paiement"""
    return db.get_all_payment_methods()

@router.get("/api/subscriptions")
async def api_get_subscriptions(_: None = Depends(auth.require_authentication)):
    """Récupère tous les abonnements"""
    return db.get_all_subscriptions()

@router.post("/api/categories")
async def api_add_category(category: NewCategory, _: None = Depends(auth.require_authentication)):
    """Ajoute une nouvelle catégorie"""
    result = db.add_category(category.nom, category.type)
    if result:
        return result
    else:
        return JSONResponse(
            status_code=400,
            content={"error":  "Catégorie déjà existante"}
        )

@router.post("/api/subscriptions")
async def api_add_subscription(data: dict, _: None = Depends(auth.require_authentication)):
    """Ajoute un nouvel abonnement"""
    result = db.add_subscription(data['nom'])
    if result:
        return result
    else:
        return JSONResponse(
            status_code=400,
            content={"error": "Abonnement déjà existant"}
        )

@router.delete("/api/categories/{category_id}")
async def api_delete_category(category_id:  int, _: None = Depends(auth.require_authentication)):
    """Supprime une catégorie"""
    result = db.delete_category(category_id)
    if 'error' in result:
        return JSONResponse(status_code=400, content=result)
    return result

@router.put("/api/categories/reorder")
async def api_reorder_categories(data: dict, _: None = Depends(auth.require_authentication)):
    """Réordonne les catégories
    Attend un dict avec 'orders':  [{'id': 1, 'ordre': 0}, {'id': 2, 'ordre': 1}, ...]
    """
    result = db.update_categories_order(data['orders'])
    if 'error' in result:
        return JSONResponse(status_code=400, content=result)
    return result

@router.post("/api/transactions")
async def api_add_transaction(transaction:  NewTransaction, _: None = Depends(auth.require_authentication)):
    """Ajoute une nouvelle transaction"""
    transaction_id = db.add_transaction(transaction.dict())
    return {"id": transaction_id, "status": "success"}

@router.get("/api/transactions")
async def api_get_transactions(limit: int = 100, _: None = Depends(auth.require_authentication)):
    """Récupère toutes les transactions"""
    return db.get_all_transactions(limit)

@router.get("/api/accounts/summary")
async def api_get_account_summary(_: None = Depends(auth.require_authentication)):
    """Récupère le résumé des comptes avec soldes calculés"""
    return db.get_account_summary()

@router.put("/api/accounts/{account_id}/balance")
async def api_update_account_balance(account_id:  int, data: dict, _: None = Depends(auth.require_authentication)):
    """Met à jour le solde d'un compte"""
    result = db.update_account_balance(account_id, data['balance'])
    if 'error' in result:
        return JSONResponse(status_code=400, content=result)
    return result

@router.put("/api/accounts/{account_id}/name")
async def api_update_account_name(account_id:  int, data: dict, _: None = Depends(auth.require_authentication)):
    """Met à jour le nom d'un compte"""
    result = db.update_account_name(account_id, data['name'])
    if 'error' in result:
        return JSONResponse(status_code=400, content=result)
    return result

# ============ ROUTES IMPORT CSV ============

@router.post("/api/import/parse")
async def api_parse_csv(file: UploadFile = File(...), _: None = Depends(auth.require_authentication)):
    """Parse un fichier CSV et retourne un aperçu des données"""
    try:
        # Lire le contenu du fichier
        contents = await file.read()
        decoded = contents.decode('utf-8')
        
        # Parser le CSV
        csv_reader = csv.DictReader(io.StringIO(decoded))
        rows = list(csv_reader)
        
        if not rows:
            return JSONResponse(
                status_code=400,
                content={"error":  "Le fichier CSV est vide"}
            )
        
        # Détecter les colonnes disponibles
        columns = list(rows[0].keys())
        
        # Retourner un aperçu (max 10 lignes)
        preview = rows[:10]
        
        return {
            "success": True,
            "columns": columns,
            "preview": preview,
            "total_rows": len(rows),
            "all_data": rows  # Garder toutes les données pour l'import
        }
    
    except Exception as e: 
        return JSONResponse(
            status_code=400,
            content={"error":  f"Erreur lors de la lecture du fichier: {str(e)}"}
        )

@router.post("/api/import/execute")
async def api_execute_import(data: dict, _: None = Depends(auth.require_authentication)):
    """Exécute l'import des transactions depuis les données CSV mappées
    
    Attend:  
    {
        "compte_id": 1,
        "type": "depense",
        "mode_paiement_id": 1,
        "mapping": {
            "date": "Date",
            "description": "Description",
            "montant": "Montant",
            "categorie":  "Catégorie"
        },
        "rows": [...]
    }
    """
    try:
        compte_id = data['compte_id']
        transaction_type = data['type']
        mode_paiement_id = data.get('mode_paiement_id')
        mapping = data['mapping']
        rows = data['rows']
        
        transactions_to_import = []
        
        for row in rows:
            # Extraire les valeurs selon le mapping
            date_str = row.get(mapping['date'], '')
            description = row.get(mapping.get('description', ''), '')
            categorie_nom = row.get(mapping.get('categorie', ''), 'Autres')
            
            # ========== GESTION DES MONTANTS ==========
            is_multi_currency = mapping.get('is_multi_currency', False)
            taux_usd_cad = mapping.get('taux_usd_cad', 1.35)
            
            if is_multi_currency:
                # Mode CAD$ + USD$
                montant_cad_str = row.get('CAD$', '0').replace('$', '').replace(',', '').replace(' ', '').strip()
                montant_usd_str = row.get('USD$', '0').replace('$', '').replace(',', '').replace(' ', '').strip()
                
                try:
                    montant_cad_float = float(montant_cad_str) if montant_cad_str else 0
                except ValueError:
                    montant_cad_float = 0
                
                try:
                    montant_usd_float = float(montant_usd_str) if montant_usd_str else 0
                except ValueError:
                    montant_usd_float = 0
                
                # Prendre CAD en priorité, sinon USD converti
                if montant_cad_float != 0:
                    montant_final = montant_cad_float
                elif montant_usd_float != 0:
                    montant_final = montant_usd_float * taux_usd_cad
                else:
                    continue  # Ignorer si les deux sont à 0
            else:
                # Mode simple (une seule colonne)
                montant_str = row.get(mapping['montant'], '0')
                montant_str = montant_str.replace('$', '').replace(',', '').replace(' ', '').strip()
                try:
                    montant_final = float(montant_str)
                except ValueError:
                    continue
            
            # ========== FIN GESTION MONTANTS ==========
            
            # Détecter le type si "auto"
            actual_type = transaction_type
            if transaction_type == 'auto':  
                actual_type = 'depense' if montant_final < 0 else 'revenu'
            
            # Convertir en valeur absolue
            montant = abs(montant_final)
            
            # Ignorer les lignes avec montant = 0
            if montant == 0:
                continue
            
            # Parser la date
            try:
                # Essayer différents formats de date
                for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%-m/%-d/%Y', '%m/%d/%y']:  
                    try:
                        date_obj = datetime.strptime(date_str.strip(), date_format)
                        date_formatted = date_obj.strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
                else:
                    date_formatted = datetime.now().strftime('%Y-%m-%d')
            except Exception:
                date_formatted = datetime.now().strftime('%Y-%m-%d')
            
            # Trouver ou créer la catégorie
            if categorie_nom:  
                categorie_id = db.find_or_create_category(categorie_nom, actual_type)
            else:
                categorie_id = None
            
            # Créer la transaction
            transaction_data = {
                'date': date_formatted,
                'compte_id': compte_id,
                'montant': montant,
                'categorie_id': categorie_id,
                'description': description,
                'necessite':  None,
                'necessity_level': 'Neutre' if actual_type == 'depense' else None,
                'mode_paiement_id': mode_paiement_id,
                'type': actual_type,
                'compte_destination_id': None,
                'subscription_id': None
            }
            
            transactions_to_import.append(transaction_data)
        
        # Importer en masse
        result = db.bulk_add_transactions(transactions_to_import)
        
        return result
    
    except Exception as e: 
        return JSONResponse(
            status_code=400,
            content={"error": f"Erreur lors de l'import: {str(e)}"}
        )