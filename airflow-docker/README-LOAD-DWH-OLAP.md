# 📊 DAG load_dwh_olap - Data Warehouse OLAP Optimisé

## 🎯 Objectif

Le DAG `load_dwh_olap` transforme les données RAW PostgreSQL en un modèle dimensionnel OLAP optimisé pour les requêtes analytiques haute performance avec des types de données natifs PostgreSQL.

---

## 🏗️ Architecture du Data Warehouse OLAP

### 📊 Différences avec le Modèle Star Schema
| Aspect | Star Schema (load_dwh_star) | OLAP (load_dwh_olap) |
|--------|----------------------------|----------------------|
| **Schema** | `ecommerce_dwh_star` | `ecommerce_dwh` |
| **Clés temporelles** | INT (YYYYMMDD, HHMMSS) | DATE et TIME natifs |
| **Performance** | Optimisé pour stockage | Optimisé pour requêtes |
| **Requêtes** | Jointures sur INT | Fonctions temporelles natives |
| **Index** | Clés surrogates | Types natifs + index composites |

### 🗄️ Tables OLAP Créées

#### 📅 **dim_date** - Dimension Temporelle (Date)
| Colonne | Type | Description |
|---------|------|-------------|
| `date_key` | DATE (PK) | Date native PostgreSQL |
| `day` | SMALLINT | Jour du mois (1-31) |
| `month` | SMALLINT | Mois (1-12) |
| `quarter` | SMALLINT | Trimestre (1-4) |
| `year` | SMALLINT | Année |
| `day_of_week` | VARCHAR(10) | Nom du jour |

#### ⏰ **dim_time** - Dimension Temporelle (Heure)
| Colonne | Type | Description |
|---------|------|-------------|
| `time_key` | TIME (PK) | Heure native PostgreSQL |
| `hour` | SMALLINT | Heure (0-23) |
| `minute` | SMALLINT | Minute (0-59) |
| `second` | SMALLINT | Seconde (0-59) |
| `am_pm` | VARCHAR(2) | AM/PM |

#### 👥 **dim_customer** - Dimension Client
| Colonne | Type | Description |
|---------|------|-------------|
| `customer_key` | SERIAL (PK) | Clé auto-incrémentée |
| `client_id` | INT (UNIQUE) | ID client original |
| `full_name` | TEXT | Nom complet (MAJUSCULES) |
| `email` | TEXT | Email (MAJUSCULES) |
| `signup_date` | DATE | Date d'inscription |

#### 📦 **dim_product** - Dimension Produit
| Colonne | Type | Description |
|---------|------|-------------|
| `product_key` | SERIAL (PK) | Clé auto-incrémentée |
| `product_id` | INT (UNIQUE) | ID produit original |
| `product_name` | TEXT | Nom produit (MAJUSCULES) |
| `category_id` | INT | ID catégorie |
| `category_name` | TEXT | Nom catégorie (MAJUSCULES) |
| `price` | NUMERIC(10,2) | Prix unitaire |

#### 💳 **dim_payment_method** - Dimension Méthode de Paiement
| Colonne | Type | Description |
|---------|------|-------------|
| `payment_method_key` | SERIAL (PK) | Clé auto-incrémentée |
| `method` | VARCHAR(50) (UNIQUE) | Méthode (MAJUSCULES) |

#### 📈 **fact_sales** - Table de Faits (Ventes)
| Colonne | Type | Description |
|---------|------|-------------|
| `sale_key` | SERIAL (PK) | Clé auto-incrémentée |
| `sale_id` | INT (UNIQUE) | ID vente original |
| `date_key` | DATE (FK) | Référence dim_date |
| `time_key` | TIME (FK) | Référence dim_time |
| `product_key` | INT (FK) | Référence dim_product |
| `customer_key` | INT (FK) | Référence dim_customer |
| `quantity` | INT | Quantité vendue |
| `total_amount` | NUMERIC(10,2) | Montant total |
| `payment_method_key` | INT (FK) | Référence dim_payment_method |

