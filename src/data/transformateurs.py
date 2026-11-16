"""
transformateurs.py : transformations réutilisables (notebooks, modèles, application).

Deux familles de fonctions :

1. Des transformations LIGNE PAR LIGNE, qui n'apprennent rien des données :
   remplacer une valeur impossible par NaN, regrouper des libellés en familles.
   Elles peuvent s'appliquer avant le découpage train/test sans fuite de données.

2. Un constructeur de préprocesseur scikit-learn (imputation, encodage,
   standardisation) qui, lui, APPREND des données : il doit être ajusté sur le
   jeu d'entraînement uniquement, puis seulement appliqué au test et, plus tard,
   aux saisies de l'application.

Ces fonctions vivent dans un fichier importable (et pas dans un notebook) : un
pipeline enregistré avec joblib ne garde qu'une référence vers elles.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    FunctionTransformer,
    OneHotEncoder,
    OrdinalEncoder,
    StandardScaler,
)

from src.utilis import config

# ---------------------------------------------------------------------------
# 1. Plausibilité des valeurs (règles de bon sens, à justifier dans le rapport)
#    Une valeur impossible est remplacée par NaN : la ligne est conservée et la
#    valeur sera imputée plus tard, avec la médiane du jeu d'entraînement.
# ---------------------------------------------------------------------------
ANNEE_MAX_PLAUSIBLE = 2030   # construction future (neuf en cours) tolérée jusque-là
HAUTEUR_MIN, HAUTEUR_MAX = 1.8, 5.0     # mètres
NIVEAUX_MAX = 15


def appliquer_plausibilite(df):
    """Convertit les variables numériques candidates en nombres puis remplace par NaN les valeurs impossibles.

    Retourne (tableau, nombre de valeurs impossibles remplacées par colonne).
    """
    d = df.copy()
    regles = {
        "surface_habitable_logement": lambda s: s <= 0,
        "hauteur_sous_plafond": lambda s: (s < HAUTEUR_MIN) | (s > HAUTEUR_MAX),
        "annee_construction": lambda s: (s < 1700) | (s > ANNEE_MAX_PLAUSIBLE),
        "nombre_niveau_logement": lambda s: (s < 1) | (s > NIVEAUX_MAX),
        "nombre_niveau_immeuble": lambda s: (s < 1) | (s > 60),
        "nombre_appartement": lambda s: (s < 1) | (s > 2000),
        "surface_habitable_immeuble": lambda s: s <= 0,
        "numero_etage_appartement": lambda s: (s < -5) | (s > 60),
    }
    for colonne in set(config.VARIABLES_CANDIDATES_NUMERIQUES) | set(regles):
        if colonne in d.columns:
            d[colonne] = pd.to_numeric(d[colonne], errors="coerce")   # texte -> NaN

    compte = {}
    for colonne, invalide in regles.items():
        if colonne in d.columns:
            masque = invalide(d[colonne]).fillna(False)
            compte[colonne] = int(masque.sum())
            d.loc[masque, colonne] = np.nan
    return d, compte


# ---------------------------------------------------------------------------
# 2. Regroupement de modalités : beaucoup de libellés très détaillés (38 types de
#    ventilation, dont 26 portés par moins de 1 % des logements) -> quelques familles.
# ---------------------------------------------------------------------------
def _minuscules(serie):
    """Texte en minuscules, valeurs absentes conservées (NaN)."""
    s = serie.astype(object)
    return s.where(s.notna(), np.nan).map(lambda v: v.lower() if isinstance(v, str) else np.nan)


def _regrouper(serie, regles, defaut="autre"):
    """Associe chaque texte à la première famille dont le motif correspond."""
    texte = _minuscules(serie)
    resultat = pd.Series(defaut, index=serie.index, dtype=object)
    resultat[texte.isna()] = np.nan
    deja = pd.Series(False, index=serie.index)
    for famille, motif in regles:
        trouve = texte.fillna("").str.contains(motif, regex=True) & ~deja
        resultat[trouve] = famille
        deja |= trouve
    return resultat


REGLES_VENTILATION = [
    ("vmc_double_flux", r"double flux|vmc df"),
    ("vmc_hygro", r"hygro"),
    ("vmc_autoreglable", r"auto.?réglable|autoréglable"),
    ("naturelle", r"naturelle"),
    ("fenetres", r"fenêtres|fenetres"),
    ("entrees_air", r"entrées d.air|entrees d.air"),
    ("vmc_autre", r"vmc|mécanique|mecanique"),
]

REGLES_ENERGIE = [
    ("electricite", r"électricité|electricite"),
    ("gaz_naturel", r"gaz naturel"),
    ("gpl", r"gpl|propane|butane"),
    ("fioul", r"fioul"),
    ("bois", r"bois"),
    ("reseau_chaleur", r"réseau|reseau"),
    ("charbon", r"charbon"),
]


def regrouper_ventilation(serie):
    """Libellés de ventilation -> quelques familles."""
    return _regrouper(serie, REGLES_VENTILATION)


def regrouper_energie(serie):
    """Libellés d'énergie (chauffage ou eau chaude) -> quelques familles."""
    return _regrouper(serie, REGLES_ENERGIE)


