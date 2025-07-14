# DAGs Airflow pour le Projet E-commerce

Ce document décrit les DAGs Airflow créés pour traiter les données SQL et CSV du projet e-commerce.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MySQL OLTP    │    │   PostgreSQL    │    │     Airflow     │
│ (ecommerce_ops) │    │   RAW Layer     │    │   Orchestrator  │
│                 │    │                 │    │                 │
│ • categories    │    │ • categories_raw│    │ • DAG Management│
│ • products      │────▶ • products_raw  │────▶ • Scheduling   │
│ • clients       │    │ • clients_raw   │    │ • Monitoring    │
│ • sales         │    │ • sales_raw     │    │ • Error Handling│
│ • inventory     │    │ • inventory_raw │    │                 │
│ • payment_hist  │    │ • payment_raw   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 DAGs Disponibles

### 1. `setup_connections` - Configuration des Connexions
**Objectif**: Configurer automatiquement les connexions Airflow vers les bases de données.

**Tâches**:
- `create_mysql_connection`: Connexion vers MySQL OLTP
- `create_postgres_connection`: Connexion vers PostgreSQL RAW
- `create_filesystem_connection`: Connexion pour les fichiers CSV
- `test_mysql_connection`: Test de la connexion MySQL
- `test_postgres_connection`: Test de la connexion PostgreSQL
- `display_connection_info`: Affichage des informations de connexion

**Exécution**: Manuelle (à exécuter en premier)

### 2. `init_ecommerce_oltp` - Initialisation Base OLTP
**Objectif**: Créer et peupler la base de données MySQL OLTP avec les données initiales.

**Tâches**:
- `create_database`: Création de la base `ecommerce_ops_db`
- `create_tables`: Création des tables (categories, products, clients, sales, inventory, payment_history)
- `insert_data`: Insertion des données de test
- `verify_data`: Vérification de l'intégrité des données

**Données insérées**:
- 3 catégories de produits
- 6 produits
- 6 clients
- 10 ventes
- Données d'inventaire
- 10 historiques de paiement

**Exécution**: Manuelle (à exécuter après setup_connections)

### 3. `process_payment_csv` - Traitement CSV Paiements
**Objectif**: Traiter et nettoyer le fichier CSV des paiements avant insertion en base.

**Tâches**:
- `validate_csv_file`: Validation de l'existence et structure du CSV
- `clean_csv_data`: Nettoyage des données (formats de dates, montants)
- `validate_cleaned_data`: Validation des données nettoyées
- `backup_existing_data`: Sauvegarde des données existantes
- `load_csv_to_mysql`: Chargement en base MySQL
- `verify_data_integrity`: Vérification de l'intégrité
- `cleanup_temp_files`: Nettoyage des fichiers temporaires

**Nettoyage effectué**:
- Conversion des montants (virgules → points)
- Normalisation des dates (DD/MM/YYYY → YYYY-MM-DD)
- Suppression des espaces et caractères indésirables
- Validation des types de données

**Exécution**: Quotidienne à minuit

### 4. `sync_ecommerce_data` - Synchronisation et Maintenance
**Objectif**: Maintenance quotidienne et surveillance de la qualité des données.

**Tâches**:
- `check_database_health`: Vérification de la santé de la base
- `generate_data_quality_report`: Génération de rapports de qualité
- `reconcile_sales_payments`: Réconciliation ventes/paiements
- `update_inventory_status`: Mise à jour des statuts de stock
- `optimize_database`: Optimisation et nettoyage
- `wait_for_new_csv`: Surveillance de nouveaux fichiers CSV
- `cleanup_old_logs`: Nettoyage des anciens logs

**Rapports générés**:
- Compteurs par table
- Produits sans stock
- Ventes sans paiement
- Paiements échoués/en attente
- Incohérences de montants
- Produits sous seuil de réapprovisionnement

**Exécution**: Quotidienne à 2h du matin

## 🚀 Démarrage Rapide

### 1. Démarrer la Stack
```powershell
# Démarrage standard
.\start-ecommerce-stack.ps1

# Avec outils d'administration
.\start-ecommerce-stack.ps1 -WithAdmin

# Avec nettoyage préalable
.\start-ecommerce-stack.ps1 -Clean -WithAdmin
```

