#!/usr/bin/env python3
"""
Gestion de la base de données Monétariat
"""

import sqlite3
from pathlib import Path
from datetime import datetime

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "databases" / "monetariat.db"

def get_db_connection():
    """Crée une connexion à la base de données"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialise la base de données"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Table des comptes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,
            solde_initial REAL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table des catégories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            type TEXT NOT NULL,
            ordre INTEGER DEFAULT 999,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(nom, type)
        )
    ''')
    
    # Table des modes de paiement
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Table des abonnements
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table des transactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            compte_id INTEGER NOT NULL,
            montant REAL NOT NULL,
            categorie_id INTEGER,
            description TEXT,
            necessite TEXT,
            necessity_level TEXT,
            mode_paiement_id INTEGER,
            type TEXT NOT NULL,
            compte_destination_id INTEGER,
            subscription_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (compte_id) REFERENCES accounts(id),
            FOREIGN KEY (categorie_id) REFERENCES categories(id),
            FOREIGN KEY (mode_paiement_id) REFERENCES payment_methods(id),
            FOREIGN KEY (compte_destination_id) REFERENCES accounts(id),
            FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
        )
    ''')
    
    # Insérer les comptes par défaut
    cursor.execute('SELECT COUNT(*) FROM accounts')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO accounts (nom, type, solde_initial) VALUES ('Débit', 'debit', 0)")
        cursor.execute("INSERT INTO accounts (nom, type, solde_initial) VALUES ('Épargne', 'epargne', 0)")
        cursor.execute("INSERT INTO accounts (nom, type, solde_initial) VALUES ('Crédit', 'credit', 0)")
    
    # Insérer les catégories par défaut - DÉPENSES
    default_expense_categories = [
        'Alimentation', 'Transport', 'Logement', 'Loisirs', 
        'Santé', 'Abonnement', 'Autres'
    ]
    for cat in default_expense_categories:  
        cursor.execute(
            "INSERT OR IGNORE INTO categories (nom, type) VALUES (?, 'depense')",
            (cat,)
        )
    
    # Insérer les catégories par défaut - REVENUS
    default_income_categories = ['Salaire', 'Remboursement', 'Autres']
    for cat in default_income_categories:
        cursor.execute(
            "INSERT OR IGNORE INTO categories (nom, type) VALUES (?, 'revenu')",
            (cat,)
        )
    
    # Insérer les modes de paiement par défaut
    default_payment_methods = ['Comptant', 'Carte', 'Virement', 'Chèque']
    for method in default_payment_methods:  
        cursor.execute(
            "INSERT OR IGNORE INTO payment_methods (nom) VALUES (?)",
            (method,)
        )
    
    conn.commit()
    conn.close()

# Fonctions CRUD

def get_all_accounts():
    """Récupère tous les comptes"""
    conn = get_db_connection()
    accounts = conn.execute('SELECT * FROM accounts ORDER BY id').fetchall()
    conn.close()
    return [dict(row) for row in accounts]

def get_categories_by_type(cat_type):
    """Récupère les catégories par type (depense/revenu)"""
    conn = get_db_connection()
    categories = conn.execute(
        'SELECT * FROM categories WHERE type = ? ORDER BY nom',
        (cat_type,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in categories]

def get_categories_sorted(cat_type):
    """Récupère les catégories triées avec 'Autres' à la fin et ordre personnalisé"""
    conn = get_db_connection()
    categories = conn.execute('''
        SELECT * FROM categories 
        WHERE type = ? 
        ORDER BY 
            ordre ASC,
            CASE WHEN LOWER(nom) = 'autres' THEN 1 ELSE 0 END,
            nom
    ''', (cat_type,)).fetchall()
    conn.close()
    return [dict(row) for row in categories]

def get_all_payment_methods():
    """Récupère tous les modes de paiement"""
    conn = get_db_connection()
    methods = conn.execute('SELECT * FROM payment_methods ORDER BY nom').fetchall()
    conn.close()
    return [dict(row) for row in methods]

def get_all_subscriptions():
    """Récupère tous les abonnements"""
    conn = get_db_connection()
    subs = conn.execute('SELECT * FROM subscriptions ORDER BY nom').fetchall()
    conn.close()
    return [dict(row) for row in subs]

def add_category(nom, cat_type):
    """Ajoute une nouvelle catégorie"""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO categories (nom, type) VALUES (?, ?)',
            (nom, cat_type)
        )
        conn.commit()
        category_id = cursor.lastrowid
        conn.close()
        return {'id': category_id, 'nom': nom, 'type': cat_type}
    except sqlite3.IntegrityError:
        conn.close()
        return None

def add_subscription(nom):
    """Ajoute un nouvel abonnement"""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO subscriptions (nom) VALUES (?)',
            (nom,)
        )
        conn.commit()
        subscription_id = cursor.lastrowid
        conn.close()
        return {'id': subscription_id, 'nom': nom}
    except sqlite3.IntegrityError:
        conn.close()
        return None

def delete_category(category_id):
    """Supprime une catégorie"""
    conn = get_db_connection()
    try:
        # Vérifier si la catégorie est utilisée
        cursor = conn.execute(
            'SELECT COUNT(*) FROM transactions WHERE categorie_id = ?',
            (category_id,)
        )
        count = cursor.fetchone()[0]
        
        if count > 0:
            conn.close()
            return {'error': f'Impossible de supprimer :  {count} transaction(s) utilisent cette catégorie'}
        
        conn.execute('DELETE FROM categories WHERE id = ?', (category_id,))
        conn.commit()
        conn.close()
        return {'success': True}
    except Exception as e: 
        conn.close()
        return {'error':  str(e)}

def update_categories_order(category_orders):
    """Met à jour l'ordre de plusieurs catégories
    category_orders: liste de dict avec {id: x, ordre: y}
    """
    conn = get_db_connection()
    try:
        for item in category_orders:
            conn.execute(
                'UPDATE categories SET ordre = ?  WHERE id = ?',
                (item['ordre'], item['id'])
            )
        conn.commit()
        conn.close()
        return {'success': True}
    except Exception as e: 
        conn.close()
        return {'error': str(e)}

def add_transaction(data):
    """Ajoute une nouvelle transaction"""
    conn = get_db_connection()
    cursor = conn.execute('''
        INSERT INTO transactions 
        (date, compte_id, montant, categorie_id, description, necessite, 
         necessity_level, mode_paiement_id, type, compte_destination_id, subscription_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['date'],
        data['compte_id'],
        data['montant'],
        data.get('categorie_id'),
        data.get('description'),
        data.get('necessite'),
        data.get('necessity_level'),
        data.get('mode_paiement_id'),
        data['type'],
        data.get('compte_destination_id'),
        data.get('subscription_id')
    ))
    conn.commit()
    transaction_id = cursor.lastrowid
    
    conn.close()
    return transaction_id

def get_all_transactions(limit=100):
    """Récupère toutes les transactions"""
    conn = get_db_connection()
    transactions = conn.execute('''
        SELECT 
            t.*,
            a.nom as compte_nom,
            c.nom as categorie_nom,
            pm.nom as mode_paiement_nom,
            ad.nom as compte_destination_nom,
            s.nom as subscription_nom
        FROM transactions t
        LEFT JOIN accounts a ON t.compte_id = a.id
        LEFT JOIN categories c ON t.categorie_id = c.id
        LEFT JOIN payment_methods pm ON t.mode_paiement_id = pm.id
        LEFT JOIN accounts ad ON t.compte_destination_id = ad.id
        LEFT JOIN subscriptions s ON t.subscription_id = s.id
        ORDER BY t.date DESC, t.created_at DESC
        LIMIT ?  
    ''', (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in transactions]

def update_account_balance(account_id, new_balance):
    """Met à jour le solde d'un compte"""
    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE accounts SET solde_initial = ? WHERE id = ?',
            (new_balance, account_id)
        )
        conn.commit()
        conn.close()
        return {'success': True}
    except Exception as e:
        conn.close()
        return {'error': str(e)}

