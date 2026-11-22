"""Fabrication des figures Plotly de l'application (fonctions pures : un tableau en entrée, une figure en sortie)."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app import donnees
from app.libelles import libelle_modalite

# Couleurs de l'échelle DPE, de A (vert) à G (rouge).
COULEURS_DPE = {"A": "#319834", "B": "#33cc31", "C": "#cbfc34", "D": "#fbfe06",
                "E": "#fbcc05", "F": "#fc9935", "G": "#fc0205"}
GABARIT = "plotly_white"
INDICATEURS = {
    "conso": "Consommation (kWhEP/m²/an)",
    "ges": "Émissions de GES (kg CO₂/m²/an)",
}


def _mise_en_forme(fig, titre, hauteur=380):
    fig.update_layout(title={"text": titre, "font": {"size": 15}}, template=GABARIT, height=hauteur,
                      margin={"l": 10, "r": 10, "t": 50, "b": 10}, legend_title_text="")
    return fig


def figure_vide(message="Aucun logement ne correspond à ces filtres", hauteur=380):
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font={"size": 15, "color": "#777"})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(template=GABARIT, height=hauteur, margin={"l": 10, "r": 10, "t": 30, "b": 10})
    return fig


# ----------------------------------------------------------------------------- Contexte / Exploration
def repartition_etiquettes(df):
    """Barres : part de chaque étiquette DPE."""
    if df.empty:
        return figure_vide()
    comptes = df["etiquette"].value_counts().reindex(donnees.ORDRE_ETIQUETTES).fillna(0)
    parts = comptes / comptes.sum() * 100
    fig = go.Figure(go.Bar(
        x=donnees.ORDRE_ETIQUETTES, y=parts.to_numpy(),
        marker_color=[COULEURS_DPE[e] for e in donnees.ORDRE_ETIQUETTES],
        text=[f"{p:.1f} %" for p in parts], textposition="outside",
        customdata=comptes.to_numpy(),
        hovertemplate="Étiquette %{x}<br>%{customdata:,.0f} logements<extra></extra>"))
    fig.update_yaxes(title="Part des logements (%)", range=[0, max(parts.max() * 1.18, 5)])
    fig.update_xaxes(title="Étiquette DPE")
    return _mise_en_forme(fig, "Répartition des étiquettes DPE")


def repartition_jeux(df):
    """Anneau : logements existants et neufs."""
    if df.empty:
        return figure_vide()
    comptes = df["jeu"].value_counts()
    fig = px.pie(names=[libelle_modalite(j) for j in comptes.index], values=comptes.to_numpy(), hole=0.55,
                 color_discrete_sequence=["#2c7fb8", "#7fcdbb"])
    fig.update_traces(textinfo="percent+label", hovertemplate="%{label}<br>%{value:,.0f} logements<extra></extra>")
    fig.update_layout(showlegend=False)
    return _mise_en_forme(fig, "Logements existants et neufs")


def serie_mensuelle(df):
    """Courbe : nombre de DPE reçus par mois."""
    mensuel = df.loc[df["mois"].astype(str).str.match(r"^\d{4}-\d{2}$"), "mois"].value_counts().sort_index()
    if mensuel.empty:
        return figure_vide()
    fig = px.line(x=mensuel.index, y=mensuel.to_numpy(), markers=True)
    fig.update_traces(line_color="#2c7fb8", hovertemplate="%{x}<br>%{y:,.0f} DPE<extra></extra>")
    fig.update_xaxes(title="Mois de réception du DPE")
    fig.update_yaxes(title="Nombre de DPE")
    return _mise_en_forme(fig, "DPE reçus par mois")


def histogramme(df, colonne="conso"):
    """Histogramme de la consommation ou des émissions (tronqué au 99e centile)."""
    valeurs = df[colonne].dropna()
    if valeurs.empty:
        return figure_vide()
    valeurs = valeurs[valeurs <= valeurs.quantile(0.99)]
    fig = px.histogram(x=valeurs, nbins=40, color_discrete_sequence=["#2c7fb8"])
    fig.add_vline(x=float(valeurs.median()), line_dash="dash", line_color="#d62728",
                  annotation_text=f"médiane {valeurs.median():.0f}", annotation_position="top right")
    fig.update_xaxes(title=INDICATEURS[colonne])
    fig.update_yaxes(title="Nombre de logements")
    return _mise_en_forme(fig, f"Distribution : {INDICATEURS[colonne].split(' (')[0].lower()}")


def boite(df, colonne="conso"):
    """Boîtes à moustaches par énergie de chauffage (énergies présentes dans au moins 30 logements)."""
    base = df.dropna(subset=[colonne, "energie_chauffage"])
    tailles = base["energie_chauffage"].value_counts()
    base = base[base["energie_chauffage"].isin(tailles[tailles >= 30].index)]
    if base.empty:
        return figure_vide("Pas assez de logements pour comparer les énergies")
    ordre = base.groupby("energie_chauffage")[colonne].median().sort_values().index.tolist()
    base = base.assign(energie=base["energie_chauffage"].map(libelle_modalite))
    fig = px.box(base, x="energie", y=colonne, points=False, color_discrete_sequence=["#2c7fb8"],
                 category_orders={"energie": [libelle_modalite(o) for o in ordre]})
    fig.update_xaxes(title="Énergie principale de chauffage")
    fig.update_yaxes(title=INDICATEURS[colonne])
    return _mise_en_forme(fig, "Selon l'énergie de chauffage")


def nuage(df, colonne="conso", n_max=2000):
    """Nuage de points : surface et consommation, coloré par étiquette (échantillon)."""
    base = df.dropna(subset=["surface", colonne])
    base = base[base["surface"] <= 400]
    if base.empty:
        return figure_vide()
    if len(base) > n_max:
        base = base.sample(n_max, random_state=0)
    fig = px.scatter(base, x="surface", y=colonne, color=base["etiquette"].astype(str),
                     color_discrete_map=COULEURS_DPE, opacity=0.6,
                     category_orders={"color": donnees.ORDRE_ETIQUETTES},
                     hover_data={"commune": True, "periode": True})
    fig.update_traces(marker={"size": 6})
    fig.update_xaxes(title="Surface habitable (m²)")
    fig.update_yaxes(title=INDICATEURS[colonne])
    return _mise_en_forme(fig, f"Surface et {INDICATEURS[colonne].split(' (')[0].lower()} ({len(base):,} logements)")


def carte_chaleur(df):
    """Carte de chaleur : part de chaque étiquette selon la période de construction."""
    base = df.dropna(subset=["periode"])
    if base.empty:
        return figure_vide()
    table = pd.crosstab(base["periode"], base["etiquette"].astype(str), normalize="index") * 100
    table = table.reindex(columns=donnees.ORDRE_ETIQUETTES, fill_value=0)
    table = table.loc[donnees.trier_periodes(table.index)]
    fig = px.imshow(table, text_auto=".0f", aspect="auto", color_continuous_scale="Blues",
                    labels={"x": "Étiquette", "y": "Période de construction", "color": "% de la période"})
    fig.update_layout(coloraxis_showscale=False)
    return _mise_en_forme(fig, "Étiquettes selon la période de construction (%)")


# ----------------------------------------------------------------------------- Carte
INDICATEURS_CARTE = {
    "part_passoires": ("Part de passoires (F ou G, en %)", "YlOrRd"),
    "conso_mediane": ("Consommation médiane (kWhEP/m²/an)", "YlOrRd"),
    "logements": ("Nombre de logements", "Blues"),
}


def carte_communes(communes, indicateur="part_passoires"):
    """Carte interactive : un marqueur par commune (taille : effectif, couleur : indicateur choisi)."""
    if communes.empty:
        return figure_vide("Aucune commune ne correspond à ces filtres", hauteur=620)
    titre, echelle = INDICATEURS_CARTE[indicateur]
    fig = px.scatter_map(
        communes, lat="lat", lon="lon", size="logements", color=indicateur, color_continuous_scale=echelle,
        hover_name="commune", size_max=30, zoom=7.3, center={"lat": 42.15, "lon": 9.1},
        custom_data=["commune", "departement"], map_style="open-street-map",
        hover_data={"lat": False, "lon": False, "logements": ":,.0f", "conso_mediane": ":.0f",
                    "part_passoires": ":.1f"},
        labels={indicateur: titre, "logements": "Logements", "conso_mediane": "Conso médiane",
                "part_passoires": "% passoires"})
    fig.update_layout(height=620, margin={"l": 0, "r": 0, "t": 0, "b": 0}, coloraxis_colorbar={"title": ""},
                      clickmode="event+select")
    return fig


def top_communes(communes, indicateur="part_passoires", n=10):
    """Barres : les communes en tête selon l'indicateur."""
    if communes.empty:
        return figure_vide(hauteur=340)
    titre, _ = INDICATEURS_CARTE[indicateur]
    top = communes.nlargest(n, indicateur).iloc[::-1]
    fig = px.bar(top, x=indicateur, y="commune", orientation="h", color_discrete_sequence=["#2c7fb8"],
                 hover_data={"logements": ":,.0f"})
    fig.update_xaxes(title=titre)
    fig.update_yaxes(title="")
    return _mise_en_forme(fig, f"Les {len(top)} premières communes", hauteur=340)


