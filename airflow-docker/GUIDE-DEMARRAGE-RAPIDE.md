# 🚀 Guide de Démarrage Rapide - Stack E-commerce Airflow

## ✅ Étape 1 : Vérification de l'Installation

Votre stack e-commerce Airflow est maintenant **DÉMARRÉE** ! 🎉

### Services Disponibles
- **🌐 Airflow UI** : http://localhost:8090 (airflow/airflow)
- **🗄️ MySQL OLTP** : localhost:3307 (root/root_password)
- **🗄️ PostgreSQL RAW** : localhost:5435 (postgres/postgres_password)
- **🔧 phpMyAdmin** : http://localhost:8081
- **🔧 pgAdmin** : http://localhost:8082 (admin@example.com/admin)

## 📋 Étape 2 : Configuration Initiale (5 minutes)

### 2.1 Accéder à Airflow
1. Ouvrez votre navigateur
2. Allez sur : **http://localhost:8090**
3. Connectez-vous avec :
   - **Utilisateur** : `airflow`
   - **Mot de passe** : `airflow`

### 2.2 Exécuter les DAGs dans l'ordre

#### ✅ **DAG 1 : `setup_connections`** (OBLIGATOIRE - 1ère fois)
- **Objectif** : Configure les connexions aux bases de données
- **Action** : Cliquez sur le DAG → Cliquez sur "Trigger DAG" ▶️
- **Durée** : ~30 secondes
- **Statut attendu** : ✅ Success (toutes les tâches vertes)

#### ✅ **DAG 2 : `init_ecommerce_oltp`** (OBLIGATOIRE - 1ère fois)
- **Objectif** : Crée les tables et insère les données de démonstration
- **Action** : Cliquez sur le DAG → Cliquez sur "Trigger DAG" ▶️
- **Durée** : ~2 minutes
- **Statut attendu** : ✅ Success (toutes les tâches vertes)

#### ✅ **DAG 3 : `process_payment_csv`** (RECOMMANDÉ)
- **Objectif** : Traite le fichier CSV des paiements
- **Action** : Cliquez sur le DAG → Cliquez sur "Trigger DAG" ▶️
- **Durée** : ~1 minute
- **Statut attendu** : ✅ Success (toutes les tâches vertes)

#### ✅ **DAG 4 : `load_raw_data`** (NOUVEAU)
- **Objectif** : Charge les données OLTP vers PostgreSQL RAW
- **Action** : Cliquez sur le DAG → Cliquez sur "Trigger DAG" ▶️
- **Durée** : ~2 minutes
- **Statut attendu** : ✅ Success (toutes les tâches vertes)

#### ✅ **DAG 5 : `load_dwh_star`** (NOUVEAU)
- **Objectif** : Crée le Data Warehouse en étoile depuis RAW
- **Action** : Cliquez sur le DAG → Cliquez sur "Trigger DAG" ▶️
- **Durée** : ~4-5 minutes
- **Statut attendu** : ✅ Success (toutes les tâches vertes)

#### ✅ **DAG 6 : `load_dwh_olap`** (NOUVEAU)
- **Objectif** : Crée le Data Warehouse OLAP optimisé depuis RAW
- **Action** : Cliquez sur le DAG → Cliquez sur "Trigger DAG" ▶️
- **Durée** : ~4-5 minutes
- **Statut attendu** : ✅ Success (toutes les tâches vertes)

## 🎯 Étape 3 : Démonstration Complète (Optionnel)

### Option A : Démonstration Automatique
Exécutez le **DAG `demo_full_pipeline`** qui fait tout automatiquement :
- Configure les connexions
- Initialise les données
- Traite le CSV
- Charge les données RAW
- Génère un rapport complet

### Option B : Activation des DAGs Automatiques
1. **`load_raw_data`** : Activez-le pour le chargement quotidien vers RAW (1h)
2. **`load_dwh_star`** : Activez-le pour le Data Warehouse étoile (3h)
3. **`load_dwh_olap`** : Activez-le pour le Data Warehouse OLAP (4h)
4. **`process_payment_csv`** : Activez-le pour le traitement quotidien des CSV
5. **`sync_ecommerce_data`** : Activez-le pour la maintenance quotidienne (2h)

