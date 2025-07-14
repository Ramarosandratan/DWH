# 🗺️ Guide d'Intégration des Régions dans le Data Warehouse

## 🎯 Objectif

Ce guide vous accompagne pour ajouter la colonne `region_id` dans la table source MySQL et l'intégrer complètement dans le Data Warehouse avec génération de graphiques d'analyse.

---

## 📋 Étapes d'Intégration

### ✅ **Étape 1 : Préparation de la Structure**

**DAG à exécuter** : `add_region_column`

**Actions réalisées** :
- ✅ Création de la table `regions` dans MySQL
- ✅ Ajout de la colonne `region_id` à la table `sales`
- ✅ Mise à jour des données selon votre mapping
- ✅ Mise à jour des tables RAW PostgreSQL
- ✅ Mise à jour des tables DWH (Star + OLAP)
- ✅ Création des procédures stockées

**Mapping des régions** :
```
sale_id    region_id    région
   1           2         Sud
   2           1         Nord  
   3           1         Nord
   4           2         Sud
   5           2         Sud
   6           2         Sud
   7           1         Nord
   8           3         Est
   9           3         Est
  10           1         Nord
```

### ✅ **Étape 2 : Rechargement des Données**

Après l'ajout de la colonne, vous devez recharger les données :

1. **`load_raw_data`** - Recharge les données RAW avec region_id
2. **`load_dwh_star`** - Recharge le DWH Star Schema avec régions
3. **`load_dwh_olap`** - Recharge le DWH OLAP avec régions

### ✅ **Étape 3 : Génération des Graphiques**

**DAG à exécuter** : `create_region_chart`

**Graphiques générés** :
- 📊 Chiffre d'affaires par région
- 📈 Répartition des ventes par région
- 🛒 Panier moyen par région
- 📦 Quantité totale par région
- 🔄 Comparaison Star Schema vs OLAP
- 📅 Évolution temporelle par région

---

## 🚀 Ordre d'Exécution Recommandé

### **Phase 1 : Intégration Structure**
```
1. add_region_column (NOUVEAU)
   ├── create_regions_table_mysql
   ├── add_region_column_to_mysql
   ├── update_raw_tables_for_regions
   ├── update_dwh_tables_for_regions
   ├── create_region_procedures
   └── validate_region_integration
```

### **Phase 2 : Rechargement Données**
```
2. load_raw_data (MODIFIÉ)
   └── Inclut maintenant regions_raw + region_id dans sales_raw

3. load_dwh_star (MODIFIÉ)
   └── Inclut maintenant dim_region + region_key dans fact_sales

4. load_dwh_olap (MODIFIÉ)
   └── Inclut maintenant dim_region + region_key dans fact_sales
```

### **Phase 3 : Analyse et Graphiques**
```
5. create_region_chart (NOUVEAU)
   ├── create_sales_by_region_chart
   ├── create_comparative_chart
   ├── create_time_series_by_region
   └── cleanup_old_charts
```

---

## 🖱️ Exécution Manuelle

### **1. Intégration des Régions**
1. **Accédez à** : http://localhost:8090
2. **Connectez-vous** : airflow/airflow
3. **Cliquez sur** : `add_region_column`
4. **Trigger DAG** ▶️
5. **Durée** : ~2-3 minutes
6. **Vérifiez** : Toutes les tâches en vert ✅

### **2. Rechargement des Données**
```
Ordre d'exécution :
1. load_raw_data ▶️ (2-3 min)
2. load_dwh_star ▶️ (4-5 min)  
3. load_dwh_olap ▶️ (4-5 min)
```

### **3. Génération des Graphiques**
1. **Cliquez sur** : `create_region_chart`
2. **Trigger DAG** ▶️
3. **Durée** : ~1-2 minutes
4. **Résultats** : Graphiques dans `/opt/airflow/resource/`

---

## 📊 Résultats Attendus

### **Données MySQL (Source)**
```sql
-- Vérification dans MySQL
SELECT s.sale_id, s.region_id, r.region_name, s.total_amount
FROM ecommerce_ops_db.sales s
LEFT JOIN ecommerce_ops_db.regions r ON s.region_id = r.region_id
ORDER BY s.sale_id;
```

### **Données RAW PostgreSQL**
```sql
-- Vérification dans PostgreSQL RAW
SELECT sale_id, region_id FROM raw.sales_raw ORDER BY sale_id::INT;
SELECT * FROM raw.regions_raw;
```

