"""
regles_dpe.py : règle de calcul de l'étiquette DPE à partir des seuils.

L'étiquette découle de deux valeurs : la consommation en énergie primaire
(kWhEP/m²/an) et les émissions de GES (kg CO2/m²/an). Chacune donne une classe
de A à G, et l'étiquette finale est la plus défavorable des deux.

Les seuils viennent de config.py et restent à confirmer sur la documentation
officielle. Ce module sert à vérifier la règle sur les données (notebook
d'exploration), à l'approche « régression puis seuils » et à l'application.
"""

import numpy as np
import pandas as pd

from src.utilis import config


def _classer(valeurs, seuils):
    """Classe chaque valeur de A à G selon les bornes hautes incluses (valeur absente -> NaN)."""
    serie = pd.Series(valeurs, copy=False)
    bornes = [-np.inf] + [borne for borne, _ in seuils] + [np.inf]
    lettres = [lettre for _, lettre in seuils] + ["G"]
    classes = pd.cut(serie, bins=bornes, labels=lettres, right=True)
    return classes.astype(object)


def etiquette_energie(conso_ep_par_m2):
    """Classe issue de la consommation en énergie primaire (kWhEP/m²/an)."""
    return _classer(conso_ep_par_m2, config.SEUILS_ENERGIE_PRIMAIRE)


def etiquette_ges(ges_par_m2):
    """Classe issue des émissions de GES (kg CO2/m²/an)."""
    return _classer(ges_par_m2, config.SEUILS_GES)


def etiquette_theorique(conso_ep_par_m2, ges_par_m2):
    """Étiquette DPE finale : la plus défavorable des deux classes.

    Retourne NaN si l'une des deux valeurs est absente.
    """
    rang = {lettre: i for i, lettre in enumerate(config.ORDRE_ETIQUETTES)}
    energie = etiquette_energie(conso_ep_par_m2).map(rang)
    ges = etiquette_ges(ges_par_m2)
    ges = pd.Series(ges.values, index=energie.index).map(rang)
    pire = pd.concat([energie, ges], axis=1).max(axis=1, skipna=False)
    return pire.map(dict(enumerate(config.ORDRE_ETIQUETTES)))
