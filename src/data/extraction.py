"""
extraction.py : téléchargement des DPE depuis l'API ADEME (data-fair).

Rôle : récupérer les logements du périmètre défini dans config.py (région
Corse) pour les deux jeux (existant et neuf), avec uniquement les colonnes de
config.COLONNES_A_EXTRAIRE, et les enregistrer TELS QUELS dans data/raw/.
Aucun nettoyage ici : c'est le rôle du prétraitement.

Utilisation, depuis la racine du projet (m2_enedis/) :
    python -m src.data.extraction --compter              # nombre de lignes, sans rien télécharger
    python -m src.data.extraction --jeu existant --limite 2000   # test rapide
    python -m src.data.extraction --jeu tous             # téléchargement complet

Sorties : data/raw/dpe_existant.csv et data/raw/dpe_neuf.csv, avec une colonne
supplémentaire « source_jeu » (existant ou neuf).
"""

import argparse
import logging
import time

import pandas as pd
import requests

from src.utilis import config

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Requêtes HTTP
# ---------------------------------------------------------------------------
def _get_json(url, params=None):
    """GET avec nouvelles tentatives en cas d'erreur réseau ou serveur.

    Une erreur client (4xx, par exemple une colonne inconnue) n'est pas
    retentée : elle signale un problème de requête, pas de réseau. Les codes
    408 (délai dépassé) et 429 (trop de requêtes) sont retentés.
    """
    derniere_erreur = None
    for essai in range(1, config.NB_ESSAIS_MAX + 1):
        try:
            reponse = requests.get(url, params=params, timeout=config.DELAI_REQUETE_S)
            reponse.raise_for_status()
            return reponse.json()
        except requests.HTTPError as erreur:
            code = erreur.response.status_code if erreur.response is not None else None
            if code is not None and 400 <= code < 500 and code not in (408, 429):
                details = erreur.response.text[:300] if erreur.response is not None else ""
                raise RuntimeError(
                    f"Requête refusée par l'API (code {code}) : {details}"
                ) from erreur
            derniere_erreur = erreur
        except requests.RequestException as erreur:
            derniere_erreur = erreur
        attente = 2 ** essai
        log.warning("Échec de la requête (essai %d/%d) : %s. Nouvel essai dans %d s.",
                    essai, config.NB_ESSAIS_MAX, derniere_erreur, attente)
        time.sleep(attente)
    raise RuntimeError(
        f"Échec après {config.NB_ESSAIS_MAX} essais : {derniere_erreur}"
    ) from derniere_erreur


# ---------------------------------------------------------------------------
# Schéma et préparation de la requête
# ---------------------------------------------------------------------------
def lire_colonnes_disponibles(dataset_id):
    """Liste des colonnes réellement présentes dans le jeu (GET /schema).

    Le format exact de la réponse est à confirmer dans la documentation de
    l'API : on gère ici une liste de champs (clé « key ») ou un dictionnaire.
    """
    schema = _get_json(f"{config.API_BASE}/{dataset_id}/schema")
    if isinstance(schema, list):
        return [champ["key"] for champ in schema if isinstance(champ, dict) and "key" in champ]
    if isinstance(schema, dict):
        return list(schema.get("properties", schema).keys())
    raise RuntimeError("Format de schéma inattendu : adapter lire_colonnes_disponibles().")


def _preparer_requete(nom_jeu, dataset_id):
    """Colonnes à demander et paramètres de la première requête."""
    disponibles = set(lire_colonnes_disponibles(dataset_id))

    # Le filtre géographique doit porter sur une colonne qui existe dans ce jeu.
    for cle in config.FILTRES_API:
        colonne = cle[:-3] if cle.endswith("_eq") else cle
        if colonne not in disponibles:
            raise RuntimeError(
                f"Le jeu « {nom_jeu} » n'a pas la colonne de filtre « {colonne} » : "
                "adapter FILTRES_API dans config.py."
            )

    colonnes = [c for c in config.COLONNES_A_EXTRAIRE if c in disponibles]
    absentes = [c for c in config.COLONNES_A_EXTRAIRE if c not in disponibles]
    if absentes:
        log.warning("[%s] colonnes demandées mais absentes du jeu (ignorées) : %s",
                    nom_jeu, absentes)
    for cible in (config.CIBLE_CLASSIFICATION, config.CIBLE_REGRESSION):
        if cible not in colonnes:
            raise RuntimeError(f"[{nom_jeu}] la cible « {cible} » est absente du jeu.")

    params = {"size": config.TAILLE_PAGE, "select": ",".join(colonnes), **config.FILTRES_API}
    return colonnes, params


