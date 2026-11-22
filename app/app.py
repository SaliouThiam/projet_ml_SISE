"""
Point d'entrée de l'application Dash « DPE Corse ».

Lancement en local, depuis la racine du dépôt :
    python -m app.app
puis ouvrir http://127.0.0.1:8050

Déploiement (Render, Heroku…), depuis la racine du dépôt :
    gunicorn app.app:server
"""

from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import ClientsideFunction, Dash, Input, MATCH, Output, State, html

DOSSIER_APP = Path(__file__).resolve().parent

app = Dash(
    __name__,
    use_pages=True,
    pages_folder=str(DOSSIER_APP / "pages"),
    assets_folder=str(DOSSIER_APP / "assets"),
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,          # les composants des pages ne sont pas dans la mise en page initiale
    title="DPE Corse",
    update_title=None,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server                              # objet WSGI utilisé par gunicorn


def barre_navigation():
    """Barre de navigation construite à partir des pages enregistrées (ordre et icône définis dans chaque page)."""
    pages = sorted(dash.page_registry.values(), key=lambda p: p.get("order", 99))
    liens = [dbc.NavLink([html.I(className=f"bi {p.get('icon', 'bi-circle')} me-1"), p["name"]],
                         href=p["relative_path"], active="exact") for p in pages]
    return dbc.Navbar(dbc.Container([
        html.A(dbc.Row([
            dbc.Col(html.Img(src=dash.get_asset_url("logo.svg"), alt="Logo", height="34px")),
            dbc.Col(dbc.NavbarBrand("DPE Corse", className="ms-2 text-white fw-bold")),
        ], align="center", className="g-0"), href="/", style={"textDecoration": "none"}),
        dbc.Nav(liens, navbar=True, className="ms-auto"),
    ]), className="barre-navigation", dark=True)


def mise_en_page():
    return html.Div([
        barre_navigation(),
        dbc.Container(dash.page_container, className="py-4"),
        dbc.Container(html.Hr(), className="mt-4"),
        dbc.Container(html.P([
            "Projet Python / ML, Master 2 SISE (Université Lumière Lyon 2). Données : ADEME, DPE logements "
            "existants et neufs (data.ademe.fr). Les valeurs de consommation sont des valeurs conventionnelles."],
            className="pied-de-page"), className="pb-4"),
    ])


app.layout = mise_en_page    # fonction : la barre est construite quand toutes les pages sont enregistrées

# Export PNG des graphiques : le navigateur génère l'image (assets/export_png.js), sans bibliothèque serveur.
app.clientside_callback(
    ClientsideFunction(namespace="export", function_name="png"),
    Output({"type": "png-sortie", "graphe": MATCH}, "children"),
    Input({"type": "png-bouton", "graphe": MATCH}, "n_clicks"),
    State({"type": "png-bouton", "graphe": MATCH}, "id"),
    prevent_initial_call=True,
)

if __name__ == "__main__":
    app.run(debug=True)
