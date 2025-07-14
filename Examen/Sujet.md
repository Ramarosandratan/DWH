**Énoncé examen ETL – Session juillet 2025**

### Exercice 1

* Ajouter une colonne **region\_id** dans la table source « sales » dans **Mysql**

```
sale_id    region_id  
   1             2  
   2             1  
   3             1  
   4             2  
   5             2  
   6             2  
   7             1  
   8             3  
   9             3  
  10             1  
```

* Ramener cette nouvelle colonne dans la table **fact\_sales** sur **DWH**
* Créer un graphique montrant le montant des ventes par région

### Exercice 2

* Créer une nouvelle source des données :

```
region_id    name  
   1       Analamanga  
   2       alaotra mangoro  
   3       boeny  
```

* Faites les nécessaires pour que cette table soit ramenée dans une table dimension dans DWH, en s’assurant que le nom de chaque région s’écrive en Majuscule
* Recréer le graphique dans l’exo 1 mais en montrant cette fois-ci le nom de chaque région en place de son ID
