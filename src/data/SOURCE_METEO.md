# Source OpenData - Données météo Corse

## 1. Provenance des données

Jeu de données :
Normales climatiques mensuelles 1991-2020 par commune (France)

Producteur : Weatheo (by CODELIO)

Source :
https://www.data.gouv.fr/datasets/normales-climatiques-mensuelles-1991-2020-par-commune-france

Licence des données : CC BY 4.0

Données issues des réanalyses climatiques Copernicus ERA5-Land.

## 2. Téléchargement

Télécharger le fichier :

fr_climate_normals_1991_2020.csv

Le placer dans :

src/data/raw/fr_climate_normals_1991_2020.csv

Les données brutes ne sont pas enregistrées sur GitHub.

## 3. Préparation des données

Depuis la racine du projet, exécuter :

python src/data/preparer_meteo_corse.py

Ce script prépare les normales climatiques des
360 communes corses.

Résultat :

src/data/processed/meteo_corse_communes.csv

## 4. Enrichissement des données DPE

Prérequis :
- src/data/processed/train.csv
- src/data/processed/test.csv

Exécuter :

python src/data/enrichissement_meteo.py

Résultats :

src/data/processed/train_meteo.csv
src/data/processed/test_meteo.csv

Deux variables sont ajoutées :
- temperature_moyenne_c
- precipitation_annuelle_mm

Les scripts ne remplacent pas les fichiers de sortie
existants sans vérification.

## 5. Limites des données

Les valeurs météorologiques représentent des
normales climatiques sur la période 1991-2020.

Elles sont associées aux communes et non directement
mesurées dans chaque logement.

Leur contribution aux performances de prédiction
DPE reste à confirmer.