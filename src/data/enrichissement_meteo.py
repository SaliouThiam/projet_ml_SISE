"""Rattachement des normales climatiques communales aux logements DPE.

Deux usages, avec le même code :

1. Comme module (notebooks, application) :
       from src.data import enrichissement_meteo as meteo
       logements = meteo.ajouter_meteo(logements)

2. En ligne de commande, comportement d'origine : écrit train_meteo.csv et test_meteo.csv
       python src/data/enrichissement_meteo.py

La table communale (360 communes) est produite par preparer_meteo_corse.py.
Les fonctions normaliser et creer_cle sont celles du script d'origine ; le traitement a été
rangé dans des fonctions et dans main() pour que l'import n'exécute plus rien.
"""

from pathlib import Path

import pandas as pd

# Dossier des données préparées
DOSSIER = Path(__file__).resolve().parent / "processed"
TABLE_METEO = DOSSIER / "meteo_corse_communes.csv"
COLONNES_METEO = ["temperature_moyenne_c", "precipitation_annuelle_mm"]

# Deux écritures déformées de L'Île-Rousse rencontrées dans les adresses
CORRECTIONS_CLES = {
    "2B|lalerousse": "2B|lilerousse",
    "2B|lazlerousse": "2B|lilerousse",
}


# Normaliser les noms des communes
def normaliser(noms):
    return (
        noms.fillna("")
        .astype(str)
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore")
        .str.decode("ascii")
        .str.lower()
        .str.replace(r"[^a-z0-9]", "", regex=True)
    )


def creer_cle(departements, communes):
    """Clé de jointure « département|nom normalisé » (ex. « 2B|bastia »)."""
    cle = (
        departements.astype(str).str.strip().str.upper()
        + "|"
        + normaliser(communes)
    )
    # Corriger les deux écritures déformées de L'Île-Rousse
    return cle.replace(CORRECTIONS_CLES)


def charger_table_meteo(chemin=None):
    """Table communale des normales : une ligne par commune, clé de jointure incluse."""
    chemin = Path(chemin) if chemin else TABLE_METEO
    if not chemin.exists():
        raise FileNotFoundError(
            f"Table météo introuvable : {chemin}\n"
            "Télécharger le CSV source dans src/data/raw/ puis lancer preparer_meteo_corse.py "
            "(voir SOURCE_METEO.md)."
        )
    meteo = pd.read_csv(chemin, dtype={"admin2_code": str})
    meteo["cle"] = creer_cle(meteo["admin2_code"], meteo["name"])

    # Éviter qu'une jointure duplique des logements
    if meteo["cle"].duplicated().any():
        raise ValueError("Clés météo en doublon")
    return meteo[["cle"] + COLONNES_METEO]


def ajouter_meteo(df, table=None, exiger_complet=True):
    """Ajoute temperature_moyenne_c et precipitation_annuelle_mm à chaque logement.

    L'ordre et le nombre de lignes sont conservés. Si exiger_complet est vrai, une commune
    sans correspondance déclenche une erreur ; sinon la valeur reste manquante
    (utile dans l'application, où la commune est saisie à la main).
    """
    table = charger_table_meteo() if table is None else table
    par_cle = table.set_index("cle")
    cle = creer_cle(df["code_departement_ban"], df["nom_commune_ban"])

    resultat = df.copy()
    for colonne in COLONNES_METEO:
        resultat[colonne] = cle.map(par_cle[colonne]).to_numpy()

    if exiger_complet and resultat[COLONNES_METEO].isna().any().any():
        manquantes = sorted(set(cle[resultat[COLONNES_METEO].isna().any(axis=1)]))
        raise ValueError(f"Des données météo sont manquantes ({len(manquantes)} commune(s)), "
                         f"par exemple : {manquantes[:10]}")
    return resultat


def main():
    """Enrichit séparément train et test, sans écraser d'anciens résultats."""
    table = charger_table_meteo()

    for nom in ["train", "test"]:
        sortie = DOSSIER / f"{nom}_meteo.csv"
        if sortie.exists():
            raise FileExistsError(f"Le fichier existe déjà : {sortie}")

    for nom in ["train", "test"]:
        logements = pd.read_csv(
            DOSSIER / f"{nom}.csv",
            dtype={"nom_commune_ban": str, "code_departement_ban": str},
        )
        resultat = ajouter_meteo(logements, table)

        # Vérifications
        if len(resultat) != len(logements):
            raise ValueError("Le nombre de logements a changé")
        if not resultat["numero_dpe"].equals(logements["numero_dpe"]):
            raise ValueError("L'ordre des logements a changé")

        sortie = DOSSIER / f"{nom}_meteo.csv"
        resultat.to_csv(sortie, index=False, encoding="utf-8-sig")
        print(f"{nom} : {len(resultat)} logements enrichis")
        print(f"Fichier créé : {sortie.name}")

    print("Enrichissement terminé avec succès.")


if __name__ == "__main__":
    main()