VARIABLES_CREEES_NUMERIQUES = []
VARIABLES_CREEES_CATEGORIELLES = [
    "famille_ventilation",
    "famille_energie_chauffage",
    "famille_energie_ecs",
]


def ajouter_variables(df):
    """Ajoute les familles de modalités et rend lisible l'indicateur « traversant ».

    Ne dépend que des colonnes de la ligne : aucune fuite de données possible.
    """
    d = df.copy()
    if "type_ventilation" in d.columns:
        d["famille_ventilation"] = regrouper_ventilation(d["type_ventilation"])
    if "type_energie_principale_chauffage" in d.columns:
        d["famille_energie_chauffage"] = regrouper_energie(d["type_energie_principale_chauffage"])
    if "type_energie_principale_ecs" in d.columns:
        d["famille_energie_ecs"] = regrouper_energie(d["type_energie_principale_ecs"])
    if "logement_traversant" in d.columns:   # 1/0 stockés en nombres -> oui/non
        d["logement_traversant"] = (
            pd.to_numeric(d["logement_traversant"], errors="coerce").map({1.0: "oui", 0.0: "non"})
        )
    return d


# ---------------------------------------------------------------------------
# 3. Préprocesseur scikit-learn (APPREND : à ajuster sur le train uniquement)
# ---------------------------------------------------------------------------
def _vers_objet(X):
    """Convertit chaque valeur en texte (les absentes restent NaN).

    Les encodeurs refusent les colonnes qui mélangent nombres, booléens et texte
    (par exemple 1.0 / True / « inconnu » après l'imputation) : on uniformise.
    """
    X = pd.DataFrame(X)
    return X.apply(lambda col: col.map(lambda v: np.nan if pd.isna(v) else str(v))).astype(object)


def construire_preprocesseur(variables_numeriques, variables_categorielles, pour="arbres"):
    """Retourne un ColumnTransformer non ajusté.

    pour="arbres"   : imputation + encodage ordinal (forêts, boosting : pas de standardisation).
    pour="lineaire" : imputation + standardisation + one-hot (régressions, KNN, SVM...).
    Les valeurs manquantes sont remplacées par la médiane (nombres) ou « inconnu »
    (texte). Les modalités vues pour la première fois sont codées -1 (ordinal) ou
    regroupées avec les modalités rares, moins de 1 % (one-hot).
    """
    cat_commun = [
        ("objet", FunctionTransformer(_vers_objet, feature_names_out="one-to-one")),
        ("imputation", SimpleImputer(strategy="constant", fill_value="inconnu")),
    ]
    if pour == "lineaire":
        pipe_num = Pipeline([
            ("imputation", SimpleImputer(strategy="median", add_indicator=True)),
            ("standardisation", StandardScaler()),
        ])
        pipe_cat = Pipeline(cat_commun + [
            ("encodage", OneHotEncoder(handle_unknown="infrequent_if_exist",
                                       min_frequency=0.01, sparse_output=False)),
        ])
    elif pour == "arbres":
        pipe_num = SimpleImputer(strategy="median", add_indicator=True)
        pipe_cat = Pipeline(cat_commun + [
            ("encodage", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
        ])
    else:
        raise ValueError("pour doit valoir « arbres » ou « lineaire ».")

    return ColumnTransformer(
        [("num", pipe_num, list(variables_numeriques)),
         ("cat", pipe_cat, list(variables_categorielles))],
        verbose_feature_names_out=False,
    )