---

## 🔄 Flux d'Exécution

### 1. **create_dwh_olap_schema_and_tables** (30s)
- Crée le schéma `ecommerce_dwh`
- Supprime et recrée toutes les tables OLAP
- Utilise des types natifs (DATE, TIME, SERIAL)
- Ajoute les contraintes de clés étrangères
- Crée les index optimisés pour OLAP

### 2. **create_dwh_olap_procedures** (10s)
- Crée la fonction `parse_datetime()` pour gérer les formats de date
- Crée toutes les procédures stockées de chargement OLAP
- Crée la procédure `truncate_all_tables()` pour le nettoyage
- Crée l'orchestrateur `etl_olap_master()`

### 3. **truncate_dwh_olap_tables** (10s)
- Vide toutes les tables dans l'ordre correct
- Remet à zéro les séquences SERIAL
- Prépare pour un chargement complet

### 4. **Chargement des Dimensions** (Parallèle - 1-2 min)
- `load_olap_dim_date` : Extrait toutes les dates avec types natifs
- `load_olap_dim_time` : Extrait toutes les heures avec types natifs
- `load_olap_dim_customer` : Transforme et charge les clients
- `load_olap_dim_product` : Joint produits et catégories
- `load_olap_dim_payment_method` : Charge les méthodes de paiement

### 5. **load_olap_fact_sales** (1 min)
- Joint toutes les dimensions avec les ventes RAW
- Utilise des types DATE et TIME natifs
- Résout les clés auto-incrémentées des dimensions
- Charge la table de faits

### 6. **validate_dwh_olap_data** (30s)
- Compte les enregistrements par table
- Vérifie l'intégrité référentielle
- Calcule les statistiques business
- Génère un rapport de validation OLAP

### 7. **cleanup_old_olap_reports** (5s)
- Nettoie les anciens rapports OLAP
- Conserve les 10 derniers

---

## ⚙️ Configuration

### 📅 **Planification**
- **Fréquence** : Quotidien à 4h du matin
- **Après** : `load_dwh_star` (3h) pour comparaison des modèles
- **Statut** : ✅ **ACTIF**
- **Retries** : 2 tentatives avec 5 minutes d'intervalle

### 🔗 **Connexions Requises**
- **postgres_raw_conn** : Connexion PostgreSQL (RAW + DWH)

### 🔄 **Transformations OLAP Spécifiques**

