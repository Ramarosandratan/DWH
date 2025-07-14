# 🌟 DAG load_dwh_star - Data Warehouse en Étoile

## 🎯 Objectif

Le DAG `load_dwh_star` transforme les données RAW PostgreSQL en un modèle dimensionnel en étoile (star schema) optimisé pour l'analyse et le reporting business.

---

## 🏗️ Architecture du Data Warehouse

### 📊 Modèle en Étoile Implémenté
```
                    dim_date
                        |
    dim_customer ---- fact_sales ---- dim_product
                        |
                    dim_time
                        |
                dim_payment_method
```

### 🗄️ Tables Créées

#### 📅 **dim_date** - Dimension Temporelle (Date)
| Colonne | Type | Description |
|---------|------|-------------|
| `date_key` | INT (PK) | Clé au format YYYYMMDD |
| `day` | INT | Jour du mois (1-31) |
| `month` | INT | Mois (1-12) |
| `quarter` | INT | Trimestre (1-4) |
| `year` | INT | Année |
| `day_of_week` | VARCHAR(10) | Nom du jour |
| `day_of_week_num` | INT | Numéro ISO du jour (1-7) |

#### ⏰ **dim_time** - Dimension Temporelle (Heure)
| Colonne | Type | Description |
|---------|------|-------------|
| `time_key` | INT (PK) | Clé au format HHMMSS |
| `hour` | INT | Heure (0-23) |
| `minute` | INT | Minute (0-59) |
| `second` | INT | Seconde (0-59) |
| `am_pm` | VARCHAR(2) | AM/PM |

#### 👥 **dim_customer** - Dimension Client
| Colonne | Type | Description |
|---------|------|-------------|
| `customer_key` | INT (PK) | Clé surrogate |
| `client_id` | INT | ID client original |
| `full_name` | TEXT | Nom complet (MAJUSCULES) |
| `email` | TEXT | Email (MAJUSCULES) |
| `signup_date` | DATE | Date d'inscription |

#### 📦 **dim_product** - Dimension Produit
| Colonne | Type | Description |
|---------|------|-------------|
| `product_key` | INT (PK) | Clé surrogate |
| `product_id` | INT | ID produit original |
| `product_name` | TEXT | Nom produit (MAJUSCULES) |
| `category_id` | INT | ID catégorie |
| `category_name` | TEXT | Nom catégorie (MAJUSCULES) |
| `price` | NUMERIC(10,2) | Prix unitaire |

#### 💳 **dim_payment_method** - Dimension Méthode de Paiement
| Colonne | Type | Description |
|---------|------|-------------|
| `payment_method_key` | INT (PK) | Clé surrogate |
| `method` | VARCHAR(50) | Méthode (MAJUSCULES) |

#### 📈 **fact_sales** - Table de Faits (Ventes)
| Colonne | Type | Description |
|---------|------|-------------|
| `sale_key` | INT (PK) | Clé surrogate |
| `sale_id` | INT | ID vente original |
| `date_key` | INT (FK) | Référence dim_date |
| `time_key` | INT (FK) | Référence dim_time |
| `product_key` | INT (FK) | Référence dim_product |
| `customer_key` | INT (FK) | Référence dim_customer |
| `quantity` | INT | Quantité vendue |
| `total_amount` | NUMERIC(10,2) | Montant total |
| `payment_method_key` | INT (FK) | Référence dim_payment_method |

---

## 🔄 Flux d'Exécution

### 1. **create_dwh_schema_and_tables** (30s)
- Crée le schéma `ecommerce_dwh_star`
- Supprime et recrée toutes les tables
- Crée les séquences pour les clés surrogates
- Ajoute les contraintes de clés étrangères
- Crée les index pour les performances

### 2. **create_dwh_procedures** (10s)
- Crée la fonction `parse_datetime()` pour gérer les formats de date
- Crée toutes les procédures stockées de chargement
- Crée la procédure orchestratrice `etl_master()`

### 3. **Chargement des Dimensions** (Parallèle - 1-2 min)
- `load_dim_date` : Extrait toutes les dates uniques
- `load_dim_time` : Extrait toutes les heures uniques
- `load_dim_customer` : Transforme et charge les clients
- `load_dim_product` : Joint produits et catégories
- `load_dim_payment_method` : Charge les méthodes de paiement

### 4. **load_fact_sales** (1 min)
- Joint toutes les dimensions avec les ventes RAW
- Calcule les clés temporelles (date_key, time_key)
- Résout les clés surrogates des dimensions
- Charge la table de faits

### 5. **validate_dwh_data** (30s)
- Compte les enregistrements par table
- Vérifie l'intégrité référentielle
- Calcule les statistiques business
- Génère un rapport de validation

