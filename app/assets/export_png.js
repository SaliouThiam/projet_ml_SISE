// Exporte un graphique Plotly en PNG depuis le navigateur.
// Appelé par un callback Dash « clientside » (voir app/app.py).
window.dash_clientside = Object.assign({}, window.dash_clientside, {
  export: {
    png: function (nClicks, id) {
      if (!nClicks) { return window.dash_clientside.no_update; }
      var conteneur = document.getElementById(id.graphe);
      if (conteneur && window.Plotly) {
        var graphe = conteneur.getElementsByClassName('js-plotly-plot')[0] || conteneur;
        window.Plotly.downloadImage(graphe, {format: 'png', filename: id.graphe, width: 1200, height: 700});
      }
      return String(nClicks);
    }
  }
});
