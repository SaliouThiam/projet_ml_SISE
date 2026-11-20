"""Préparer ou vérifier les normales climatiques par commune en Corse.

Entrée attendue (téléchargée séparément depuis le jeu OpenData) :
    src/data/raw/fr_climate_normals_1991_2020.csv

Sortie :
    src/data/processed/meteo_corse_communes.csv

Ce script ne remplace jamais un fichier existant : il en vérifie le contenu.
À placer dans src/data/, à côté de enrichissement_meteo.py.
"""

from pathlib import Path

import pandas as pd


DOSSIER = Path(__file__).resolve().parent
SOURCE = DOSSIER / "raw" / "fr_climate_normals_1991_2020.csv"
SORTIE = DOSSIER / "processed" / "meteo_corse_communes.csv"


def preparer_meteo() -> pd.DataFrame:
    if not SOURCE.is_file():
        raise FileNotFoundError(
            f"CSV météo introuvable : {SOURCE}\n"
            "Télécharger le CSV source et le placer dans src/data/raw/."
        )

    colonnes = [
        "code", "name", "admin2_code", "month", "tmean_c", "precip_mm", "period"
    ]
    donnees = pd.read_csv(
        SOURCE,
        usecols=colonnes,
        dtype={"code": str, "admin2_code": str, "period": str},
        low_memory=False,
    )
    corse = donnees.loc[donnees["admin2_code"].isin(["2A", "2B"])].copy()

    if corse.empty:
        raise ValueError("Aucune commune corse trouvée dans le CSV source.")
    if corse["period"].isna().any() or set(corse["period"]) != {"1991-2020"}:
        raise ValueError("La période météo ne correspond pas à 1991-2020.")

    for colonne in ("month", "tmean_c", "precip_mm"):
        corse[colonne] = pd.to_numeric(corse[colonne], errors="coerce")
    if corse[["code", "name", "admin2_code", "month", "tmean_c", "precip_mm"]].isna().any().any():
        raise ValueError("Valeurs manquantes ou non numériques dans les données corses.")
    if not corse["month"].isin(range(1, 13)).all():
        raise ValueError("Des mois sont en dehors de l'intervalle 1 à 12.")
    if corse.duplicated(["code", "month"]).any():
        raise ValueError("Doublons détectés pour une commune et un mois.")

    resume = corse.groupby(
        ["code", "name", "admin2_code"], as_index=False
    ).agg(
        nb_mois=("month", "nunique"),
        temperature_moyenne_c=("tmean_c", "mean"),
        precipitation_annuelle_mm=("precip_mm", "sum"),
    )

    if (resume["nb_mois"] != 12).any():
        raise ValueError("Certaines communes n'ont pas leurs 12 mois de météo.")
    if len(resume) != 360:
        raise ValueError(f"360 communes attendues, {len(resume)} trouvées.")

    return resume


def main() -> None:
    resultat = preparer_meteo()
    if SORTIE.exists():
        existant = pd.read_csv(
            SORTIE, dtype={"code": str, "admin2_code": str}, low_memory=False
        )
        colonnes = list(resultat.columns)
        if set(existant.columns) != set(colonnes):
            raise ValueError(
                "Le fichier météo existant n'a pas les colonnes attendues. "
                "Il n'a pas été modifié."
            )
        colonnes_cle = ["code", "name", "admin2_code"]
        existant = existant[colonnes].sort_values(colonnes_cle).reset_index(drop=True)
        resultat = resultat.sort_values(colonnes_cle).reset_index(drop=True)
        pd.testing.assert_frame_equal(
            existant, resultat, check_dtype=False, check_exact=False,
            rtol=1e-10, atol=1e-6,
        )
        print(f"Vérification OK : {len(resultat)} communes, fichier existant inchangé.")
        print(f"Fichier vérifié : {SORTIE}")
    else:
        SORTIE.parent.mkdir(parents=True, exist_ok=True)
        resultat.to_csv(SORTIE, index=False, encoding="utf-8-sig")
        print(f"Fichier créé : {SORTIE}")
        print(f"Communes préparées : {len(resultat)}")


if __name__ == "__main__":
    main()
