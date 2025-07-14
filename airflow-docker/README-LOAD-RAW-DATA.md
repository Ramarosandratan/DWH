# 📊 DAG load_raw_data - Chargement des Données RAW

## 🎯 Objectif

Le DAG `load_raw_data` extrait les données depuis la base MySQL OLTP et les charge dans les tables RAW PostgreSQL avec tous les champs convertis en TEXT, conformément au fichier `DDL_RAW.sql`.

---

## 🏗️ Architecture

### Source : MySQL OLTP (ecommerce_ops_db)
- **Tables sources** : categories, products, clients, sales, inventory, payment_history
- **Types de données** : Types natifs (INT, VARCHAR, DECIMAL, DATETIME, etc.)
- **Contraintes** : Clés primaires, clés étrangères, contraintes

### Destination : PostgreSQL RAW (ecommerce_raw_db)
- **Schema** : `raw`
- **Tables cibles** : *_raw (categories_raw, products_raw, etc.)
- **Types de données** : Tous les champs en TEXT
- **Contraintes** : Aucune (pas de PK, pas de FK)

---

## 📋 Tâches du DAG

### 1. **create_raw_schema**
- **Objectif** : Crée le schéma `raw` et toutes les tables RAW
- **Action** : Exécute le DDL pour créer/recréer les tables
- **Durée** : ~10 secondes

### 2. **load_*_raw** (6 tâches parallèles)
- **load_categories_raw** : Charge les catégories
- **load_products_raw** : Charge les produits
- **load_clients_raw** : Charge les clients
- **load_sales_raw** : Charge les ventes
- **load_inventory_raw** : Charge les stocks
- **load_payment_history_raw** : Charge l'historique des paiements

### 3. **validate_raw_data**
- **Objectif** : Valide les données chargées
- **Vérifications** :
  - Comptage des enregistrements par table
  - Vérification de la cohérence des relations
  - Détection des enregistrements orphelins
- **Rapport** : Génère un rapport de validation

### 4. **cleanup_old_reports**
- **Objectif** : Nettoie les anciens rapports de validation
- **Action** : Conserve seulement les 10 derniers rapports

---

## 🔄 Planification

- **Fréquence** : Quotidien à 1h du matin
- **Timezone** : UTC
- **Catchup** : Désactivé
- **Retries** : 2 tentatives avec 5 minutes d'intervalle

---

## 📊 Mapping des Tables

| Table Source (MySQL) | Table Cible (PostgreSQL) | Colonnes |
|----------------------|---------------------------|----------|
| `categories` | `raw.categories_raw` | category_id, name |
| `products` | `raw.products_raw` | product_id, name, category_id, price |
| `clients` | `raw.clients_raw` | client_id, first_name, last_name, email, created_at |
| `sales` | `raw.sales_raw` | sale_id, client_id, product_id, sale_date_time, quantity, total_amount |
| `inventory` | `raw.inventory_raw` | product_id, stock_quantity, reorder_threshold, updated_at |
| `payment_history` | `raw.payment_history_raw` | payment_id, sale_id, client_id, payment_date, amount, method, status |

---

## 🛠️ Transformations Appliquées

### Conversion de Types
- **Tous les champs** → TEXT
- **Valeurs NULL** → Chaîne vide ('')
- **Valeurs 'nan'/'None'** → Chaîne vide ('')

### Gestion des Données
- **Truncate & Load** : Les tables sont vidées puis rechargées
- **Insertion par batch** : 1000 enregistrements par batch
- **Gestion des erreurs** : Rollback automatique en cas d'erreur

---

## 📈 Surveillance et Validation

### Métriques Surveillées
- **Nombre d'enregistrements** par table
- **Cohérence des relations** (même en TEXT)
- **Enregistrements orphelins**
- **Temps d'exécution** par tâche

### Rapports Générés
- **Localisation** : `/opt/airflow/resource/raw_validation_report_YYYYMMDD_HHMMSS.txt`
- **Contenu** :
  - Statistiques par table
  - Total des enregistrements
  - Problèmes détectés
  - Horodatage

### Exemple de Rapport
```
=== RAPPORT DE VALIDATION DES DONNÉES RAW ===
Date: 2025-01-14 10:30:00

📊 STATISTIQUES PAR TABLE:
  • categories_raw: 3 enregistrements
  • products_raw: 6 enregistrements
  • clients_raw: 6 enregistrements
  • sales_raw: 10 enregistrements
  • inventory_raw: 6 enregistrements
  • payment_history_raw: 15 enregistrements

📈 TOTAL: 46 enregistrements chargés

✅ VALIDATION RÉUSSIE: Aucun problème détecté
```

