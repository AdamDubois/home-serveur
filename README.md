# 🏠 Home Serveur

Serveur personnel avec plusieurs services accessibles via VPN WireGuard.

## Services

- **📡 WiFi Monitor** :  Surveillance du réseau et statistiques
- **💰 Monétariat** : Suivi des dépenses personnelles (protégé par mot de passe)

## Installation

Voir `INSTALL.md`

## Configuration

### Authentification Monétariat

Le service Monétariat est protégé par authentification. Par défaut, le mot de passe est `admin123`.

Pour changer le mot de passe en production :

1. Générer un nouveau hash bcrypt :
```bash
python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('votre_nouveau_mot_de_passe'))"
```

2. Définir la variable d'environnement :
```bash
export MONETARIAT_PASSWORD_HASH="votre_hash_bcrypt"
```

3. Pour persistance, ajouter dans un fichier `.env` :
```bash
MONETARIAT_PASSWORD_HASH=votre_hash_bcrypt
SESSION_SECRET_KEY=votre_cle_secrete
```

Voir `.env.example` pour plus de détails.

## Accès

- **URL** : `http://192.168.2.168:5000`
- **VPN** : WireGuard requis pour accès externe

## Stack technique

- FastAPI
- SQLite
- Jinja2
- systemd