### **Données DWH Star Schema**
```sql
-- Analyse par région - Star Schema
SELECT 
    dr.region_name,
    COUNT(*) as nb_ventes,
    SUM(f.total_amount) as ca_total,
    AVG(f.total_amount) as panier_moyen
FROM ecommerce_dwh_star.fact_sales f
JOIN ecommerce_dwh_star.dim_region dr ON f.region_key = dr.region_key
GROUP BY dr.region_key, dr.region_name
ORDER BY ca_total DESC;
```

### **Données DWH OLAP**
```sql
-- Analyse par région - OLAP
SELECT 
    dr.region_name,
    COUNT(*) as nb_ventes,
    SUM(f.total_amount) as ca_total,
    AVG(f.total_amount) as panier_moyen
FROM ecommerce_dwh.fact_sales f
JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
GROUP BY dr.region_key, dr.region_name
ORDER BY ca_total DESC;
```

### **Résultats Business Attendus**
```
📊 ANALYSE PAR RÉGION:
🗺️ Sud (2): ~40% du CA (ventes 1,4,5,6)
🗺️ Nord (1): ~35% du CA (ventes 2,3,7,10)  
🗺️ Est (3): ~25% du CA (ventes 8,9)

💰 CA TOTAL: ~500-600€
📈 VENTES TOTALES: 10
🛒 PANIER MOYEN: ~50-60€
```

---

## 📈 Graphiques Générés

### **1. Graphique Principal** (`sales_by_region_chart_*.png`)
- 💰 Chiffre d'affaires par région (Bar chart)
- 📈 Répartition des ventes (Pie chart)
- 🛒 Panier moyen par région (Bar chart)
- 📦 Quantité totale par région (Bar chart)

### **2. Graphique Comparatif** (`star_vs_olap_regions_*.png`)
- 🔄 Comparaison Star Schema vs OLAP
- 📊 Validation de la cohérence des données

### **3. Série Temporelle** (`time_series_regions_*.png`)
- 📅 Évolution du CA par région dans le temps
- 📈 Évolution du nombre de ventes par région

### **4. Rapports Textuels**
- `sales_by_region_report_*.txt` : Analyse détaillée
- `region_integration_report_*.txt` : Validation intégration

---

## 🔍 Vérification des Résultats

### **Via pgAdmin**
1. **URL** : http://localhost:8082
2. **Login** : admin@example.com / admin
3. **Base** : ecommerce_raw_db
4. **Schémas** : 
   - `raw` → `sales_raw` (colonne region_id)
   - `ecommerce_dwh_star` → `dim_region` + `fact_sales`
   - `ecommerce_dwh` → `dim_region` + `fact_sales`

### **Via phpMyAdmin**
1. **URL** : http://localhost:8081
2. **Login** : root / rootpassword
3. **Base** : ecommerce_ops_db
4. **Tables** : 
   - `sales` (colonne region_id ajoutée)
   - `regions` (table créée)

### **Fichiers Générés**
```
/opt/airflow/resource/
├── sales_by_region_chart_*.png
├── sales_by_region_report_*.txt
├── star_vs_olap_regions_*.png
├── time_series_regions_*.png
└── region_integration_report_*.txt
```

---

## 🛠️ Requêtes d'Analyse Avancées

### **Top Régions par CA**
```sql
SELECT 
    dr.region_name,
    dr.region_code,
    COUNT(*) as nb_ventes,
    SUM(f.total_amount) as ca_total,
    ROUND(AVG(f.total_amount), 2) as panier_moyen,
    ROUND((SUM(f.total_amount) / (SELECT SUM(total_amount) FROM ecommerce_dwh.fact_sales)) * 100, 1) as pourcentage_ca
FROM ecommerce_dwh.fact_sales f
JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
GROUP BY dr.region_key, dr.region_name, dr.region_code
ORDER BY ca_total DESC;
```

### **Analyse Temporelle par Région**
```sql
SELECT 
    dr.region_name,
    f.date_key,
    COUNT(*) as ventes_jour,
    SUM(f.total_amount) as ca_jour
FROM ecommerce_dwh.fact_sales f
JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
GROUP BY dr.region_key, dr.region_name, f.date_key
ORDER BY f.date_key, dr.region_name;
```

