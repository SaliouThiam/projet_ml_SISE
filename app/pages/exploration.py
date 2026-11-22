"""Page « Exploration » : filtres, indicateurs, quatre types de graphiques, tableau et exports."""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html

from app import composants, donnees, graphiques
from app.libelles import libelle_modalite

dash.register_page(__name__, path="/exploration", name="Exploration", title="DPE Corse · Exploration",
                   order=1, icon="bi-bar-chart-line")

COLONNES_TABLEAU = ["etiquette", "conso", "ges", "surface", "periode", "type_batiment",
                    "energie_chauffage", "commune", "jeu"]
VALEURS_PAR_DEFAUT = ("tous", donnees.ORDRE_ETIQUETTES, [], [], [donnees.SURFACE_MIN, donnees.SURFACE_MAX], 2000, "conso")


def _options(colonne):
    return [{"label": libelle_modalite(v), "value": v} for v in donnees.valeurs_possibles(colonne)]


def _panneau_filtres():
    return dbc.Card(dbc.CardBody([
        html.H5([html.I(className="bi bi-funnel me-2"), "Filtres"]),
        html.Label("Jeu de données", className="fw-bold mt-2"),
        dbc.RadioItems(id="expl-jeu", value="tous", options=[
            {"label": "Tous", "value": "tous"}, {"label": "Existants", "value": "existant"},
            {"label": "Neufs", "value": "neuf"}]),
        html.Label("Étiquettes affichées", className="fw-bold mt-3"),
        dbc.Checklist(id="expl-etiquettes", value=donnees.ORDRE_ETIQUETTES, inline=True,
                      options=[{"label": e, "value": e} for e in donnees.ORDRE_ETIQUETTES]),
        html.Label("Énergie de chauffage", className="fw-bold mt-3"),
        dcc.Dropdown(id="expl-energies", options=_options("energie_chauffage"), multi=True,
                     placeholder="Toutes"),
        html.Label("Type de bâtiment", className="fw-bold mt-3"),
        dcc.Dropdown(id="expl-batiments", options=_options("type_batiment"), multi=True, placeholder="Tous"),
        html.Label("Surface habitable (m²)", className="fw-bold mt-3"),
        dcc.RangeSlider(id="expl-surface", min=donnees.SURFACE_MIN, max=donnees.SURFACE_MAX, step=10,
                        value=[donnees.SURFACE_MIN, donnees.SURFACE_MAX],
                        marks={v: str(v) for v in range(0, 301, 50)},
                        tooltip={"placement": "bottom", "always_visible": False}),
        html.Label("Indicateur étudié", className="fw-bold mt-4"),
        dbc.RadioItems(id="expl-indicateur", value="conso", options=[
            {"label": "Consommation (kWhEP/m²/an)", "value": "conso"},
            {"label": "Émissions de GES (kg CO₂/m²/an)", "value": "ges"}]),
        html.Label("Points du nuage (échantillon)", className="fw-bold mt-3"),
        dcc.Slider(id="expl-points", min=500, max=5000, step=500, value=2000,
                   marks={500: "500", 2500: "2 500", 5000: "5 000"}),
        dbc.Button([html.I(className="bi bi-arrow-counterclockwise me-1"), "Réinitialiser"], id="expl-reset",
                   color="secondary", outline=True, size="sm", className="mt-4 w-100"),
    ]), className="carte-sans-bordure")


def layout():
    try:
        donnees.charger()
    except donnees.DonneesIntrouvables as erreur:
        return composants.alerte(str(erreur), "Données de l'application introuvables")
    return html.Div([
        composants.entete("Exploration des logements",
                          "Filtrez les logements : indicateurs, graphiques et tableau se mettent à jour.", "bi-bar-chart-line"),
        dbc.Row([
            dbc.Col(_panneau_filtres(), md=3, className="mb-3"),
            dbc.Col([
                dbc.Row(id="expl-kpis", className="mb-3 g-3"),
                dbc.Row([
                    dbc.Col(composants.graphique("expl-histo"), md=6, className="mb-3"),
                    dbc.Col(composants.graphique("expl-boite"), md=6, className="mb-3"),
                    dbc.Col(composants.graphique("expl-nuage"), md=6, className="mb-3"),
                    dbc.Col(composants.graphique("expl-heatmap"), md=6, className="mb-3"),
                ]),
                html.H5("Logements sélectionnés", className="titre-page"),
                html.P(id="expl-legende", className="text-muted"),
                dash_table.DataTable(
                    id="expl-table", columns=[{"name": c, "id": c} for c in COLONNES_TABLEAU], page_size=10,
                    sort_action="native", style_table={"overflowX": "auto"},
                    style_cell={"padding": "6px", "fontSize": 13}, style_header={"fontWeight": "bold"}),
                dbc.Button([html.I(className="bi bi-filetype-csv me-1"), "Télécharger les données filtrées (.csv)"],
                           id="expl-csv", color="primary", className="mt-3"),
                dcc.Download(id="expl-download"),
            ], md=9),
        ]),
    ])


