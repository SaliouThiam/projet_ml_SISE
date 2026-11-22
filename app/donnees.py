"""Chargement et filtrage des données de l'application (fichier léger app/data/logements_app.csv.gz)."""

import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

FICHIER = Path(__file__).resolve().parent / "data" / "logements_app.csv.gz"
ORDRE_ETIQUETTES = list("ABCDEFG")
SURFACE_MIN, SURFACE_MAX = 0, 300            # bornes du curseur de surface (m²)


class DonneesIntrouvables(FileNotFoundError):
    """Le fichier de données de l'application n'a pas été généré."""


@lru_cache(maxsize=1)
def charger():
    """Données des logements (lues une seule fois par processus)."""
    if not FICHIER.exists():
        raise DonneesIntrouvables(
            f"Fichier introuvable : {FICHIER}. Lancer : python scripts/preparer_donnees_app.py")
    df = pd.read_csv(FICHIER, dtype={"departement": str})
    df["etiquette"] = pd.Categorical(df["etiquette"], categories=ORDRE_ETIQUETTES, ordered=True)
    df["passoire"] = df["etiquette"].isin(["F", "G"])
    return df


def _annee_periode(periode):
    """Année approximative d'une période (« avant 1948 » < « 1948-1974 » < « après 2021 »)."""
    annees = re.findall(r"\d{4}", str(periode))
    if not annees:
        return np.inf
    annee = int(annees[0])
    t = str(periode).lower()
    return annee - 10 if t.startswith("avant") else annee + 2 if t.startswith("apr") else annee


def trier_periodes(periodes):
    """Périodes de construction dans l'ordre chronologique."""
    return sorted(set(periodes), key=_annee_periode)


def valeurs_possibles(colonne):
    """Valeurs distinctes d'une colonne, pour alimenter les listes de choix."""
    return sorted(charger()[colonne].dropna().astype(str).unique())


def filtrer(df, jeu="tous", etiquettes=None, energies=None, batiments=None, surface=None,
            departement="tous"):
    """Applique les filtres de l'interface.

    jeu: « tous », « existant » ou « neuf » ; etiquettes: liste de lettres (liste vide : aucun
    logement) ; energies et batiments: listes de choix (vide ou None : pas de filtre) ;
    surface: (min, max) en m² ; departement: « tous », « 2A » ou « 2B ».
    """
    masque = pd.Series(True, index=df.index)
    if jeu in ("existant", "neuf"):
        masque &= df["jeu"] == jeu
    if etiquettes is not None:
        masque &= df["etiquette"].isin(etiquettes)
    if energies:
        masque &= df["energie_chauffage"].isin(energies)
    if batiments:
        masque &= df["type_batiment"].isin(batiments)
    if surface and (surface[0] > SURFACE_MIN or surface[1] < SURFACE_MAX):
        masque &= df["surface"].between(surface[0], surface[1])
    if departement in ("2A", "2B"):
        masque &= df["departement"] == departement
    return df.loc[masque]


def indicateurs(df):
    """Indicateurs clés d'un ensemble de logements (None s'il est vide)."""
    if df.empty:
        return None
    return {
        "n": len(df),
        "conso_mediane": float(df["conso"].median()),
        "part_passoires": float(df["passoire"].mean()),
        "surface_mediane": float(df["surface"].median()),
        "part_electricite": float((df["energie_chauffage"] == "electricite").mean()),
    }


def agreger_communes(df):
    """Une ligne par commune : effectif, consommation médiane, part de passoires, position."""
    if df.empty:
        return pd.DataFrame(columns=["departement", "commune", "logements", "conso_mediane",
                                     "ges_median", "part_passoires", "lat", "lon"])
    communes = df.groupby(["departement", "commune"], observed=True).agg(
        logements=("conso", "size"),
        conso_mediane=("conso", "median"),
        ges_median=("ges", "median"),
        part_passoires=("passoire", "mean"),
        lat=("lat_commune", "first"),
        lon=("lon_commune", "first"),
    ).reset_index()
    communes["part_passoires"] = communes["part_passoires"] * 100
    return communes.dropna(subset=["lat", "lon"])