### 2. Configuration Initiale
1. Accéder à Airflow: http://localhost:8090 (airflow/airflow)
2. Exécuter le DAG `setup_connections`
3. Exécuter le DAG `init_ecommerce_oltp`
4. Activer le DAG `process_payment_csv`
5. Activer le DAG `sync_ecommerce_data`

### 3. Surveillance
- **Airflow UI**: http://localhost:8090
- **phpMyAdmin**: http://localhost:8081 (si -WithAdmin)
- **pgAdmin**: http://localhost:8082 (admin@example.com/admin)
- **Flower**: http://localhost:5555 (si -WithFlower)

## 🔧 Configuration

### Connexions Airflow
| Connexion ID | Type | Host | Port | Database | User | Password |
|--------------|------|------|------|----------|------|----------|
| mysql_ops | MySQL | mysql_ops_db | 3306 | ecommerce_ops_db | root | root_password |
| postgres_raw | PostgreSQL | postgres_raw_db | 5432 | ecommerce_raw_db | postgres | postgres_password |
| fs_default | Filesystem | - | - | - | - | - |

### Variables d'Environnement
```env
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
_PIP_ADDITIONAL_REQUIREMENTS=apache-airflow-providers-mysql apache-airflow-providers-postgres pandas
```

## 📁 Structure des Fichiers

```
airflow-docker/
├── dags/
│   ├── setup_connections.py          # Configuration connexions
│   ├── init_ecommerce_oltp.py        # Initialisation OLTP
│   ├── process_payment_csv.py        # Traitement CSV
│   └── sync_ecommerce_data.py        # Synchronisation
├── resource/
│   └── payment_history.csv           # Fichier CSV source
├── docker-compose-extended.yaml      # Configuration Docker complète
├── start-ecommerce-stack.ps1         # Script de démarrage
├── stop-ecommerce-stack.ps1          # Script d'arrêt
└── README-ECOMMERCE-DAGS.md          # Cette documentation
```

## 🔍 Monitoring et Alertes

### Indicateurs de Qualité Surveillés
- **Produits sans stock**: Produits avec stock = 0
- **Ventes sans paiement**: Ventes sans enregistrement de paiement
- **Paiements échoués**: Statut = 'failed'
- **Paiements en attente**: Statut = 'pending'
- **Incohérences de montants**: Différence entre vente et paiement
- **Produits sous seuil**: Stock ≤ seuil de réapprovisionnement

### Logs et Rapports
- Rapports de qualité quotidiens dans `/opt/airflow/resource/`
- Logs Airflow dans l'interface web
- Sauvegardes automatiques avant modifications

## 🛠️ Maintenance

### Commandes Utiles
```bash
# Voir les logs en temps réel
docker-compose -f docker-compose-extended.yaml logs -f

# Redémarrer un service spécifique
docker-compose -f docker-compose-extended.yaml restart airflow-scheduler

# Accéder au conteneur Airflow
docker-compose -f docker-compose-extended.yaml exec airflow-worker bash

# Nettoyer les volumes (ATTENTION: perte de données)
docker-compose -f docker-compose-extended.yaml down -v
```

### Sauvegarde des Données
Les DAGs créent automatiquement des sauvegardes avant les modifications importantes:
- Tables de sauvegarde avec timestamp
- Rétention de 7 sauvegardes maximum
- Nettoyage automatique des anciennes sauvegardes

## ⚠️ Dépannage

### Problèmes Courants

1. **Connexions échouées**
   - Vérifier que les services de base de données sont démarrés
   - Exécuter le DAG `setup_connections`
   - Vérifier les logs des conteneurs

2. **Fichier CSV non trouvé**
   - Vérifier la présence du fichier dans `/resource/`
   - Vérifier les permissions de fichier

3. **Erreurs de format de données**
   - Le DAG `process_payment_csv` nettoie automatiquement les données
   - Vérifier les logs pour les détails des erreurs

4. **Services lents à démarrer**
   - Attendre 2-3 minutes après le démarrage
   - Vérifier l'état avec `docker-compose ps`

### Logs Importants
- **Airflow**: Interface web → Admin → Logs
- **MySQL**: `docker-compose logs mysql_ops_db`
- **PostgreSQL**: `docker-compose logs postgres_raw_db`

## 📞 Support

Pour toute question ou problème:
1. Consulter les logs Airflow
2. Vérifier l'état des services Docker
3. Consulter cette documentation
4. Contacter l'équipe Data

---

**Version**: 1.0  
**Dernière mise à jour**: Janvier 2025  
**Auteur**: Data Team