def update_account_name(account_id, new_name):
    """Met à jour le nom d'un compte"""
    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE accounts SET nom = ? WHERE id = ?',
            (new_name, account_id)
        )
        conn.commit()
        conn.close()
        return {'success':  True}
    except sqlite3.IntegrityError:
        conn.close()
        return {'error': 'Ce nom de compte existe déjà'}
    except Exception as e:
        conn.close()
        return {'error': str(e)}

def get_account_summary():
    """Récupère le résumé de tous les comptes avec leurs soldes calculés"""
    conn = get_db_connection()
    
    # Récupérer tous les comptes
    accounts = conn.execute('SELECT * FROM accounts ORDER BY id').fetchall()
    result = []
    
    for account in accounts:
        account_dict = dict(account)
        account_id = account_dict['id']
        
        # Calculer le solde réel basé sur les transactions
        # Revenus et transferts entrants
        revenus = conn.execute('''
            SELECT COALESCE(SUM(montant), 0) as total
            FROM transactions
            WHERE (type = 'revenu' AND compte_id = ?)
               OR (type = 'transfert' AND compte_destination_id = ?)
        ''', (account_id, account_id)).fetchone()[0]
        
        # Dépenses et transferts sortants
        depenses = conn.execute('''
            SELECT COALESCE(SUM(montant), 0) as total
            FROM transactions
            WHERE (type = 'depense' AND compte_id = ?)
               OR (type = 'transfert' AND compte_id = ?)
        ''', (account_id, account_id)).fetchone()[0]
        
        solde_reel = account_dict['solde_initial'] + revenus - depenses
        account_dict['solde_reel'] = solde_reel
        
        result.append(account_dict)
    
    conn.close()
    return result