### **Performance par Région et Produit**
```sql
SELECT 
    dr.region_name,
    dp.product_name,
    COUNT(*) as nb_ventes,
    SUM(f.quantity) as quantite_totale,
    SUM(f.total_amount) as ca_produit_region
FROM ecommerce_dwh.fact_sales f
JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
JOIN ecommerce_dwh.dim_product dp ON f.product_key = dp.product_key
GROUP BY dr.region_key, dr.region_name, dp.product_key, dp.product_name
ORDER BY ca_produit_region DESC;
```

### **Analyse de Cohorte par Région**
```sql
SELECT 
    dr.region_name,
    DATE_TRUNC('month', dc.signup_date) as cohorte_mois,
    COUNT(DISTINCT f.customer_key) as clients_actifs,
    SUM(f.total_amount) as ca_cohorte
FROM ecommerce_dwh.fact_sales f
JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
JOIN ecommerce_dwh.dim_customer dc ON f.customer_key = dc.customer_key
GROUP BY dr.region_key, dr.region_name, DATE_TRUNC('month', dc.signup_date)
ORDER BY cohorte_mois, ca_cohorte DESC;
```

---

## 🎯 Cas d'Usage Business

### **1. Analyse Géographique**
- **Objectif** : Identifier les régions les plus performantes
- **KPI** : CA par région, nombre de ventes, panier moyen
- **Action** : Optimiser la logistique et le marketing

### **2. Expansion Géographique**
- **Objectif** : Décider où ouvrir de nouveaux points de vente
- **KPI** : Potentiel de croissance par région
- **Action** : Investissements ciblés

### **3. Personnalisation Marketing**
- **Objectif** : Adapter les campagnes par région
- **KPI** : Préférences produits par région
- **Action** : Campagnes géolocalisées

### **4. Optimisation Logistique**
- **Objectif** : Réduire les coûts de livraison
- **KPI** : Volume et fréquence par région
- **Action** : Optimisation des entrepôts

---

## 🔧 Dépannage

### **Problème : Colonne region_id non trouvée**
```sql
-- Vérifier la structure MySQL
DESCRIBE ecommerce_ops_db.sales;

-- Ajouter manuellement si nécessaire
ALTER TABLE ecommerce_ops_db.sales ADD COLUMN region_id INT DEFAULT 1;
```

### **Problème : Données manquantes dans DWH**
```sql
-- Vérifier les jointures
SELECT COUNT(*) FROM ecommerce_dwh.fact_sales WHERE region_key IS NULL;

-- Recharger si nécessaire
CALL ecommerce_dwh.load_dim_region();
CALL ecommerce_dwh.load_fact_sales();
```

### **Problème : Graphiques non générés**
- **Cause** : matplotlib non installé
- **Solution** : Exécuter `.\install-chart-dependencies.ps1`
- **Alternative** : Utiliser les rapports textuels

---

## 📚 Fichiers Modifiés

### **DAGs Créés**
- ✅ `add_region_column.py` - Intégration structure régions
- ✅ `create_region_chart.py` - Génération graphiques

### **DAGs Modifiés**
- ✅ `load_raw_data.py` - Ajout table regions_raw + colonne region_id
- ✅ `load_dwh_star.py` - Procédures mises à jour (automatique)
- ✅ `load_dwh_olap.py` - Procédures mises à jour (automatique)

### **Scripts Utilitaires**
- ✅ `install-chart-dependencies.ps1` - Installation matplotlib
- ✅ `GUIDE-INTEGRATION-REGIONS.md` - Ce guide

---

## 🎉 Statut Final

### ✅ **Intégration Complète Réalisée**
- **Structure** : Tables et colonnes créées
- **Données** : Mapping régions appliqué
- **Pipeline** : ETL mis à jour
- **Analyse** : Graphiques et rapports disponibles

### 🚀 **Prêt pour l'Analyse**
Votre Data Warehouse est maintenant enrichi avec la dimension géographique !

**Action immédiate** :
1. **Exécutez** : `add_region_column` ▶️
2. **Rechargez** : `load_raw_data` → `load_dwh_star` → `load_dwh_olap`
3. **Analysez** : `create_region_chart` ▶️
4. **Explorez** : Graphiques et rapports générés

---

**Version** : 1.0  
**Auteur** : Data Team  
**Date** : Janvier 2025  
**Statut** : ✅ Opérationnel