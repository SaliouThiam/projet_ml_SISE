"""
predict.py : prédiction de l'étiquette DPE et de la consommation d'énergie.

Ce module regroupe tout ce qui touche à la prédiction, sans rien savoir de l'interface :
l'application Dash l'appelle, et il se teste sans la lancer.

Ce qu'il fait :
  - charge les modèles enregistrés par les notebooks 03 (classification) et 04 (régression) ;
  - transforme une saisie (dictionnaire variable -> valeur) en ligne au format attendu ;
  - renvoie l'étiquette, ses probabilités, la consommation estimée avec une fourchette ;
  - explique l'estimation par rapport à un logement de référence.

Les informations du formulaire (valeurs possibles, valeurs de référence, erreurs typiques)
sont lues dans app/data/formulaire.json, produit par scripts/preparer_donnees_app.py.
"""

import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.utilis import config
from src.utilis import regles_dpe

RACINE_DEPOT = Path(__file__).resolve().parents[2]            # dossier contenant src/ et app/
FICHIER_FORMULAIRE = RACINE_DEPOT / "app" / "data" / "formulaire.json"
FICHIER_CLASSIFICATION = "modele_classification.joblib"
FICHIERS_REGRESSION = ("modele_regression.joblib", "modele_regression_consommation.joblib")


class PredicteurIndisponible(RuntimeError):
    """Les modèles ou le fichier du formulaire sont introuvables."""


def _nombre(valeur):
    """Convertit une saisie en nombre ; vide ou invalide -> valeur manquante."""
    if valeur is None or (isinstance(valeur, str) and not valeur.strip()):
        return np.nan
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return np.nan


def _texte(valeur):
    """Convertit une saisie en texte ; vide -> valeur manquante."""
    if valeur is None or (isinstance(valeur, float) and np.isnan(valeur)):
        return np.nan
    texte = str(valeur).strip()
    return texte if texte else np.nan


class Predicteur:
    """Charge les modèles une fois et répond aux demandes de prédiction."""

    def __init__(self, dossier_modeles=None, fichier_formulaire=None):
        dossier = Path(dossier_modeles) if dossier_modeles else config.DOSSIER_MODELES
        fichier_formulaire = Path(fichier_formulaire) if fichier_formulaire else FICHIER_FORMULAIRE

        chemin_cls = dossier / FICHIER_CLASSIFICATION
        chemin_reg = next((dossier / n for n in FICHIERS_REGRESSION if (dossier / n).exists()), None)
        manquants = [str(p) for p in (chemin_cls, fichier_formulaire) if not p.exists()]
        if chemin_reg is None:
            manquants.append(str(dossier / FICHIERS_REGRESSION[0]))
        if manquants:
            raise PredicteurIndisponible(
                "Fichiers introuvables : " + ", ".join(manquants) +
                ". Exécuter les notebooks 03 et 04, puis scripts/preparer_donnees_app.py."
            )

        self.modele_cls = joblib.load(chemin_cls)
        self.modele_reg = joblib.load(chemin_reg)
        with open(fichier_formulaire, encoding="utf-8") as f:
            self.formulaire = json.load(f)

        self.variables_cls = list(self.modele_cls.feature_names_in_)
        self.variables_reg = list(self.modele_reg.feature_names_in_)
        # Ordre d'affichage : variables de la régression, puis celles propres à la classification.
        self.variables = self.variables_reg + [v for v in self.variables_cls if v not in self.variables_reg]
        self.numeriques = set(self.formulaire["numeriques"])
        self.classes = list(self.modele_cls.classes_)

    # ------------------------------------------------------------------ saisie
    def _ligne(self, saisie, variables):
        """Une ligne de données au format attendu par un pipeline (colonnes dans l'ordre appris)."""
        valeurs = {}
        for variable in variables:
            brute = saisie.get(variable)
            valeurs[variable] = _nombre(brute) if variable in self.numeriques else _texte(brute)
        ligne = pd.DataFrame([valeurs], columns=variables)
        for variable in variables:
            if variable in self.numeriques:
                ligne[variable] = ligne[variable].astype(float)
            else:
                ligne[variable] = ligne[variable].astype(object)
        return ligne

    # -------------------------------------------------------------- prédiction
    def predire(self, saisie):
        """Estime l'étiquette et la consommation d'un logement décrit par `saisie`.

        Retourne un dictionnaire :
          etiquette, probabilites (A à G), consommation (kWhEP/m²/an), fourchette (bas, haut),
          etiquette_consommation (déduite des seuils officiels), coherent (les deux étiquettes concordent).
        """
        proba = self.modele_cls.predict_proba(self._ligne(saisie, self.variables_cls))[0]
        probabilites = {c: float(p) for c, p in zip(self.classes, proba)}
        etiquette = max(probabilites, key=probabilites.get)

        consommation = float(max(0.0, self.modele_reg.predict(self._ligne(saisie, self.variables_reg))[0]))
        erreurs = self.formulaire.get("erreurs") or {}
        marge = erreurs.get("p80")
        fourchette = (max(0.0, consommation - marge), consommation + marge) if marge else None

        etiquette_conso = str(regles_dpe.etiquette_energie(pd.Series([consommation])).iloc[0])
        return {
            "etiquette": etiquette,
            "probabilites": probabilites,
            "consommation": consommation,
            "fourchette": fourchette,
            "etiquette_consommation": etiquette_conso,
            "coherent": etiquette_conso == etiquette,
        }

    # ------------------------------------------------------------- explication
    def expliquer(self, saisie, n=6):
        """Contribution de chaque variable renseignée à la consommation estimée.

        On remplace une variable à la fois par sa valeur de référence (médiane ou modalité la plus
        fréquente) et on mesure la variation de la prédiction. Contribution positive : la valeur
        saisie augmente la consommation par rapport à la référence. Approximation qui ignore
        les interactions entre variables.
        """
        reference = self.formulaire["reference"]
        ligne = self._ligne(saisie, self.variables_reg)
        base = float(self.modele_reg.predict(ligne)[0])

        lignes = []
        for variable in self.variables_reg:
            valeur = ligne[variable].iloc[0]
            if pd.isna(valeur) or variable not in reference:
                continue                                     # variable non renseignée : pas d'explication
            modifiee = ligne.copy()
            modifiee[variable] = reference[variable] if variable not in self.numeriques else float(reference[variable])
            lignes.append({"variable": variable, "valeur": valeur, "reference": reference[variable],
                           "contribution": base - float(self.modele_reg.predict(modifiee)[0])})
        tableau = pd.DataFrame(lignes, columns=["variable", "valeur", "reference", "contribution"])
        if tableau.empty:
            return tableau
        ordre = tableau["contribution"].abs().sort_values(ascending=False).index
        return tableau.loc[ordre].head(n).reset_index(drop=True)


@lru_cache(maxsize=1)
def obtenir_predicteur():
    """Prédicteur partagé : les modèles ne sont chargés qu'une fois par processus."""
    return Predicteur()
