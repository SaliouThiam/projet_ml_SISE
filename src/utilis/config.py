"""

Ce fichier contient uniquement des constantes
partagées par l'extraction, le prétraitement, les modèles, l'application Dash et
l'API. Si un choix change (périmètre, colonnes à télécharger...), on le modifie
ici et nulle part ailleurs.

Ce que ce fichier décide :
  - ce qu'on télécharge (périmètre + colonnes) ;
  - ce qu'on exclut d'office par raisonnement (fuites de données).

Ce que ce fichier NE décide PAS :
  - la sélection finale des variables, le feature engineering et les
    transformations (imputation, encodage, standardisation, découpage
    train/test...). Ils sont traités dans un fichier dédié
    (src/data/preprocessing.py, préparé d'abord en notebook) à partir des
    mesures faites sur les données. Les listes ci-dessous ne sont donc que des
    CANDIDATES.

"""

from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Chemins du projet
# ---------------------------------------------------------------------------
RACINE = Path(__file__).resolve().parent.parent  # dossier m2_enedis/
DATA_BRUT = RACINE / "data" / "raw"              # extractions brutes de l'API
DATA_TRAITE = RACINE / "data" / "processed"      # données nettoyées
DATA_ECHANTILLON = RACINE / "data" / "sample"    # petit échantillon versionné
DOSSIER_MODELES = RACINE / "models"              # modèles entraînés (.joblib)

# ---------------------------------------------------------------------------
# 2. API ADEME (plateforme data-fair)
# ---------------------------------------------------------------------------
API_BASE = "https://data.ademe.fr/data-fair/api/v1/datasets"

# Identifiants des jeux de données : clé = nom interne, valeur = id ADEME.
DATASETS = {
    "existant": "dpe03existant",  # DPE logements existants (depuis juillet 2021)
    "neuf": "dpe02neuf",          # DPE logements neufs (depuis juillet 2021)
}

TAILLE_PAGE = 1000            # lignes par requête (maximum autorisé à vérifier dans la doc)
DELAI_REQUETE_S = 60          # délai maximal d'attente d'une réponse
PAUSE_ENTRE_REQUETES_S = 0.2  # pause polie entre deux pages
NB_ESSAIS_MAX = 3             # nouvelles tentatives en cas d'erreur réseau

# ---------------------------------------------------------------------------
# 3. Périmètre des données
#    Région Corse : la moins volumineuse, donc adaptée à l'espace disponible.
# ---------------------------------------------------------------------------
REGION_NOM = "Corse"
CODE_REGION = "94"  # code INSEE de la région ; à confirmer avec un values_agg sur code_region_ban

# Filtres envoyés à l'API (syntaxe « colonne_eq=valeur » de data-fair).
# Le filtre agit côté serveur : seules les lignes de la région sont téléchargées.
FILTRES_API = {
    "code_region_ban_eq": CODE_REGION,
}


# ---------------------------------------------------------------------------
# 4. Variables cibles
# ---------------------------------------------------------------------------
CIBLE_CLASSIFICATION = "etiquette_dpe"            # classes A à G
CIBLE_REGRESSION = "conso_5_usages_par_m2_ep"     # kWhEP/m²/an

# Colonnes qui servent à CONTRÔLER la règle de l'étiquette, jamais à prédire.
GES_PAR_M2 = "emission_ges_5_usages_par_m2"       # kg CO2/m²/an
ETIQUETTE_GES = "etiquette_ges"

ORDRE_ETIQUETTES = ["A", "B", "C", "D", "E", "F", "G"]

# ---------------------------------------------------------------------------
# 5. Variables explicatives CANDIDATES
#    Critère de départ : l'utilisateur peut les renseigner dans la page
#    « Prédiction ». Ce n'est pas la liste finale : elle sera réduite après
#    l'audit (valeurs manquantes, variance, redondance, utilité).
# ---------------------------------------------------------------------------
VARIABLES_CANDIDATES_NUMERIQUES = [
    "surface_habitable_logement",
    "hauteur_sous_plafond",
    "annee_construction",
    "nombre_niveau_logement",
     "numero_etage_appartement",
    "nombre_niveau_immeuble",
    "nombre_appartement",
    "surface_habitable_immeuble",
    "volume_stockage_generateur_n1_ecs_n1",
    "surface_chauffee_installation_chauffage_n1"
]