---

## 🚀 Utilisation

### Exécution Manuelle
1. **Interface Airflow** : http://localhost:8090
2. **Cliquer sur** `load_raw_data`
3. **Trigger DAG** ▶️

### Exécution via CLI
```bash
# Déclencher le DAG
docker exec airflow-docker-airflow-scheduler-1 airflow dags trigger load_raw_data

# Voir l'état d'exécution
docker exec airflow-docker-airflow-scheduler-1 airflow dags state load_raw_data
```

### Ordre d'Exécution Recommandé
1. **setup_connections** (une fois)
2. **init_ecommerce_oltp** (une fois)
3. **process_payment_csv** (si nécessaire)
4. **load_raw_data** ← **Ce DAG**
5. **sync_ecommerce_data** (maintenance)

---

## 🔍 Dépannage

### Problèmes Courants

#### ❌ Erreur de Connexion MySQL
```
Solution: Vérifier que le DAG setup_connections a été exécuté
Commande: docker exec airflow-docker-airflow-scheduler-1 airflow connections list
```

#### ❌ Erreur de Connexion PostgreSQL
```
Solution: Vérifier que la base PostgreSQL RAW est accessible
Commande: docker exec airflow-docker-postgres_raw_db-1 psql -U postgres -d ecommerce_raw_db -c "\dt raw.*"
```

#### ❌ Tables Source Vides
```
Solution: Exécuter d'abord init_ecommerce_oltp pour créer les données
Ordre: init_ecommerce_oltp → load_raw_data
```

#### ❌ Échec de Validation
```
Solution: Consulter le rapport de validation dans /opt/airflow/resource/
Action: Vérifier la cohérence des données sources
```

### Logs Utiles
```bash
# Logs du DAG
docker-compose -f docker-compose-extended.yaml logs airflow-worker

# Logs PostgreSQL RAW
docker-compose -f docker-compose-extended.yaml logs postgres_raw_db

# Logs MySQL OLTP
docker-compose -f docker-compose-extended.yaml logs mysql_ops_db
```

---

## 📊 Vérification des Résultats

### Via pgAdmin
1. **URL** : http://localhost:8082
2. **Login** : admin@example.com / admin
3. **Serveur** : postgres_raw_db:5432
4. **Base** : ecommerce_raw_db
5. **Schema** : raw

### Via Ligne de Commande
```bash
# Connexion à PostgreSQL RAW
docker exec -it airflow-docker-postgres_raw_db-1 psql -U postgres -d ecommerce_raw_db

# Vérifier les tables
\dt raw.*

# Compter les enregistrements
SELECT 'categories_raw' as table_name, COUNT(*) FROM raw.categories_raw
UNION ALL
SELECT 'products_raw', COUNT(*) FROM raw.products_raw
UNION ALL
SELECT 'clients_raw', COUNT(*) FROM raw.clients_raw
UNION ALL
SELECT 'sales_raw', COUNT(*) FROM raw.sales_raw
UNION ALL
SELECT 'inventory_raw', COUNT(*) FROM raw.inventory_raw
UNION ALL
SELECT 'payment_history_raw', COUNT(*) FROM raw.payment_history_raw;
```

---

## 🎯 Prochaines Étapes

### Après l'Exécution Réussie
1. **Vérifier les données** dans pgAdmin
2. **Consulter le rapport** de validation
3. **Planifier les DAGs suivants** (transformation, DWH)

### Développement Futur
- **Chargement incrémental** (au lieu de truncate & load)
- **Détection des changements** (CDC)
- **Partitionnement** des grandes tables
- **Compression** des données historiques

---

## 📚 Ressources

### Documentation Technique
- **DDL_RAW.sql** : Structure des tables RAW
- **README-ECOMMERCE-DAGS.md** : Documentation générale
- **Logs Airflow** : Interface web → DAG → Logs

### Scripts Utiles
- **activate-dags.ps1** : Gestion des DAGs
- **diagnose-stack.ps1** : Diagnostic complet

---

**Version** : 1.0  
**Auteur** : Data Team  
**Dernière mise à jour** : Janvier 2025  
**Statut** : ✅ Opérationnel