def _logements(jeu, etiquettes, energies, batiments, surface):
    return donnees.filtrer(donnees.charger(), jeu, etiquettes, energies, batiments, surface)


@callback(
    Output("expl-kpis", "children"), Output("expl-histo", "figure"), Output("expl-boite", "figure"),
    Output("expl-nuage", "figure"), Output("expl-heatmap", "figure"), Output("expl-table", "data"),
    Output("expl-legende", "children"),
    Input("expl-jeu", "value"), Input("expl-etiquettes", "value"), Input("expl-energies", "value"),
    Input("expl-batiments", "value"), Input("expl-surface", "value"), Input("expl-points", "value"),
    Input("expl-indicateur", "value"),
)
def mettre_a_jour(jeu, etiquettes, energies, batiments, surface, n_points, indicateur):
    df = _logements(jeu, etiquettes, energies, batiments, surface)
    ind = donnees.indicateurs(df)
    cartes = [
        composants.kpi("logements", composants.valeur_ou_tiret(ind and ind["n"], ",").replace(",", " "), "bi-houses"),
        composants.kpi("consommation médiane (kWhEP/m²/an)", composants.valeur_ou_tiret(ind and ind["conso_mediane"], ".0f"), "bi-lightning-charge"),
        composants.kpi("passoires énergétiques (F ou G)", composants.valeur_ou_tiret(ind and ind["part_passoires"], ".1%"), "bi-exclamation-triangle"),
        composants.kpi("surface médiane (m²)", composants.valeur_ou_tiret(ind and ind["surface_mediane"], ".0f"), "bi-aspect-ratio"),
        composants.kpi("chauffés à l'électricité", composants.valeur_ou_tiret(ind and ind["part_electricite"], ".0%"), "bi-plug"),
    ]
    kpis = [dbc.Col(c, md=True) for c in cartes]

    tableau = df.head(500).assign(etiquette=lambda d: d["etiquette"].astype(str))[COLONNES_TABLEAU]
    legende = (f"{len(df):,} logements correspondent aux filtres".replace(",", " ")
               + (" ; les 500 premiers sont affichés (le téléchargement contient tout)." if len(df) > 500 else "."))
    return (kpis, graphiques.histogramme(df, indicateur), graphiques.boite(df, indicateur),
            graphiques.nuage(df, indicateur, n_points or 2000), graphiques.carte_chaleur(df),
            tableau.to_dict("records"), legende)


@callback(
    Output("expl-jeu", "value"), Output("expl-etiquettes", "value"), Output("expl-energies", "value"),
    Output("expl-batiments", "value"), Output("expl-surface", "value"), Output("expl-points", "value"),
    Output("expl-indicateur", "value"), Input("expl-reset", "n_clicks"), prevent_initial_call=True)
def reinitialiser(_):
    return VALEURS_PAR_DEFAUT


@callback(
    Output("expl-download", "data"), Input("expl-csv", "n_clicks"),
    State("expl-jeu", "value"), State("expl-etiquettes", "value"), State("expl-energies", "value"),
    State("expl-batiments", "value"), State("expl-surface", "value"), prevent_initial_call=True)
def exporter_csv(_, jeu, etiquettes, energies, batiments, surface):
    df = _logements(jeu, etiquettes, energies, batiments, surface)
    return dcc.send_data_frame(df[COLONNES_TABLEAU].to_csv, "logements_filtres.csv", index=False)
