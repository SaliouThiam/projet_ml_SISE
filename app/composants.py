"""Éléments d'interface réutilisés par les pages (cartes d'indicateurs, boutons d'export, alertes)."""

import dash_bootstrap_components as dbc
from dash import dcc, html

# Barre d'outils des graphiques : bouton « appareil photo » (PNG) activé, logo Plotly masqué.
CONFIG_GRAPHE = {"displaylogo": False,
                 "toImageButtonOptions": {"format": "png", "filename": "graphique_dpe", "scale": 2}}


def kpi(titre, valeur, icone):
    """Carte d'indicateur : une valeur en grand, un titre, une icône Bootstrap."""
    return dbc.Card(dbc.CardBody(dbc.Row([
        dbc.Col(html.I(className=f"bi {icone} kpi-icone"), width="auto", className="d-flex align-items-center"),
        dbc.Col([html.Div(valeur, className="kpi-valeur"), html.Div(titre, className="kpi-titre")]),
    ], className="g-2")), className="carte-sans-bordure h-100")


def bouton_png(graphe_id):
    """Bouton « Exporter en PNG » : un callback clientside (app/app.py) déclenche le téléchargement."""
    return html.Div([
        dbc.Button([html.I(className="bi bi-image me-1"), "Exporter en PNG"],
                   id={"type": "png-bouton", "graphe": graphe_id}, size="sm", outline=True, color="secondary"),
        html.Div(id={"type": "png-sortie", "graphe": graphe_id}, style={"display": "none"}),
    ], className="text-end")


def graphique(graphe_id, figure=None):
    """Carte contenant un graphique et son bouton d'export PNG."""
    return dbc.Card(dbc.CardBody([
        dcc.Graph(id=graphe_id, figure=figure if figure is not None else {}, config=CONFIG_GRAPHE),
        bouton_png(graphe_id),
    ]), className="carte-sans-bordure h-100")


def entete(titre, sous_titre, icone):
    return html.Div([
        html.H2([html.I(className=f"bi {icone} me-2"), titre], className="titre-page"),
        html.P(sous_titre, className="text-muted"),
    ], className="mb-3")


def alerte(message, titre="Données ou modèles introuvables"):
    return dbc.Alert([html.H5(titre, className="alert-heading"), html.P(message, className="mb-0")],
                     color="warning", className="mt-3")


def valeur_ou_tiret(valeur, format_):
    return "—" if valeur is None else format(valeur, format_)
