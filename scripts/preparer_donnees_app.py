"""
preparer_donnees_app.py : fabrique les fichiers légers utilisés par l'application.

L'application ne lit jamais train.csv / test.csv (trop volumineux, absents de Git). Ce script
en extrait deux petits fichiers, à enregistrer dans le dépôt :

    app/data/logements_app.csv.gz   une ligne par logement, colonnes utiles aux pages
                                    Contexte, Exploration et Carte (ni adresse ni coordonnées
                                    individuelles : seule la position moyenne de la commune)
    app/data/formulaire.json        pour la page Prédiction : valeurs possibles de chaque variable,
                                    valeurs de référence, erreurs typiques du modèle

    python scripts/preparer_donnees_app.py
"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from src.utilis import config  # noqa: E402
from src.models import predict  # noqa: E402

SORTIE = RACINE / "app" / "data"
ETIQ, CONSO, GES = config.CIBLE_CLASSIFICATION, config.CIBLE_REGRESSION, config.GES_PAR_M2
MAX_MODALITES = 30      # modalités proposées au maximum pour une variable catégorielle


def charger_jeux():
    train = pd.read_csv(config.DATA_TRAITE / "train.csv", low_memory=False)
    test = pd.read_csv(config.DATA_TRAITE / "test.csv", low_memory=False)
    for d in (train, test):
        d["conso_aberrante"] = d["conso_aberrante"].astype(str).str.lower().eq("true")
    return train, test


def preparer_logements(train, test):
    """Tableau pour les pages de données : colonnes utiles seulement, sans adresse ni coordonnées."""
    df = pd.concat([train, test], ignore_index=True)
    df = df.loc[~df["conso_aberrante"]].copy()

    geo = df["_geopoint"].astype("string").str.split(",", expand=True)
    df["lat"] = pd.to_numeric(geo[0], errors="coerce") if geo.shape[1] >= 2 else np.nan
    df["lon"] = pd.to_numeric(geo[1], errors="coerce") if geo.shape[1] >= 2 else np.nan
    cle = ["code_departement_ban", "nom_commune_ban"]
    centres = df.groupby(cle)[["lat", "lon"]].median().round(4)
    df = df.join(centres, on=cle, rsuffix="_commune")

    energie = "famille_energie_chauffage" if "famille_energie_chauffage" in df.columns else "type_energie_principale_chauffage"
    sortie = pd.DataFrame({
        "etiquette": df[ETIQ],
        "conso": df[CONSO].round(1),
        "ges": df[GES].round(1),
        "surface": df["surface_habitable_logement"].round(1),
        "periode": df["periode_construction"],
        "type_batiment": df["type_batiment"],
        "energie_chauffage": df[energie],
        "isolation": df["qualite_isolation_enveloppe"] if "qualite_isolation_enveloppe" in df.columns else np.nan,
        "jeu": df["source_jeu"],
        "departement": df["code_departement_ban"].astype(str),
        "commune": df["nom_commune_ban"],
        "lat_commune": df["lat_commune"],
        "lon_commune": df["lon_commune"],
        "mois": pd.to_datetime(df["date_reception_dpe"], errors="coerce").dt.to_period("M").astype(str),
        "methode": df["methode_application_dpe"],
    })
    return sortie.loc[sortie["etiquette"].notna() & sortie["conso"].notna()].reset_index(drop=True)


def charger_modeles():
    """Modèles enregistrés (None s'ils sont absents)."""
    dossier = config.DOSSIER_MODELES
    chemin_reg = next((dossier / n for n in predict.FICHIERS_REGRESSION if (dossier / n).exists()), None)
    chemin_cls = dossier / predict.FICHIER_CLASSIFICATION
    return (joblib.load(chemin_cls) if chemin_cls.exists() else None,
            joblib.load(chemin_reg) if chemin_reg else None)


def preparer_formulaire(train, test, modele_cls, modele_reg):
    """Valeurs possibles, références et erreurs typiques pour la page Prédiction."""
    with open(config.DOSSIER_MODELES / "variables_retenues.json", encoding="utf-8") as f:
        decisions = json.load(f)
    numeriques_connues = set(decisions["variables_numeriques"])

    variables = []
    for modele in (modele_reg, modele_cls):
        if modele is not None:
            variables += [v for v in modele.feature_names_in_ if v not in variables]
    if not variables:
        variables = decisions["variables_numeriques"] + decisions["variables_categorielles"]

    base = train.loc[~train["conso_aberrante"]]
    formulaire = {"variables": variables, "numeriques": {}, "categorielles": {}, "reference": {}}
    for variable in variables:
        if variable in numeriques_connues:
            serie = pd.to_numeric(base[variable], errors="coerce").dropna()
            formulaire["numeriques"][variable] = {
                "min": float(serie.min()), "p05": float(serie.quantile(0.05)),
                "mediane": float(serie.median()), "p95": float(serie.quantile(0.95)),
                "max": float(serie.max()),
            }
            formulaire["reference"][variable] = float(serie.median())
        else:
            serie = base[variable].dropna().astype(str)
            parts = serie.value_counts(normalize=True).head(MAX_MODALITES)
            formulaire["categorielles"][variable] = [
                {"valeur": valeur, "part": float(part)} for valeur, part in parts.items()]
            formulaire["reference"][variable] = str(serie.mode().iloc[0])

    formulaire["erreurs"] = None
    if modele_reg is not None:
        test_r = test.loc[~test["conso_aberrante"]]
        vars_reg = list(modele_reg.feature_names_in_)
        erreur = np.abs(modele_reg.predict(test_r[vars_reg]) - test_r[CONSO].to_numpy())
        formulaire["erreurs"] = {"mae": float(erreur.mean()), "p80": float(np.percentile(erreur, 80))}
    formulaire["n_logements_entrainement"] = int(len(train))
    return formulaire


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    train, test = charger_jeux()

    logements = preparer_logements(train, test)
    chemin_logements = SORTIE / "logements_app.csv.gz"
    logements.to_csv(chemin_logements, index=False, compression="gzip")
    print(f"{len(logements):,} logements -> {chemin_logements.relative_to(RACINE)} "
          f"({chemin_logements.stat().st_size / 1e6:.1f} Mo)")

    modele_cls, modele_reg = charger_modeles()
    if modele_cls is None or modele_reg is None:
        print("Attention : modèle(s) introuvable(s), les erreurs typiques ne seront pas calculées.")
    formulaire = preparer_formulaire(train, test, modele_cls, modele_reg)
    chemin_formulaire = SORTIE / "formulaire.json"
    with open(chemin_formulaire, "w", encoding="utf-8") as f:
        json.dump(formulaire, f, ensure_ascii=False, indent=1)
    print(f"{len(formulaire['variables'])} variables -> {chemin_formulaire.relative_to(RACINE)}")
    if formulaire["erreurs"]:
        print(f"Erreurs typiques de la consommation : MAE {formulaire['erreurs']['mae']:.1f}, "
              f"80 % des erreurs sous {formulaire['erreurs']['p80']:.1f} kWhEP/m²/an")


if __name__ == "__main__":
    main()
