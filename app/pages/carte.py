"""Page « Carte » : carte interactive des communes (un marqueur par commune) et classement."""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html

from app import composants, donnees, graphiques

dash.register_page(__name__, path="/carte", name="Carte", title="DPE Corse · Carte",
                   order=2, icon="bi-geo-alt")

DEPARTEMENTS = [{"label": "Toute la Corse", "value": "tous"},
                {"label": "Corse-du-Sud (2A)", "value": "2A"},
                {"label": "Haute-Corse (2B)", "value": "2B"}]
COLONNES_TABLE = [("Commune", "commune"), ("Dép.", "departement"), ("Logements", "logements"),
                  ("Conso médiane", "conso_mediane"), ("% passoires", "part_passoires")]


def layout():
    try:
        donnees.charger()
    except donnees.DonneesIntrouvables as erreur:
        return composants.alerte(str(erreur), "Données de l'application introuvables")
    return html.Div([
        composants.entete("Carte des communes",
                          "Un marqueur par commune : sa taille indique le nombre de logements, sa couleur l'indicateur choisi. "
                          "Cliquez sur un marqueur pour le détail.", "bi-geo-alt"),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5([html.I(className="bi bi-funnel me-2"), "Filtres"]),
                html.Label("Jeu de données", className="fw-bold mt-2"),
                dbc.RadioItems(id="carte-jeu", value="tous", options=[
                    {"label": "Tous", "value": "tous"}, {"label": "Existants", "value": "existant"},
                    {"label": "Neufs", "value": "neuf"}]),
                html.Label("Étiquettes prises en compte", className="fw-bold mt-3"),
                dbc.Checklist(id="carte-etiquettes", value=donnees.ORDRE_ETIQUETTES, inline=True,
                              options=[{"label": e, "value": e} for e in donnees.ORDRE_ETIQUETTES]),
                html.Label("Département", className="fw-bold mt-3"),
                dcc.Dropdown(id="carte-dept", options=DEPARTEMENTS, value="tous", clearable=False),
                html.Label("Couleur des marqueurs", className="fw-bold mt-3"),
                dbc.RadioItems(id="carte-indicateur", value="part_passoires", options=[
                    {"label": "Part de passoires (F ou G)", "value": "part_passoires"},
                    {"label": "Consommation médiane", "value": "conso_mediane"},
                    {"label": "Nombre de logements", "value": "logements"}]),
                html.Label("Logements minimum par commune", className="fw-bold mt-3"),
                dcc.Slider(id="carte-min", min=1, max=200, step=1, value=10,
                           marks={1: "1", 50: "50", 100: "100", 200: "200"},
                           tooltip={"placement": "bottom", "always_visible": False}),
            ]), className="carte-sans-bordure"), md=3, className="mb-3"),
            dbc.Col([
                dbc.Row(id="carte-kpis", className="mb-3 g-3"),
                dbc.Card(dcc.Graph(id="carte-graphe", config={"scrollZoom": True, "displaylogo": False}),
                         className="carte-sans-bordure mb-3"),
                html.Div(id="carte-detail"),
            ], md=9),
        ]),
        dbc.Row([
            dbc.Col(composants.graphique("carte-top"), md=6, className="mb-3"),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Les communes en détail"),
                dash_table.DataTable(
                    id="carte-table", columns=[{"name": n, "id": i} for n, i in COLONNES_TABLE], page_size=10,
                    sort_action="native", style_table={"overflowX": "auto"},
                    style_cell={"padding": "6px", "fontSize": 13}, style_header={"fontWeight": "bold"}),
                dbc.Button([html.I(className="bi bi-filetype-csv me-1"), "Télécharger les communes (.csv)"],
                           id="carte-csv", color="primary", size="sm", className="mt-3"),
                dcc.Download(id="carte-download"),
            ]), className="carte-sans-bordure h-100"), md=6, className="mb-3"),
        ]),
    ])


def _communes(jeu, etiquettes, departement, minimum):
    df = donnees.filtrer(donnees.charger(), jeu, etiquettes, departement=departement)
    communes = donnees.agreger_communes(df)
    return communes[communes["logements"] >= (minimum or 1)]


@callback(
    Output("carte-graphe", "figure"), Output("carte-kpis", "children"), Output("carte-table", "data"),
    Output("carte-top", "figure"),
    Input("carte-jeu", "value"), Input("carte-etiquettes", "value"), Input("carte-dept", "value"),
    Input("carte-indicateur", "value"), Input("carte-min", "value"))
def mettre_a_jour(jeu, etiquettes, departement, indicateur, minimum):
    communes = _communes(jeu, etiquettes, departement, minimum)
    nb_logements = int(communes["logements"].sum()) if len(communes) else 0
    kpis = [dbc.Col(composants.kpi("communes affichées", f"{len(communes)}", "bi-geo-alt"), md=4),
            dbc.Col(composants.kpi("logements concernés", f"{nb_logements:,}".replace(",", " "), "bi-houses"), md=4),
            dbc.Col(composants.kpi("communes avec plus de 20 % de passoires",
                                   f"{int((communes['part_passoires'] > 20).sum()) if len(communes) else 0}",
                                   "bi-exclamation-triangle"), md=4)]
    tableau = communes.sort_values("logements", ascending=False).round(
        {"conso_mediane": 0, "part_passoires": 1}).to_dict("records")
    return (graphiques.carte_communes(communes, indicateur), kpis, tableau,
            graphiques.top_communes(communes, indicateur))


@callback(
    Output("carte-detail", "children"), Input("carte-graphe", "clickData"),
    State("carte-jeu", "value"), State("carte-etiquettes", "value"), State("carte-dept", "value"))
def detail_commune(clic, jeu, etiquettes, departement):
    if not clic:
        return dbc.Alert([html.I(className="bi bi-hand-index me-2"),
                          "Cliquez sur un marqueur pour voir le détail d'une commune."], color="light")
    commune, dept = clic["points"][0]["customdata"][:2]
    df = donnees.filtrer(donnees.charger(), jeu, etiquettes)
    df = df[(df["commune"] == commune) & (df["departement"] == dept)]
    ind = donnees.indicateurs(df)
    if ind is None:
        return dbc.Alert(f"Aucun logement à {commune} avec ces filtres.", color="warning")
    return dbc.Card(dbc.CardBody([
        html.H5([html.I(className="bi bi-pin-map me-2"), f"{commune} ({dept})"]),
        dbc.Row([
            dbc.Col([html.P([html.B(f"{ind['n']:,}".replace(",", " ")), " logements"]),
                     html.P([html.B(f"{ind['conso_mediane']:.0f}"), " kWhEP/m²/an (médiane)"]),
                     html.P([html.B(f"{ind['part_passoires']:.1%}"), " de passoires (F ou G)"]),
                     html.P([html.B(f"{ind['surface_mediane']:.0f} m²"), " de surface médiane"])], md=4),
            dbc.Col(dcc.Graph(figure=graphiques.etiquettes_commune(df), config={"displayModeBar": False}), md=8),
        ]),
    ]), className="carte-sans-bordure")


@callback(
    Output("carte-download", "data"), Input("carte-csv", "n_clicks"),
    State("carte-jeu", "value"), State("carte-etiquettes", "value"), State("carte-dept", "value"),
    State("carte-min", "value"), prevent_initial_call=True)
def exporter_communes(_, jeu, etiquettes, departement, minimum):
    communes = _communes(jeu, etiquettes, departement, minimum)
    return dcc.send_data_frame(communes.to_csv, "communes.csv", index=False)
