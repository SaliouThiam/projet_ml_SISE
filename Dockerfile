# Image de l'application « DPE Corse » (Dash servi par gunicorn).
#
# Construction (depuis la racine du dépôt) :   docker build -t dpe-corse .
# Lancement en local :                         docker run --rm -p 8050:8050 dpe-corse
# puis ouvrir http://localhost:8050
#
# Prérequis : app/data/logements_app.csv.gz, app/data/formulaire.json et les modèles
# (.joblib) doivent exister dans le dépôt avant la construction (voir la documentation).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

# 1. Dépendances : cette couche est réutilisée tant que requirements-app.txt ne change pas.
COPY requirements-app.txt .
RUN pip install -r requirements-app.txt

# 2. Code, modèles et données légères (les exclusions sont dans .dockerignore).
#    src/ contient le code partagé ET les modèles enregistrés ; les modèles sont rechargés
#    avec les fonctions de src/data/transformateurs.py, qui doivent donc être présentes.
COPY src/ ./src/
COPY app/ ./app/

# 3. Exécution sous un utilisateur sans privilèges.
RUN useradd --create-home appuser && chown -R appuser /code
USER appuser

# Les hébergeurs (Render, Heroku) fournissent le port dans la variable PORT ; 8050 sinon.
ENV PORT=8050
EXPOSE 8050

# Un seul processus (les modèles sont chargés une fois) et plusieurs fils pour les requêtes simultanées.
CMD ["sh", "-c", "gunicorn app.app:server --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120"]