VARIABLES_CANDIDATES_CATEGORIELLES = [
    "type_batiment",
    "periode_construction",
    "qualite_isolation_murs",
    "qualite_isolation_menuiseries",
    "qualite_isolation_plancher_bas",
    "qualite_isolation_enveloppe",
    "type_energie_principale_chauffage",
    "type_installation_chauffage",
    "type_energie_principale_ecs",
    "type_ventilation",
    "zone_climatique",
    "classe_altitude",
    "classe_inertie_batiment",
    "logement_traversant",
    "type_generateur_chauffage_principal",
    "type_emetteur_installation_chauffage_n1",
    "type_generateur_n1_installation_n1",
    "type_installation_ecs",
    "type_generateur_chauffage_principal_ecs",
    "type_generateur_n1_ecs_n1",
    "typologie_logement",
    "position_logement_dans_immeuble",
    "isolation_toiture",
    "inertie_lourde",
    "type_generateur_froid",
    "protection_solaire_exterieure",
    "presence_brasseur_air",
    "presence_production_pv",
    "type_installation_solaire_n1"
]

VARIABLES_CANDIDATES = (
    VARIABLES_CANDIDATES_NUMERIQUES + VARIABLES_CANDIDATES_CATEGORIELLES
)

# ---------------------------------------------------------------------------
# 6. Colonnes gardées pour l'application mais PAS données aux modèles
#    (carte, filtres, rafraîchissement, détection des doublons...)
# ---------------------------------------------------------------------------
COLONNES_CONTEXTE = [
    "numero_dpe",
    "date_reception_dpe",
    "date_etablissement_dpe",
    "date_derniere_modification_dpe",
    "methode_application_dpe",
    "version_dpe",
    "adresse_ban",
    "code_postal_ban",
    "code_departement_ban",  # 2A / 2B : filtre de l'application
    "nom_commune_ban",
    "_geopoint",
    "score_ban",
    "statut_geocodage",
]


def _sans_doublon(*listes):
    """Concatène des listes en conservant l'ordre et en supprimant les doublons."""
    vues, resultat = set(), []
    for liste in listes:
        for nom in liste:
            if nom not in vues:
                vues.add(nom)
                resultat.append(nom)
    return resultat


# ---------------------------------------------------------------------------
# 7. Colonnes téléchargées (paramètre `select` de l'API)
#    Seules ces colonnes sont demandées : tout ce qu'on sait d'office inutile
#    (résultats intermédiaires du calcul, coûts, descriptions textuelles,
#    identifiants techniques...) n'est jamais téléchargé, pour économiser
#    l'espace disque et le temps.
# ---------------------------------------------------------------------------
COLONNES_A_EXTRAIRE = _sans_doublon(
    [CIBLE_CLASSIFICATION, CIBLE_REGRESSION, GES_PAR_M2, ETIQUETTE_GES],
    VARIABLES_CANDIDATES,
    COLONNES_CONTEXTE,
)

# ---------------------------------------------------------------------------
# 8. Détection des fuites de données
#    Ces colonnes sont des RÉSULTATS du calcul du DPE : interdites comme
#    variables explicatives. Cette exclusion se décide par raisonnement et non
#    par une mesure statistique (elles sont fortement corrélées à la cible
#    justement parce qu'elles en dérivent).
# ---------------------------------------------------------------------------
# PREFIXES_FUITE = (
#     "conso_",
#    # "emission_ges_",
#     "cout_",
#     "besoin_",
#    # "deperditions_",
#     # "apport_",
# )
COLONNES_FUITE_EXACTES = {"etiquette_ges", "ubat_w_par_m2_k"}


def est_colonne_fuite(nom_colonne: str) -> bool:
    """Vrai si la colonne dérive du calcul du DPE et ne doit pas servir de variable."""
    return  nom_colonne in COLONNES_FUITE_EXACTES


# ---------------------------------------------------------------------------
# 9. Seuils officiels du DPE (borne haute de chaque classe, bornes incluses)
#   VÉRIFIER sur la documentation officielle avant usage : la grille peut
#    avoir des ajustements (par exemple pour les très petites surfaces).
# ---------------------------------------------------------------------------
SEUILS_ENERGIE_PRIMAIRE = [  # kWhEP/m²/an
    (70, "A"), (110, "B"), (180, "C"), (250, "D"), (330, "E"), (420, "F"),
]  # au-delà de 420 : classe G

SEUILS_GES = [  # kg CO2/m²/an
    (6, "A"), (11, "B"), (30, "C"), (50, "D"), (70, "E"), (100, "F"),
]  # au-delà de 100 : classe G

# ---------------------------------------------------------------------------
# 10. Paramètres généraux d'entraînement
#     (le découpage lui-même est réalisé dans le fichier de prétraitement)
# ---------------------------------------------------------------------------
GRAINE_ALEATOIRE = 42   # reproductibilité des découpages et des modèles
TAILLE_TEST = 0.2       # part des données réservée à l'évaluation
