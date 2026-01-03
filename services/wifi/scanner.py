#!/usr/bin/env python3
"""
Script de monitoring WiFi - Ping le routeur et enregistre les stats
Adapté pour la nouvelle structure home-serveur
"""

import re
import sqlite3
import subprocess
import sys
import os
import time
from datetime import datetime
from pathlib import Path

# Forcer le fuseau horaire local
os.environ['TZ'] = 'America/Montreal'
time.tzset()

# Configuration - NOUVEAUX PATHS
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "databases" / "wifi.db"
LOG_PATH = BASE_DIR / "logs" / "wifi_scanner.log"

# Hôtes à monitorer (adapter selon votre réseau)
HOSTS = [
    "192.168.2.1",      # Routeur local (ADAPTER SELON TON RÉSEAU)
    "8.8.8.8",          # Google DNS (Internet)
]

def log_message(message):
    """Enregistre un message dans le fichier de log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(log_entry)
    
    print(log_entry.strip())

def ping_host(host, count=4, timeout=2):
    """
    Ping un hôte et retourne les statistiques
    
    Returns:
        dict: Statistiques du ping ou None si erreur
    """
    try: 
        result = subprocess.run(
            ['ping', '-c', str(count), '-W', str(timeout), host],
            capture_output=True,
            text=True,
            timeout=timeout * count + 5
        )
        
        return parse_ping_output(result.stdout, result.returncode)
    
    except subprocess.TimeoutExpired:
        log_message(f"❌ Timeout lors du ping de {host}")
        return {
            'min':  None,
            'avg': None,
            'max': None,
            'loss': 100.0,
            'transmitted': count,
            'received': 0,
            'status': 'timeout'
        }
    except Exception as e: 
        log_message(f"❌ Erreur lors du ping de {host}: {e}")
        return None

def parse_ping_output(output, return_code):
    """
    Parse la sortie de la commande ping
    """
    stats = {
        'min': None,
        'avg': None,
        'max': None,
        'loss': 100.0,
        'transmitted': 0,
        'received': 0,
        'status': 'success' if return_code == 0 else 'failed'
    }
    
    # Extraire les statistiques de paquets
    packet_pattern = r'(\d+) packets transmitted, (\d+) received, ([\d.]+)% packet loss'
    packet_match = re.search(packet_pattern, output)
    
    if packet_match:
        stats['transmitted'] = int(packet_match.group(1))
        stats['received'] = int(packet_match.group(2))
        stats['loss'] = float(packet_match.group(3))
    
    # Extraire les temps de réponse (RTT)
    rtt_pattern = r'rtt min/avg/max/[a-z]+ = ([\d.]+)/([\d.]+)/([\d.]+)'
    rtt_match = re.search(rtt_pattern, output)
    
    if rtt_match:
        stats['min'] = float(rtt_match.group(1))
        stats['avg'] = float(rtt_match.group(2))
        stats['max'] = float(rtt_match.group(3))
    
    return stats

def save_to_db(host, stats):
    """Enregistre les statistiques dans la base de données"""
    try: 
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
            INSERT INTO ping_stats 
            (timestamp, host, min_latency, avg_latency, max_latency, packet_loss, 
             packets_transmitted, packets_received, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            current_time,
            host,
            stats['min'],
            stats['avg'],
            stats['max'],
            stats['loss'],
            stats['transmitted'],
            stats['received'],
            stats['status']
        ))
        
        conn.commit()
        conn.close()
        
        log_message(f"✅ Données enregistrées pour {host} - Latence: {stats['avg']}ms, Perte: {stats['loss']}%")
        
    except Exception as e:
        log_message(f"❌ Erreur lors de l'enregistrement dans la DB: {e}")

def main():
    """Fonction principale"""
    log_message("🚀 Début du monitoring WiFi")
    
    for host in HOSTS:
        log_message(f"📡 Ping de {host}...")
        stats = ping_host(host)
        
        if stats:
            save_to_db(host, stats)
        else:
            log_message(f"⚠️ Impossible de récupérer les stats pour {host}")
    
    log_message("✅ Monitoring WiFi terminé\n")

if __name__ == "__main__":
    main()