def bulk_add_transactions(transactions_data):
    """Ajoute plusieurs transactions en une seule fois
    transactions_data: liste de dict avec les données de chaque transaction
    Retourne:  dict avec succès, erreurs, et nombre importé
    """
    conn = get_db_connection()
    imported = 0
    errors = []
    
    for idx, data in enumerate(transactions_data):
        try:
            cursor = conn.execute('''
                INSERT INTO transactions 
                (date, compte_id, montant, categorie_id, description, necessite, 
                 necessity_level, mode_paiement_id, type, compte_destination_id, subscription_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['date'],
                data['compte_id'],
                data['montant'],
                data.get('categorie_id'),
                data.get('description'),
                data.get('necessite'),
                data.get('necessity_level'),
                data.get('mode_paiement_id'),
                data['type'],
                data.get('compte_destination_id'),
                data.get('subscription_id')
            ))
            imported += 1
        except Exception as e:
            errors.append({
                'line':  idx + 1,
                'error': str(e),
                'data': data
            })
    
    conn.commit()
    conn.close()
    
    return {
        'success': True,
        'imported': imported,
        'errors': errors,
        'total': len(transactions_data)
    }

def find_or_create_category(nom, cat_type):
    """Trouve une catégorie ou la crée si elle n'existe pas
    Retourne l'ID de la catégorie
    """
    conn = get_db_connection()
    
    # Chercher la catégorie existante
    result = conn.execute(
        'SELECT id FROM categories WHERE LOWER(nom) = LOWER(?) AND type = ?',
        (nom, cat_type)
    ).fetchone()
    
    if result:
        conn.close()
        return result[0]
    
    # Créer la catégorie si elle n'existe pas
    try:
        cursor = conn.execute(
            'INSERT INTO categories (nom, type) VALUES (?, ?)',
            (nom, cat_type)
        )
        conn.commit()
        category_id = cursor.lastrowid
        conn.close()
        return category_id
    except Exception: 
        conn.close()
        return None