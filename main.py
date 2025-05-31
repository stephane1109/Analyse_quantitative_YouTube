# pip install streamlit pandas google-api-python-client XlsxWriter altair
# pip install google-auth-oauthlib

# python -m streamlit run main.py

###
### main.py — YouTube Data v3 • Graph journalièr + Deltas
### =========================================================================
### Affiche, pour chaque jour, le cumul quotidien de vues, likes et commentaires
### sous forme de barres, et conserve les deltas
### (journaliers) dans la DataFrame/Tableau et le fichier Excel.
###

import os
import io
import sqlite3
import toml
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime
from googleapiclient.discovery import build

# Forcer le répertoire courant (cron)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Configuration Streamlit (centrée)
st.set_page_config(page_title='YT v3 • graph journalier', layout='centered')
st.title('YouTube – nbre vues - likes - commentaires')

# Charger les secrets
cfg = toml.load('secrets.toml')
CHEMIN_BDD = os.path.abspath(cfg['sqlite']['chemin'])
CLE_API    = cfg['youtube']['api_key']
ID_VIDEO   = cfg['youtube']['video_id']

# Initialisation SQLite
@st.cache_resource
def init_bdd():
    os.makedirs(os.path.dirname(CHEMIN_BDD) or '.', exist_ok=True)
    conn = sqlite3.connect(CHEMIN_BDD, check_same_thread=False)
    conn.execute(
        'CREATE TABLE IF NOT EXISTS cumul(ts TEXT PRIMARY KEY, vues INTEGER, likes INTEGER, commentaires INTEGER)'
    )
    conn.commit()
    return conn
conn = init_bdd()

# Récupérer cumul via API
def recuperer_cumul() -> dict:
    yt = build('youtube', 'v3', developerKey=CLE_API)
    items = yt.videos().list(part='statistics', id=ID_VIDEO).execute().get('items', [])
    if not items:
        return {}
    s = items[0]['statistics']
    return {
        'ts': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'vues': int(s.get('viewCount', 0)),
        'likes': int(s.get('likeCount', 0)),
        'commentaires': int(s.get('commentCount', 0))
    }

# Enregistrer en base
def enregistrer_cumul(row: dict):
    if not row:
        return
    conn.execute(
        'INSERT OR REPLACE INTO cumul(ts,vues,likes,commentaires) VALUES(?,?,?,?)',
        (row['ts'], row['vues'], row['likes'], row['commentaires'])
    )
    conn.commit()

# Construire DataFrame quotidien + delta en pandas
def obtenir_quotidien() -> pd.DataFrame:
    q = '''
    SELECT date(ts) AS Jour,
           MAX(vues) AS vues,
           MAX(likes) AS likes,
           MAX(commentaires) AS commentaires
    FROM cumul
    GROUP BY date(ts)
    ORDER BY date(ts);
    '''
    df = pd.read_sql_query(q, conn)
    if df.empty:
        return df
    # convertir en chaîne pour usage en catégorie
    df['Jour'] = pd.to_datetime(df['Jour']).dt.strftime('%Y-%m-%d')
    # calcul des deltas
    for m in ['vues', 'likes', 'commentaires']:
        df[f'{m}_delta'] = df[m].diff().fillna(0).astype(int)
    return df

# Tracer barres collées
def tracer_barres(df: pd.DataFrame, metric: str, color: str) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X('Jour:N', title='Date', axis=alt.Axis(labelAngle=-45),
                    scale=alt.Scale(paddingInner=0, paddingOuter=0)),
            y=alt.Y(f'{metric}:Q', title=metric.capitalize()),
            color=alt.value(color),
            tooltip=[
                alt.Tooltip('Jour:N', title='Date'),
                alt.Tooltip(f'{metric}:Q', title=metric.capitalize()),
                alt.Tooltip(f'{metric}_delta:Q', title=f'{metric} Δ')
            ]
        )
        .properties(width={'step': 30}, height=300)
    )

# UI: bouton d'enregistrement
if st.button('Enregistrer cumul du jour'):
    row = recuperer_cumul()
    enregistrer_cumul(row)
    if row:
        st.success(f"Enregistré {row['ts']}")

# Lecture quotidienne
df = obtenir_quotidien()
if df.empty:
    st.info('Aucune donnée.')
    st.stop()

# Score du jour
date_last = df['Jour'].iloc[-1]
st.subheader(f"Score du {date_last}")
today = df.iloc[-1]
cols = st.columns(3)
cols[0].metric('Vues', int(today['vues']), int(today['vues_delta']))
cols[1].metric('Likes', int(today['likes']), int(today['likes_delta']))
cols[2].metric('Commentaires', int(today['commentaires']), int(today['commentaires_delta']))

# Tableau
st.subheader('Données quotidiennes')
st.dataframe(df, use_container_width=True)

# Graphiques simples
st.subheader('Vues par jour')
st.write(tracer_barres(df, 'vues', '#1f77b4'))

st.subheader('Likes par jour')
st.write(tracer_barres(df, 'likes', '#ff7f0e'))

st.subheader('Commentaires par jour')
st.write(tracer_barres(df, 'commentaires', '#2ca02c'))

# Export Excel
buf = io.BytesIO()
df.to_excel(buf, index=False, sheet_name='Jour')
buf.seek(0)
st.download_button('Export Excel', buf, 'stats.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