### 6. **cleanup_old_dwh_reports** (5s)
- Nettoie les anciens rapports
- Conserve les 10 derniers

---

## ⚙️ Configuration

### 📅 **Planification**
- **Fréquence** : Quotidien à 3h du matin
- **Après** : `load_raw_data` (1h) et `sync_ecommerce_data` (2h)
- **Statut** : ✅ **ACTIF**
- **Retries** : 2 tentatives avec 5 minutes d'intervalle

### 🔗 **Connexions Requises**
- **postgres_raw_conn** : Connexion PostgreSQL (RAW + DWH)

### 🔄 **Transformations Appliquées**

#### Nettoyage des Données
- **Texte** : `TRIM()` et `UPPER()` pour la cohérence
- **Nombres** : Remplacement des virgules par des points
- **Dates** : Parsing intelligent des formats DD/MM/YYYY et YYYY-MM-DD

#### Clés Temporelles
- **date_key** : Format YYYYMMDD (ex: 20250114)
- **time_key** : Format HHMMSS (ex: 143052)

#### Clés Surrogates
- **Séquences PostgreSQL** pour générer des clés uniques
- **Indépendantes** des IDs métier

---

## 🚀 Utilisation

### ✅ **Prérequis**
1. ✅ `setup_connections` (connexions configurées)
2. ✅ `init_ecommerce_oltp` (données OLTP créées)
3. ✅ `load_raw_data` (données RAW chargées)

### 🎯 **Ordre d'Exécution Recommandé**
1. ✅ `setup_connections`
2. ✅ `init_ecommerce_oltp`
3. ✅ `process_payment_csv` (optionnel)
4. ✅ `load_raw_data`
5. 🆕 **`load_dwh_star`** ← **Ce DAG**
6. ✅ `sync_ecommerce_data`

### 🖱️ **Exécution Manuelle**
1. **Accédez à** : http://localhost:8090
2. **Connectez-vous** : airflow/airflow
3. **Cliquez sur** : `load_dwh_star`
4. **Cliquez sur** : "Trigger DAG" ▶️
5. **Durée attendue** : ~4-5 minutes

---

## 📈 Résultats Attendus

### 📊 **Données Transformées**
```
📋 STATISTIQUES ATTENDUES:
  • dim_date: ~10-15 dates uniques
  • dim_time: ~10-15 heures uniques
  • dim_customer: 6 clients
  • dim_product: 6 produits
  • dim_payment_method: 3-4 méthodes
  • fact_sales: 10+ ventes

📈 STATISTIQUES BUSINESS:
  • Montant total des ventes: ~500-1000 €
  • Montant moyen par vente: ~50-100 €
  • Clients uniques: 6
  • Produits vendus: 6
```

### 📄 **Rapport Généré**
- **Localisation** : `/opt/airflow/resource/dwh_validation_report_*.txt`
- **Contenu** : Statistiques détaillées, validation, métriques business

---

## 🔍 Vérification des Résultats

### Via pgAdmin
1. **URL** : http://localhost:8082
2. **Login** : admin@example.com / admin
3. **Base** : ecommerce_raw_db
4. **Schema** : `ecommerce_dwh_star`

### Requêtes de Vérification
```sql
-- Vue d'ensemble
SELECT 
  'dim_date' as table_name, COUNT(*) as records FROM ecommerce_dwh_star.dim_date
UNION ALL
SELECT 'dim_time', COUNT(*) FROM ecommerce_dwh_star.dim_time
UNION ALL
SELECT 'dim_customer', COUNT(*) FROM ecommerce_dwh_star.dim_customer
UNION ALL
SELECT 'dim_product', COUNT(*) FROM ecommerce_dwh_star.dim_product
UNION ALL
SELECT 'dim_payment_method', COUNT(*) FROM ecommerce_dwh_star.dim_payment_method
UNION ALL
SELECT 'fact_sales', COUNT(*) FROM ecommerce_dwh_star.fact_sales;

-- Analyse des ventes par client
SELECT 
  c.full_name,
  COUNT(*) as nb_ventes,
  SUM(f.total_amount) as total_achats
FROM ecommerce_dwh_star.fact_sales f
JOIN ecommerce_dwh_star.dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.customer_key, c.full_name
ORDER BY total_achats DESC;

-- Ventes par produit
SELECT 
  p.product_name,
  p.category_name,
  COUNT(*) as nb_ventes,
  SUM(f.quantity) as quantite_totale,
  SUM(f.total_amount) as ca_total
FROM ecommerce_dwh_star.fact_sales f
JOIN ecommerce_dwh_star.dim_product p ON f.product_key = p.product_key
GROUP BY p.product_key, p.product_name, p.category_name
ORDER BY ca_total DESC;

-- Ventes par jour de la semaine
SELECT 
  d.day_of_week,
  COUNT(*) as nb_ventes,
  SUM(f.total_amount) as ca_jour
FROM ecommerce_dwh_star.fact_sales f
JOIN ecommerce_dwh_star.dim_date d ON f.date_key = d.date_key
GROUP BY d.day_of_week_num, d.day_of_week
ORDER BY d.day_of_week_num;
```