## 🔍 Étape 4 : Vérification des Résultats

### 4.1 Via Airflow UI
- Vérifiez que tous les DAGs sont en statut ✅ Success
- Consultez les logs des tâches pour plus de détails

### 4.2 Via phpMyAdmin (Base MySQL)
1. Allez sur : http://localhost:8081
2. Connectez-vous avec : `root` / `root_password`
3. Sélectionnez la base `ecommerce_ops_db`
4. Vérifiez les tables :
   - `categories` (3 enregistrements)
   - `products` (6 enregistrements)
   - `clients` (6 enregistrements)
   - `sales` (10 enregistrements)
   - `inventory` (6 enregistrements)
   - `payment_history` (10+ enregistrements)

### 4.3 Via pgAdmin (Base PostgreSQL)
1. Allez sur : http://localhost:8082
2. Connectez-vous avec : `admin@example.com` / `admin`
3. Ajoutez un serveur :
   - **Host** : `postgres_raw_db`
   - **Port** : `5432`
   - **Database** : `ecommerce_raw_db`
   - **Username** : `postgres`
   - **Password** : `postgres_password`

## 📊 Étape 5 : Surveillance et Monitoring

### Rapports Automatiques
- Les rapports de qualité sont générés dans `/opt/airflow/resource/`
- Consultez les logs Airflow pour les alertes

### Indicateurs Clés Surveillés
- ✅ Produits sans stock
- ✅ Ventes sans paiement
- ✅ Paiements échoués
- ✅ Incohérences de montants
- ✅ Produits sous seuil de réapprovisionnement

## 🛠️ Commandes Utiles

### Gestion de la Stack
```powershell
# Voir l'état des services
.\diagnose-stack.ps1

# Voir les logs en temps réel
docker-compose -f docker-compose-extended.yaml logs -f

# Redémarrer un service
docker-compose -f docker-compose-extended.yaml restart airflow-scheduler

# Arrêter la stack
.\stop-ecommerce-stack.ps1

# Redémarrer la stack
.\start-ecommerce-stack.ps1 -WithAdmin
```

### Vérification des Ports
```powershell
# Vérifier la disponibilité des ports
.\check-ports.ps1
```

## 🚨 Dépannage Rapide

### Problème : DAG en échec
1. Consultez les logs dans l'interface Airflow
2. Vérifiez que les bases de données sont accessibles
3. Redémarrez le DAG

### Problème : Connexion aux bases échouée
1. Vérifiez que les conteneurs sont en cours d'exécution
2. Re-exécutez le DAG `setup_connections`
3. Consultez les logs des conteneurs de base de données

### Problème : Interface Airflow inaccessible
1. Vérifiez que le port 8090 n'est pas utilisé par un autre service
2. Attendez 2-3 minutes après le démarrage
3. Redémarrez le conteneur `airflow-apiserver`

## 📈 Prochaines Étapes

### Développement
1. **Ajoutez vos propres DAGs** dans le dossier `dags/`
2. **Modifiez les données** dans les fichiers SQL ou CSV
3. **Personnalisez les rapports** selon vos besoins

### Production
1. **Configurez les alertes** email/Slack
2. **Ajustez les horaires** des DAGs selon vos besoins
3. **Sauvegardez régulièrement** les données

## 📞 Support

### Documentation Complète
- **README-ECOMMERCE-DAGS.md** : Documentation technique détaillée
- **Logs Airflow** : Interface web → Admin → Logs

### Diagnostic
```powershell
# Diagnostic complet
.\diagnose-stack.ps1 -Detailed
```

---

## 🎉 Félicitations !

Votre pipeline de données e-commerce est maintenant opérationnel ! 

**Prochaine action recommandée** : Accédez à http://localhost:8090 et exécutez les DAGs dans l'ordre indiqué.

---

**Version** : 1.0  
**Dernière mise à jour** : Janvier 2025  
**Support** : Consultez les logs Airflow et la documentation technique