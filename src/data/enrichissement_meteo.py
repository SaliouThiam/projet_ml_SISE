from pathlib import Path
import pandas as pd

# Dossier des données préparées
DOSSIER = Path(__file__).resolve().parent / "processed"

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
    cle = (
        departements.astype(str).str.strip().str.upper()
        + "|"
        + normaliser(communes)
    )

    # Corriger les deux écritures déformées de L'Île-Rousse
    return cle.replace({
        "2B|lalerousse": "2B|lilerousse",
        "2B|lazlerousse": "2B|lilerousse",
    })


# Charger les données météo
meteo = pd.read_csv(
    DOSSIER / "meteo_corse_communes.csv",
    dtype={"admin2_code": str}
)

meteo["cle"] = creer_cle(
    meteo["admin2_code"],
    meteo["name"]
)

# Éviter qu'une jointure duplique des logements
if meteo["cle"].duplicated().any():
    raise ValueError("Clés météo en doublon")

meteo = meteo[
    ["cle", "temperature_moyenne_c", "precipitation_annuelle_mm"]
]

# Ne pas écraser d'anciens résultats
for nom in ["train", "test"]:
    sortie = DOSSIER / f"{nom}_meteo.csv"
    if sortie.exists():
        raise FileExistsError(f"Le fichier existe déjà : {sortie}")

# Enrichir séparément train et test
for nom in ["train", "test"]:
    logements = pd.read_csv(
        DOSSIER / f"{nom}.csv",
        dtype={
            "nom_commune_ban": str,
            "code_departement_ban": str
        }
    )

    logements["cle"] = creer_cle(
        logements["code_departement_ban"],
        logements["nom_commune_ban"]
    )

    resultat = logements.merge(
        meteo,
        on="cle",
        how="left",
        validate="many_to_one",
        sort=False
    )

    # Vérifications
    if len(resultat) != len(logements):
        raise ValueError("Le nombre de logements a changé")

    if resultat[
        ["temperature_moyenne_c", "precipitation_annuelle_mm"]
    ].isna().any().any():
        raise ValueError("Des données météo sont manquantes")

    if not resultat["numero_dpe"].equals(logements["numero_dpe"]):
        raise ValueError("L'ordre des logements a changé")

    resultat = resultat.drop(columns=["cle"])

    sortie = DOSSIER / f"{nom}_meteo.csv"
    resultat.to_csv(sortie, index=False, encoding="utf-8-sig")

    print(f"{nom} : {len(resultat)} logements enrichis")
    print(f"Fichier créé : {sortie.name}")

print("Enrichissement terminé avec succès.")