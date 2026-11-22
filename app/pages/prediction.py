"""Page « Prédiction » : estimation de l'étiquette DPE et de la consommation d'un logement."""

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, dcc, html

from app import composants, graphiques
from app.libelles import GROUPES, groupe_variable, libelle_modalite, libelle_variable
from src.models.predict import PredicteurIndisponible, obtenir_predicteur

dash.register_page(__name__, path="/prediction", name="Prédiction", title="DPE Corse · Prédiction",
                   order=3, icon="bi-calculator")

AVERTISSEMENT = ("Estimation indicative fournie par un modèle statistique entraîné sur des DPE de Corse. "
                 "Elle ne remplace pas un diagnostic réalisé par un professionnel.")


def _champ(predicteur, variable):
    """Un champ de formulaire : nombre pour une variable numérique, liste de choix sinon."""
    identifiant = {"type": "champ", "nom": variable}
    if variable in predicteur.numeriques:
        info = predicteur.formulaire["numeriques"][variable]
        composant = dbc.Input(id=identifiant, type="number", placeholder=f"ex. {info['mediane']:.0f}")
    else:
        choix = predicteur.formulaire["categorielles"].get(variable, [])
        composant = dcc.Dropdown(id=identifiant, placeholder="Je ne sais pas", clearable=True,
                                 options=[{"label": libelle_modalite(c["valeur"]), "value": c["valeur"]} for c in choix])
    return dbc.Col([html.Label(libelle_variable(variable), className="small fw-bold"), composant],
                   md=6, className="mb-3")


def layout():
    try:
        predicteur = obtenir_predicteur()
    except PredicteurIndisponible as erreur:
        return composants.alerte(str(erreur), "Modèles introuvables")

    par_groupe = {g: [] for g in list(GROUPES) + ["Autres informations"]}
    for variable in predicteur.variables:
        par_groupe[groupe_variable(variable)].append(variable)
    sections = [dbc.AccordionItem(dbc.Row([_champ(predicteur, v) for v in variables]), title=groupe)
                for groupe, variables in par_groupe.items() if variables]

    return html.Div([
        composants.entete("Estimer l'étiquette et la consommation d'un logement",
                          "Renseignez ce que vous connaissez : les champs laissés vides sont traités comme « inconnu ».",
                          "bi-calculator"),
        dbc.Row([
            dbc.Col([
                dbc.Accordion(sections, always_open=True, active_item=[f"item-{i}" for i in range(len(sections))]),
                html.Div([
                    dbc.Button([html.I(className="bi bi-calculator me-1"), "Estimer"], id="pred-bouton",
                               color="primary", size="lg", className="me-2"),
                    dbc.Button([html.I(className="bi bi-arrow-counterclockwise me-1"), "Effacer"], id="pred-reset",
                               color="secondary", outline=True),
                ], className="mt-3"),
            ], md=7, className="mb-3"),
            dbc.Col(dcc.Loading(html.Div(id="pred-resultat", children=_message_initial())), md=5),
        ]),
    ])


def _message_initial():
    return dbc.Card(dbc.CardBody([
        html.Img(src=dash.get_asset_url("echelle_dpe.svg"), alt="Échelle DPE", style={"width": "100%", "maxWidth": "320px"}),
        html.P("Le résultat s'affichera ici après avoir cliqué sur « Estimer ».", className="text-muted mt-3 mb-0"),
    ]), className="carte-sans-bordure text-center")


def _afficher(resultat, explication, surface):
    etiquette = resultat["etiquette"]
    conso = resultat["consommation"]
    lignes = [html.H3(f"{conso:.0f} kWhEP/m²/an", className="mb-1")]
    if resultat["fourchette"]:
        bas, haut = resultat["fourchette"]
        lignes.append(html.P(f"Fourchette habituelle : {bas:.0f} à {haut:.0f} (80 % des estimations s'écartent "
                             f"de moins de {haut - conso:.0f} de la réalité conventionnelle).", className="text-muted small"))
    if surface and surface > 0:
        lignes.append(html.P(f"Soit environ {conso * surface:,.0f} kWh d'énergie primaire par an pour {surface:.0f} m²."
                             .replace(",", " ")))
    if not resultat["coherent"]:
        lignes.append(dbc.Alert(
            f"La consommation estimée correspond plutôt à la classe {resultat['etiquette_consommation']} d'après les "
            f"seuils officiels : l'estimation est proche d'un seuil. L'étiquette DPE tient aussi compte des "
            f"émissions de gaz à effet de serre.", color="info", className="small"))
    return html.Div([
        dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col(html.Div(etiquette, className=f"badge-dpe dpe-{etiquette}"), width="auto"),
            dbc.Col([html.Div("Étiquette estimée", className="kpi-titre"), *lignes]),
        ])), className="carte-sans-bordure mb-3"),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=graphiques.probabilites(resultat["probabilites"], etiquette),
                                        config={"displayModeBar": False})), className="carte-sans-bordure mb-3"),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=graphiques.contributions(explication),
                                        config={"displayModeBar": False})), className="carte-sans-bordure mb-3"),
        html.P(AVERTISSEMENT, className="pied-de-page"),
    ])


@callback(
    Output("pred-resultat", "children"), Input("pred-bouton", "n_clicks"),
    State({"type": "champ", "nom": ALL}, "value"), State({"type": "champ", "nom": ALL}, "id"),
    prevent_initial_call=True)
def estimer(_, valeurs, identifiants):
    saisie = {i["nom"]: v for i, v in zip(identifiants, valeurs)}
    try:
        surface_m2 = float(saisie.get("surface_habitable_logement"))
    except (TypeError, ValueError):
        surface_m2 = None
    if not surface_m2 or surface_m2 <= 0:
        return dbc.Alert("Renseignez une surface habitable valide (nombre positif).", color="warning")
    predicteur = obtenir_predicteur()
    try:
        resultat = predicteur.predire(saisie)
        explication = predicteur.expliquer(saisie)
    except Exception as erreur:                      # saisie inattendue : on l'indique sans planter l'application
        return dbc.Alert(f"Estimation impossible avec ces valeurs ({erreur}).", color="danger")
    return _afficher(resultat, explication, surface_m2)


@callback(
    Output({"type": "champ", "nom": ALL}, "value"), Output("pred-resultat", "children", allow_duplicate=True),
    Input("pred-reset", "n_clicks"), prevent_initial_call=True)
def effacer(_):
    nombre = len(dash.callback_context.outputs_list[0])
    return [None] * nombre, _message_initial()