def compter_lignes(nom_jeu):
    """Nombre de lignes du périmètre, sans rien télécharger (une ligne demandée)."""
    dataset_id = config.DATASETS[nom_jeu]
    page = _get_json(
        f"{config.API_BASE}/{dataset_id}/lines",
        params={"size": 1, **config.FILTRES_API},
    )
    return page.get("total")


# ---------------------------------------------------------------------------
# Téléchargement
# ---------------------------------------------------------------------------
def telecharger_jeu(nom_jeu, limite=None):
    """Télécharge un jeu page par page et l'enregistre dans data/raw/.

    L'écriture se fait au fil de l'eau pour ne pas garder tout le jeu en mémoire.
    `limite` permet un test rapide sur un nombre maximal de lignes.
    Retourne (chemin du fichier, nombre de lignes écrites).
    """
    dataset_id = config.DATASETS[nom_jeu]
    colonnes, params = _preparer_requete(nom_jeu, dataset_id)
    if limite:
        params["size"] = min(config.TAILLE_PAGE, limite)

    config.DATA_BRUT.mkdir(parents=True, exist_ok=True)
    sortie = config.DATA_BRUT / f"dpe_{nom_jeu}.csv"
    if sortie.exists():
        sortie.unlink()  # on repart d'un fichier vide

    page = _get_json(f"{config.API_BASE}/{dataset_id}/lines", params=params)
    total = page.get("total")
    log.info("[%s] %s lignes dans le périmètre (%s).", nom_jeu, total, config.REGION_NOM)

    ecrites = 0
    while True:
        lignes = page.get("results", [])
        if not lignes:
            break
        if limite:
            lignes = lignes[: limite - ecrites]

        # Les lignes JSON omettent les valeurs absentes : on impose les mêmes
        # colonnes, dans le même ordre, à chaque page.
        tableau = pd.DataFrame(lignes).reindex(columns=colonnes)
        tableau["source_jeu"] = nom_jeu
        tableau.to_csv(sortie, mode="a", header=(ecrites == 0), index=False)
        ecrites += len(tableau)
        log.info("[%s] %d / %s lignes enregistrées", nom_jeu, ecrites, total)

        if limite and ecrites >= limite:
            break
        suivante = page.get("next")  # URL de la page suivante, fournie par l'API
        if not suivante:
            break
        time.sleep(config.PAUSE_ENTRE_REQUETES_S)
        page = _get_json(suivante)

    if total is not None and not limite and ecrites != total:
        log.warning("[%s] %d lignes écrites pour %s annoncées par l'API.", nom_jeu, ecrites, total)
    return sortie, ecrites


# ---------------------------------------------------------------------------
# Ligne de commande
# ---------------------------------------------------------------------------
def main():
    parseur = argparse.ArgumentParser(description="Extraction des DPE depuis l'API ADEME.")
    parseur.add_argument("--jeu", choices=["existant", "neuf", "tous"], default="tous")
    parseur.add_argument("--limite", type=int, default=None,
                         help="nombre maximal de lignes par jeu (test rapide)")
    parseur.add_argument("--compter", action="store_true",
                         help="affiche le nombre de lignes du périmètre sans télécharger")
    args = parseur.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    jeux = list(config.DATASETS) if args.jeu == "tous" else [args.jeu]

    for nom in jeux:
        if args.compter:
            print(f"{nom} ({config.REGION_NOM}) : {compter_lignes(nom)} lignes")
        else:
            chemin, nb = telecharger_jeu(nom, limite=args.limite)
            print(f"{nom} : {nb} lignes -> {chemin}")


if __name__ == "__main__":
    main()
