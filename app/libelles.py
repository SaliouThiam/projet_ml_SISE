"""Libellés lisibles pour l'interface : noms de variables, modalités et regroupement du formulaire."""

LIBELLES_VARIABLES = {
    # Le logement
    "surface_habitable_logement": "Surface habitable (m²)",
    "hauteur_sous_plafond": "Hauteur sous plafond (m)",
    "annee_construction": "Année de construction",
    "periode_construction": "Période de construction",
    "type_batiment": "Type de bâtiment",
    "nombre_niveau_logement": "Nombre de niveaux du logement",
    "numero_etage_appartement": "Étage de l'appartement",
    "typologie_logement": "Typologie (T1, T2…)",
    "position_logement_dans_immeuble": "Position dans l'immeuble",
    "nombre_appartement": "Nombre d'appartements de l'immeuble",
    "nombre_niveau_immeuble": "Nombre de niveaux de l'immeuble",
    "surface_habitable_immeuble": "Surface habitable de l'immeuble (m²)",
    "logement_traversant": "Logement traversant",
    "classe_altitude": "Altitude",
    "zone_climatique": "Zone climatique",
    # Isolation et bâti
    "qualite_isolation_murs": "Isolation des murs",
    "qualite_isolation_menuiseries": "Isolation des fenêtres",
    "qualite_isolation_plancher_bas": "Isolation du plancher bas",
    "qualite_isolation_enveloppe": "Isolation globale du bâtiment",
    "isolation_toiture": "Toiture isolée",
    "inertie_lourde": "Bâtiment à inertie lourde",
    "classe_inertie_batiment": "Inertie du bâtiment",
    "protection_solaire_exterieure": "Protection solaire extérieure",
    # Chauffage
    "famille_energie_chauffage": "Énergie du chauffage",
    "type_installation_chauffage": "Chauffage individuel ou collectif",
    "type_generateur_chauffage_principal": "Générateur de chauffage principal",
    "type_generateur_n1_installation_n1": "Générateur de chauffage (installation 1)",
    "type_emetteur_installation_chauffage_n1": "Émetteurs de chaleur (radiateurs, plancher…)",
    "surface_chauffee_installation_chauffage_n1": "Surface chauffée (m²)",
    # Eau chaude
    "famille_energie_ecs": "Énergie de l'eau chaude",
    "type_installation_ecs": "Eau chaude individuelle ou collective",
    "type_generateur_chauffage_principal_ecs": "Générateur d'eau chaude principal",
    "type_generateur_n1_ecs_n1": "Générateur d'eau chaude (installation 1)",
    "volume_stockage_generateur_n1_ecs_n1": "Volume du ballon d'eau chaude (litres)",
    "type_installation_solaire_n1": "Installation solaire thermique",
    # Ventilation, climatisation, électricité
    "famille_ventilation": "Type de ventilation",
    "type_generateur_froid": "Climatisation",
    "presence_brasseur_air": "Brasseur d'air",
    "presence_production_pv": "Panneaux photovoltaïques",
}

LIBELLES_MODALITES = {
    "electricite": "Électricité", "gaz_naturel": "Gaz naturel", "gpl": "GPL, propane ou butane",
    "fioul": "Fioul", "bois": "Bois", "reseau_chaleur": "Réseau de chaleur", "charbon": "Charbon",
    "autre": "Autre", "vmc_double_flux": "VMC double flux", "vmc_hygro": "VMC hygroréglable",
    "vmc_autoreglable": "VMC autoréglable", "vmc_autre": "VMC (autre type)",
    "naturelle": "Ventilation naturelle", "hybride": "Ventilation hybride",
    "fenetres": "Ouverture des fenêtres", "entrees_air": "Entrées d'air",
    "oui": "Oui", "non": "Non", "existant": "Logements existants", "neuf": "Logements neufs",
}

GROUPES = {
    "Le logement": ["surface_habitable_logement", "hauteur_sous_plafond", "annee_construction",
                    "periode_construction", "type_batiment", "nombre_niveau_logement",
                    "numero_etage_appartement", "typologie_logement", "position_logement_dans_immeuble",
                    "nombre_appartement", "nombre_niveau_immeuble", "surface_habitable_immeuble",
                    "logement_traversant", "classe_altitude", "zone_climatique"],
    "Isolation et bâti": ["qualite_isolation_murs", "qualite_isolation_menuiseries",
                          "qualite_isolation_plancher_bas", "qualite_isolation_enveloppe",
                          "isolation_toiture", "inertie_lourde", "classe_inertie_batiment",
                          "protection_solaire_exterieure"],
    "Chauffage": ["famille_energie_chauffage", "type_installation_chauffage",
                  "type_generateur_chauffage_principal", "type_generateur_n1_installation_n1",
                  "type_emetteur_installation_chauffage_n1", "surface_chauffee_installation_chauffage_n1"],
    "Eau chaude": ["famille_energie_ecs", "type_installation_ecs", "type_generateur_chauffage_principal_ecs",
                   "type_generateur_n1_ecs_n1", "volume_stockage_generateur_n1_ecs_n1",
                   "type_installation_solaire_n1"],
    "Ventilation, climatisation et électricité": ["famille_ventilation", "type_generateur_froid",
                                                   "presence_brasseur_air", "presence_production_pv"],
}


def libelle_variable(variable):
    return LIBELLES_VARIABLES.get(variable, variable.replace("_", " ").capitalize())


def libelle_modalite(modalite):
    texte = str(modalite)
    return LIBELLES_MODALITES.get(texte, texte[:1].upper() + texte[1:])


def groupe_variable(variable):
    for groupe, variables in GROUPES.items():
        if variable in variables:
            return groupe
    return "Autres informations"