---

## 🛠️ Fonctionnalités Avancées

### 🔄 **Gestion des Formats de Date**
- **Fonction `parse_datetime()`** : Gère automatiquement DD/MM/YYYY et YYYY-MM-DD
- **Robuste** : Supporte les variations de format
- **Performance** : Fonction IMMUTABLE pour l'optimisation

### 📊 **Optimisations Performance**
- **Index** sur toutes les clés étrangères de fact_sales
- **Clés surrogates** pour de meilleures performances de jointure
- **Contraintes** pour l'intégrité des données

### 🔍 **Validation Avancée**
- **Intégrité référentielle** : Vérification des orphelins
- **Statistiques business** : Métriques métier calculées
- **Rapports horodatés** : Traçabilité complète

---

## 🎯 Cas d'Usage Business

### 📊 **Reporting et Analytics**
- **Tableaux de bord** : Ventes par période, client, produit
- **Analyses temporelles** : Tendances, saisonnalité
- **Segmentation client** : Profils d'achat, valeur client

### 🔍 **Requêtes Business Typiques**
```sql
-- Top 5 des produits les plus vendus
SELECT p.product_name, SUM(f.quantity) as total_qty
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.product_name
ORDER BY total_qty DESC
LIMIT 5;

-- CA mensuel
SELECT 
  d.year, d.month,
  SUM(f.total_amount) as ca_mensuel
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- Analyse par tranche horaire
SELECT 
  CASE 
    WHEN t.hour BETWEEN 6 AND 11 THEN 'Matin'
    WHEN t.hour BETWEEN 12 AND 17 THEN 'Après-midi'
    WHEN t.hour BETWEEN 18 AND 22 THEN 'Soirée'
    ELSE 'Nuit'
  END as tranche_horaire,
  COUNT(*) as nb_ventes,
  AVG(f.total_amount) as panier_moyen
FROM fact_sales f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY 1
ORDER BY nb_ventes DESC;
```

---

## 🔧 Dépannage

### Problèmes Courants

#### ❌ Erreur de Parsing de Date
```
Cause: Format de date non reconnu dans les données RAW
Solution: Vérifier la fonction parse_datetime() et les données sources
```

#### ❌ Violation de Contrainte FK
```
Cause: Données manquantes dans les dimensions
Solution: Vérifier l'ordre d'exécution (dimensions avant faits)
```

#### ❌ Séquences Non Trouvées
```
Cause: Schéma DWH non créé correctement
Solution: Réexécuter create_dwh_schema_and_tables
```

### Logs Utiles
```bash
# Logs du DAG
docker-compose -f docker-compose-extended.yaml logs airflow-worker

# Logs PostgreSQL
docker-compose -f docker-compose-extended.yaml logs postgres_raw_db

# Connexion directe pour debug
docker exec -it airflow-docker-postgres_raw_db-1 psql -U postgres -d ecommerce_raw_db
```

---

## 🎯 Prochaines Étapes

### Après l'Exécution Réussie
1. **Explorez les données** dans pgAdmin
2. **Testez les requêtes** business
3. **Consultez le rapport** de validation
4. **Préparez les outils** de visualisation (Tableau, Power BI, etc.)

### Extensions Possibles
- **Dimensions SCD Type 2** : Historisation des changements
- **Agrégats précalculés** : Tables de résumé pour les performances
- **Partitionnement** : Par date pour les gros volumes
- **Cubes OLAP** : Pour l'analyse multidimensionnelle

---

## 📚 Ressources

### Documentation
- **DDL_DWH.sql** : Structure des tables DWH
- **PROCEDURE.sql** : Procédures stockées
- **README-ECOMMERCE-DAGS.md** : Documentation générale

### Outils de Visualisation
- **pgAdmin** : http://localhost:8082
- **Airflow UI** : http://localhost:8090
- **Rapports** : `/opt/airflow/resource/dwh_validation_report_*.txt`

---

**Version** : 1.0  
**Auteur** : Data Team  
**Dernière mise à jour** : Janvier 2025  
**Statut** : ✅ Opérationnel  
**Modèle** : Star Schema (Étoile)