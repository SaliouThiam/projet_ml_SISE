"""Tests du rattachement météo (python -m pytest tests)."""
import numpy as np
import pandas as pd
import pytest

from src.data import enrichissement_meteo as meteo


def _table():
    return pd.DataFrame({
        "cle": ["2B|bastia", "2A|ajaccio", "2B|lilerousse"],
        "temperature_moyenne_c": [15.5, 15.8, 15.1],
        "precipitation_annuelle_mm": [700.0, 650.0, 600.0],
    })


def test_cle_normalise_accents_et_ponctuation():
    cle = meteo.creer_cle(pd.Series(["2b", "2A"]), pd.Series(["Bastia", "Ajaccio"]))
    assert cle.tolist() == ["2B|bastia", "2A|ajaccio"]


def test_cle_corrige_les_ecritures_deformees_de_l_ile_rousse():
    cle = meteo.creer_cle(pd.Series(["2B", "2B"]), pd.Series(["L'Île-Rousse", "L'Ã le-Rousse"]))
    assert cle.tolist()[0] == "2B|lilerousse"
    assert cle.tolist()[1] == "2B|lilerousse"


def test_ajouter_meteo_conserve_ordre_et_nombre_de_lignes():
    df = pd.DataFrame({"code_departement_ban": ["2A", "2B", "2B"],
                       "nom_commune_ban": ["Ajaccio", "Bastia", "Bastia"], "x": [1, 2, 3]})
    sortie = meteo.ajouter_meteo(df, table=_table())
    assert len(sortie) == 3 and sortie["x"].tolist() == [1, 2, 3]
    assert sortie["temperature_moyenne_c"].tolist() == [15.8, 15.5, 15.5]


def test_commune_inconnue_selon_exiger_complet():
    df = pd.DataFrame({"code_departement_ban": ["2B"], "nom_commune_ban": ["Inconnue"]})
    with pytest.raises(ValueError):
        meteo.ajouter_meteo(df, table=_table())
    sortie = meteo.ajouter_meteo(df, table=_table(), exiger_complet=False)
    assert np.isnan(sortie["temperature_moyenne_c"].iloc[0])