#### Types de Données Natifs
- **date_key** : DATE PostgreSQL (au lieu d'INT)
- **time_key** : TIME PostgreSQL (au lieu d'INT)
- **Clés surrogates** : SERIAL auto-incrémenté

#### Optimisations OLAP
- **ON CONFLICT DO NOTHING** : Évite les doublons
- **Index composites** : `(date_key, product_key)` pour requêtes fréquentes
- **Contraintes FK** : Intégrité référentielle complète

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
5. ✅ `load_dwh_star` (modèle étoile)
6. 🆕 **`load_dwh_olap`** ← **Ce DAG OLAP**

### 🖱️ **Exécution Manuelle**
1. **Accédez à** : http://localhost:8090
2. **Connectez-vous** : airflow/airflow
3. **Cliquez sur** : `load_dwh_olap`
4. **Cliquez sur** : "Trigger DAG" ▶️
5. **Durée attendue** : ~4-5 minutes

---

## 📈 Résultats Attendus

### 📊 **Données Transformées OLAP**
```
📋 STATISTIQUES ATTENDUES:
  • dim_date: ~10-15 dates (type DATE)
  • dim_time: ~10-15 heures (type TIME)
  • dim_customer: 6 clients (SERIAL)
  • dim_product: 6 produits (SERIAL)
  • dim_payment_method: 3-4 méthodes (SERIAL)
  • fact_sales: 10+ ventes (FK natives)

📈 STATISTIQUES BUSINESS:
  • Montant total des ventes: ~500-1000 €
  • Montant moyen par vente: ~50-100 €
  • Clients uniques: 6
  • Produits vendus: 6
  • Période: Dates complètes
  • Plage horaire: Heures complètes
```

### 📄 **Rapport OLAP Généré**
- **Localisation** : `/opt/airflow/resource/dwh_olap_validation_report_*.txt`
- **Contenu** : Statistiques OLAP, validation, métriques optimisées

---

## 🔍 Vérification des Résultats

### Via pgAdmin
1. **URL** : http://localhost:8082
2. **Login** : admin@example.com / admin
3. **Base** : ecommerce_raw_db
4. **Schema** : `ecommerce_dwh` (OLAP)

### Requêtes OLAP Optimisées
```sql
-- Vue d'ensemble OLAP
SELECT 
  'dim_date' as table_name, COUNT(*) as records FROM ecommerce_dwh.dim_date
UNION ALL
SELECT 'dim_time', COUNT(*) FROM ecommerce_dwh.dim_time
UNION ALL
SELECT 'dim_customer', COUNT(*) FROM ecommerce_dwh.dim_customer
UNION ALL
SELECT 'dim_product', COUNT(*) FROM ecommerce_dwh.dim_product
UNION ALL
SELECT 'dim_payment_method', COUNT(*) FROM ecommerce_dwh.dim_payment_method
UNION ALL
SELECT 'fact_sales', COUNT(*) FROM ecommerce_dwh.fact_sales;

-- Analyse temporelle native (avantage OLAP)
SELECT 
  EXTRACT(HOUR FROM f.time_key) as heure,
  COUNT(*) as nb_ventes,
  SUM(f.total_amount) as ca_heure
FROM ecommerce_dwh.fact_sales f
GROUP BY EXTRACT(HOUR FROM f.time_key)
ORDER BY heure;

-- Ventes par jour de la semaine (optimisé)
SELECT 
  d.day_of_week,
  COUNT(*) as nb_ventes,
  AVG(f.total_amount) as panier_moyen
FROM ecommerce_dwh.fact_sales f
JOIN ecommerce_dwh.dim_date d ON f.date_key = d.date_key
GROUP BY d.day_of_week
ORDER BY nb_ventes DESC;

-- Analyse par période (fonctions DATE natives)
SELECT 
  DATE_TRUNC('week', f.date_key) as semaine,
  COUNT(*) as ventes_semaine,
  SUM(f.total_amount) as ca_semaine
FROM ecommerce_dwh.fact_sales f
GROUP BY DATE_TRUNC('week', f.date_key)
ORDER BY semaine;

-- Top produits par tranche horaire
SELECT 
  CASE 
    WHEN EXTRACT(HOUR FROM f.time_key) BETWEEN 6 AND 11 THEN 'Matin'
    WHEN EXTRACT(HOUR FROM f.time_key) BETWEEN 12 AND 17 THEN 'Après-midi'
    WHEN EXTRACT(HOUR FROM f.time_key) BETWEEN 18 AND 22 THEN 'Soirée'
    ELSE 'Nuit'
  END as tranche,
  p.product_name,
  COUNT(*) as nb_ventes
FROM ecommerce_dwh.fact_sales f
JOIN ecommerce_dwh.dim_product p ON f.product_key = p.product_key
GROUP BY 1, p.product_name
ORDER BY tranche, nb_ventes DESC;
```

---

## 🛠️ Avantages du Modèle OLAP

### 🚀 **Performance**
- **Types natifs** : DATE/TIME plus rapides que INT
- **Fonctions temporelles** : `EXTRACT()`, `DATE_TRUNC()` optimisées
- **Index composites** : Requêtes multi-dimensionnelles rapides
- **SERIAL** : Clés auto-incrémentées efficaces

### 📊 **Requêtes Analytiques**
- **Agrégations temporelles** : Par heure, jour, semaine, mois
- **Fonctions fenêtre** : `ROW_NUMBER()`, `RANK()`, `LAG()`
- **Analyses de cohorte** : Rétention, évolution
- **Time series** : Tendances, saisonnalité

### 🔍 **Cas d'Usage OLAP**
```sql
-- Évolution mensuelle du CA
SELECT 
  DATE_TRUNC('month', date_key) as mois,
  SUM(total_amount) as ca_mensuel,
  LAG(SUM(total_amount)) OVER (ORDER BY DATE_TRUNC('month', date_key)) as ca_mois_precedent
FROM ecommerce_dwh.fact_sales
GROUP BY DATE_TRUNC('month', date_key)
ORDER BY mois;

-- Analyse de cohorte par mois d'inscription
SELECT 
  DATE_TRUNC('month', c.signup_date) as cohorte,
  COUNT(DISTINCT f.customer_key) as clients_actifs,
  SUM(f.total_amount) as ca_cohorte
FROM ecommerce_dwh.fact_sales f
JOIN ecommerce_dwh.dim_customer c ON f.customer_key = c.customer_key
GROUP BY DATE_TRUNC('month', c.signup_date)
ORDER BY cohorte;

-- Analyse des ventes par heure avec moyenne mobile
SELECT 
  time_key,
  COUNT(*) as ventes,
  AVG(COUNT(*)) OVER (
    ORDER BY time_key 
    ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING
  ) as moyenne_mobile
FROM ecommerce_dwh.fact_sales
GROUP BY time_key
ORDER BY time_key;
```

---

## 🔧 Comparaison des Modèles

### 📊 **Star Schema vs OLAP**
| Critère | Star Schema | OLAP |
|---------|-------------|------|
| **Stockage** | Plus compact (INT) | Plus expressif (DATE/TIME) |
| **Requêtes simples** | Rapide | Très rapide |
| **Requêtes temporelles** | Conversion nécessaire | Natif |
| **Fonctions analytiques** | Limitées | Complètes |
| **Maintenance** | Simple | Optimisée |
| **BI Tools** | Compatible | Optimisé |

### 🎯 **Quand Utiliser Chaque Modèle**

#### **Star Schema** (`load_dwh_star`)
- **Stockage** : Volumes très importants
- **Reporting** : Tableaux de bord simples
- **Performance** : Jointures rapides sur INT
- **Compatibilité** : Outils BI basiques

#### **OLAP** (`load_dwh_olap`)
- **Analytics** : Analyses temporelles complexes
- **Performance** : Requêtes analytiques
- **Fonctionnalités** : Fonctions PostgreSQL avancées
- **BI moderne** : Tableau, Power BI, Looker

---

## 🎯 Prochaines Étapes

### Après l'Exécution Réussie
1. **Comparez** les deux modèles (Star vs OLAP)
2. **Testez** les requêtes analytiques avancées
3. **Mesurez** les performances sur vos cas d'usage
4. **Choisissez** le modèle optimal pour votre contexte

### Extensions OLAP Possibles
- **Partitionnement** : Par date pour gros volumes
- **Matérialized Views** : Agrégats précalculés
- **Cube OLAP** : Dimensions multiples
- **Time series** : Données temporelles avancées

---

## 📚 Ressources

### Documentation
- **DDL_DWH_OLAP.sql** : Structure OLAP
- **PROCEDURE.SQL** : Procédures OLAP
- **README-LOAD-DWH-STAR.md** : Comparaison avec Star Schema

### Outils Compatibles
- **pgAdmin** : http://localhost:8082 → Schema `ecommerce_dwh`
- **Grafana** : Dashboards temps réel
- **Jupyter** : Analyses Python avancées
- **Tableau/Power BI** : Connexion PostgreSQL optimisée

---

**Version** : 1.0  
**Auteur** : Data Team  
**Dernière mise à jour** : Janvier 2025  
**Statut** : ✅ Opérationnel  
**Modèle** : OLAP Optimisé (Types Natifs)