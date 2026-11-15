"""Tests des transformations (à lancer depuis la racine : python -m pytest tests)."""
import numpy as np
import pandas as pd

from src.data import transformateurs as tf


def test_plausibilite_remplace_les_valeurs_impossibles():
    df = pd.DataFrame({
        "surface_habitable_logement": [50, 0, 80],
        "hauteur_sous_plafond": [2.5, 307.7, 1.0],
        "annee_construction": [1990, 1300, 2050],
        "nombre_niveau_logement": [1, 71, 3],
    })
    sortie, compte = tf.appliquer_plausibilite(df)
    assert sortie["surface_habitable_logement"].isna().tolist() == [False, True, False]
    assert sortie["hauteur_sous_plafond"].isna().tolist() == [False, True, True]
    assert sortie["annee_construction"].isna().tolist() == [False, True, True]
    assert sortie["nombre_niveau_logement"].isna().tolist() == [False, True, False]
    assert compte["hauteur_sous_plafond"] == 2


def test_regroupement_ventilation():
    s = pd.Series([
        "Ventilation par ouverture des fenêtres", "VMC SF Hygro B après 2012",
        "VMC SF Auto réglable de 1982 à 2000", "Ventilation naturelle par conduit",
        "Ventilation par entrées d'air hautes et basses", "VMC double flux avec échangeur",
        "Ventilation mécanique sur conduit existant avant 2013", "Système inconnu", np.nan,
    ])
    attendu = ["fenetres", "vmc_hygro", "vmc_autoreglable", "naturelle", "entrees_air",
               "vmc_double_flux", "vmc_autre", "autre"]
    sortie = tf.regrouper_ventilation(s)
    assert sortie.iloc[:8].tolist() == attendu
    assert pd.isna(sortie.iloc[8])


def test_regroupement_energie():
    s = pd.Series(["Électricité", "Gaz naturel", "GPL", "Propane", "Fioul domestique",
                   "Bois – Bûches", "Réseau de Chauffage urbain", "Non affecté",
                   "Électricité d'origine renouvelable utilisée dans le bâtiment"])
    attendu = ["electricite", "gaz_naturel", "gpl", "gpl", "fioul", "bois",
               "reseau_chaleur", "autre", "electricite"]
    assert tf.regrouper_energie(s).tolist() == attendu


def test_ajouter_variables_cree_les_familles():
    df = pd.DataFrame({
        "type_ventilation": ["VMC SF Hygro A après 2012"],
        "type_energie_principale_chauffage": ["Électricité"],
        "type_energie_principale_ecs": ["Gaz naturel"],
        "logement_traversant": [1.0],
    })
    sortie = tf.ajouter_variables(df)
    for colonne in tf.VARIABLES_CREEES_CATEGORIELLES:
        assert colonne in sortie.columns
    assert sortie["famille_ventilation"].iloc[0] == "vmc_hygro"
    assert sortie["famille_energie_ecs"].iloc[0] == "gaz_naturel"
    assert sortie["logement_traversant"].iloc[0] == "oui"


def test_preprocesseur_ne_laisse_aucune_valeur_manquante():
    train = pd.DataFrame({"x": [1.0, np.nan, 3.0, 4.0], "c": ["a", "b", np.nan, "a"]})
    test = pd.DataFrame({"x": [np.nan, 2.0], "c": ["z", "a"]})   # « z » jamais vue au train
    for mode in ("arbres", "lineaire"):
        prep = tf.construire_preprocesseur(["x"], ["c"], pour=mode)
        prep.fit(train)
        assert not np.isnan(np.asarray(prep.transform(train), dtype=float)).any()
        assert not np.isnan(np.asarray(prep.transform(test), dtype=float)).any()
