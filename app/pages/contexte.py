"""Page « Contexte » : présentation du projet, des données disponibles et de leurs grandes tendances."""

import dash
import dash_bootstrap_components as dbc
from dash import dash_table, html

from app import composants, donnees, graphiques

dash.register_page(__name__, path="/", name="Contexte", title="DPE Corse · Contexte",
                   order=0, icon="bi-house-door")

# Dictionnaire des données affichées dans l'application.
DICTIONNAIRE = [
    {"colonne": "etiquette", "description": "Étiquette DPE de A (très performant) à G (très peu performant)", "type": "texte"},
    {"colonne": "conso", "description": "Consommation d'énergie primaire par m² et par an (kWhEP/m²/an), valeur conventionnelle", "type": "nombre"},
    {"colonne": "ges", "description": "Émissions de gaz à effet de serre par m² et par an (kg CO₂/m²/an)", "type": "nombre"},
    {"colonne": "surface", "description": "Surface habitable du logement (m²)", "type": "nombre"},
    {"colonne": "periode", "description": "Période de construction du bâtiment", "type": "texte"},
    {"colonne": "type_batiment", "description": "Maison, appartement ou immeuble", "type": "texte"},
    {"colonne": "energie_chauffage", "description": "Énergie principale du chauffage (regroupée en familles)", "type": "texte"},
    {"colonne": "isolation", "description": "Qualité de l'isolation globale du bâtiment", "type": "texte"},
    {"colonne": "jeu", "description": "Logement existant ou neuf (deux jeux de données ADEME)", "type": "texte"},
    {"colonne": "departement / commune", "description": "Corse-du-Sud (2A) ou Haute-Corse (2B) et nom de la commune", "type": "texte"},
    {"colonne": "mois", "description": "Mois de réception du DPE par l'ADEME", "type": "date"},
    {"colonne": "methode", "description": "Méthode de calcul utilisée pour établir le DPE", "type": "texte"},
]


def layout():
    try:
        df = donnees.charger()
    except donnees.DonneesIntrouvables as erreur:
        return composants.alerte(str(erreur), "Données de l'application introuvables")

    ind = donnees.indicateurs(df)
    part_neuf = float((df["jeu"] == "neuf").mean())
    apercu = df.head(8).assign(etiquette=lambda d: d["etiquette"].astype(str))[
        ["etiquette", "conso", "ges", "surface", "periode", "type_batiment", "energie_chauffage", "commune", "jeu"]]

    return html.Div([
        dbc.Row([
            dbc.Col([
                composants.entete("Estimer le DPE d'un logement en Corse",
                                  "Application réalisée pour le projet Python / ML du Master 2 SISE", "bi-house-door"),
                html.P("Avec la hausse des prix de l'énergie, la sobriété énergétique est au cœur des préoccupations. "
                       "Le Diagnostic de Performance Énergétique (DPE) classe chaque logement de A à G selon sa "
                       "consommation d'énergie et ses émissions de gaz à effet de serre. Cette application permet "
                       "d'explorer les DPE de Corse et d'estimer l'étiquette et la consommation d'un logement à "
                       "partir de ses caractéristiques."),
                html.H5("Comment utiliser l'application"),
                html.Ul([
                    html.Li([html.B("Exploration"), " : filtrer les logements et comparer les consommations."]),
                    html.Li([html.B("Carte"), " : visualiser la situation de chaque commune."]),
                    html.Li([html.B("Prédiction"), " : estimer l'étiquette et la consommation d'un logement."]),
                ]),
                dbc.Alert([html.I(className="bi bi-info-circle me-2"),
                           "Les valeurs de consommation du DPE sont des valeurs ", html.B("conventionnelles"),
                           ", calculées à partir des caractéristiques du bâtiment avec des hypothèses d'usage "
                           "standard. Elles ne correspondent pas à la facture réelle d'un ménage."], color="info"),
            ], md=7),
            dbc.Col(html.Img(src=dash.get_asset_url("echelle_dpe.svg"), alt="Échelle des étiquettes DPE",
                             style={"width": "100%", "maxWidth": "380px"}), md=5,
                    className="d-flex align-items-center justify-content-center"),
        ], className="mb-4"),

        dbc.Row([
            dbc.Col(composants.kpi("logements analysés", f"{ind['n']:,}".replace(",", " "), "bi-houses"), md=3, className="mb-3"),
            dbc.Col(composants.kpi("de logements neufs", f"{part_neuf:.0%}", "bi-building-add"), md=3, className="mb-3"),
            dbc.Col(composants.kpi("consommation médiane (kWhEP/m²/an)", f"{ind['conso_mediane']:.0f}", "bi-lightning-charge"), md=3, className="mb-3"),
            dbc.Col(composants.kpi("de passoires énergétiques (F ou G)", f"{ind['part_passoires']:.1%}", "bi-exclamation-triangle"), md=3, className="mb-3"),
        ]),

        dbc.Row([
            dbc.Col(composants.graphique("ctx-etiquettes", graphiques.repartition_etiquettes(df)), md=6, className="mb-3"),
            dbc.Col(composants.graphique("ctx-jeux", graphiques.repartition_jeux(df)), md=6, className="mb-3"),
            dbc.Col(composants.graphique("ctx-mois", graphiques.serie_mensuelle(df)), md=12, className="mb-3"),
        ]),

        html.H4("Les données disponibles", className="titre-page mt-3"),
        html.P("Les données viennent des deux jeux « DPE logements existants » et « DPE logements neufs » "
               "de l'ADEME (data.ademe.fr), limités à la Corse. Seules les colonnes utiles à l'application sont "
               "conservées ; aucune adresse ni coordonnée individuelle n'est affichée."),
        dbc.Row([
            dbc.Col([html.H6("Aperçu"),
                     dash_table.DataTable(data=apercu.to_dict("records"),
                                          columns=[{"name": c, "id": c} for c in apercu.columns],
                                          style_table={"overflowX": "auto"},
                                          style_cell={"padding": "6px", "fontSize": 13},
                                          style_header={"fontWeight": "bold"})], md=12, className="mb-3"),
            dbc.Col([html.H6("Dictionnaire des données"),
                     dash_table.DataTable(data=DICTIONNAIRE,
                                          columns=[{"name": n, "id": i} for n, i in
                                                   [("Colonne", "colonne"), ("Description", "description"), ("Type", "type")]],
                                          style_table={"overflowX": "auto"},
                                          style_cell={"padding": "6px", "fontSize": 13, "textAlign": "left",
                                                      "whiteSpace": "normal", "height": "auto"},
                                          style_header={"fontWeight": "bold"})], md=12),
        ]),
    ])