def etiquettes_commune(df):
    """Barres : répartition des étiquettes dans une commune."""
    fig = repartition_etiquettes(df)
    fig.update_layout(height=260, title=None, margin={"l": 10, "r": 10, "t": 10, "b": 10})
    return fig


# ----------------------------------------------------------------------------- Prédiction
def probabilites(probas, etiquette):
    """Barres : probabilité estimée de chaque étiquette (la plus probable est en couleur pleine)."""
    lettres = donnees.ORDRE_ETIQUETTES
    valeurs = [probas.get(l, 0.0) * 100 for l in lettres]
    fig = go.Figure(go.Bar(
        x=lettres, y=valeurs, marker_color=[COULEURS_DPE[l] for l in lettres],
        marker_opacity=[1.0 if l == etiquette else 0.35 for l in lettres],
        text=[f"{v:.0f} %" for v in valeurs], textposition="outside",
        hovertemplate="Étiquette %{x} : %{y:.1f} %<extra></extra>"))
    fig.update_yaxes(title="Probabilité estimée (%)", range=[0, 110])
    fig.update_xaxes(title="Étiquette DPE")
    return _mise_en_forme(fig, "Probabilité de chaque étiquette", hauteur=320)


def contributions(tableau):
    """Barres : contribution de chaque variable renseignée (rouge : augmente la consommation)."""
    from app.libelles import libelle_variable
    if tableau.empty:
        return figure_vide("Renseignez des informations pour voir leur effet", hauteur=300)
    t = tableau.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=t["contribution"], y=[libelle_variable(v) for v in t["variable"]], orientation="h",
        marker_color=["#d62728" if c > 0 else "#1f77b4" for c in t["contribution"]],
        hovertemplate="%{y} : %{x:+.0f} kWhEP/m²/an<extra></extra>"))
    fig.update_xaxes(title="Effet sur la consommation estimée (kWhEP/m²/an)", zeroline=True)
    return _mise_en_forme(fig, "Pourquoi cette estimation ? (par rapport à un logement de référence)", hauteur=320)
