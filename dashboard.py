import logging

import discord
import streamlit as st
import asyncio
import os
import time
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
import math

# Pour rafraîchir automatiquement le Dashboard
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

st.set_page_config(layout="wide", page_title="E-Confident", page_icon=":robot_face:", initial_sidebar_state="expanded")

custom_css = """
<style>
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: lightblue;
        box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
        /* autres styles */
    }
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

last_length = 0

channels = []
messages = []
bullies = {}  # Les potentiels harceleurs

n_previous_messages = 50
n_elapsed_time = 30  # On prend en compte du cyberharcèlement lorsque les messages sont rapprochés en plage de 30 mn

# On rafraîchit le Dashboard toutes les 3 secondes à l'infinibbbbc
_ = st_autorefresh(interval=3000, limit=None, key="refresh")


def query_db_info():
    global channels
    global messages
    try:
        con = sqlite3.connect("discord.db")
        cur = con.cursor()
        channels = [
            dict(zip(["channel_id", "name", "num_users"], row))
            for row in cur.execute("SELECT * FROM channels").fetchall()
        ]
        messages = [
            dict(zip(["msg_id", "channel_id", "user_id", "msg", "label", "score", "date"], row))
            for row in cur.execute("SELECT * FROM messages").fetchall()
        ]
        con.close()
    except Exception:
        print("Impossible de lire les messages depuis la base SQLite.")

    for msg in messages:
        if msg["label"].split(" ")[-1] == "hateful":
            bullies[msg["user_id"]] = bullies.get(msg["user_id"], 0) + 1

    # On va calculer la proportion de messages haineux sur chaque channels (on ne prenant que les n derniers messages)
    prev_date = None
    for i, channel in enumerate(channels):
        channels[i]["bully_p"] = 0
        num_msg = 0
        for msg in messages[:n_previous_messages]:
            if msg["channel_id"] != channel["channel_id"]:
                continue

            num_msg += 1
            msg["date"] = datetime.strptime(msg["date"], "%Y-%m-%dT%H:%M:%S")
            if msg["label"].split(" ")[-1] == "hateful":
                coef = 1
                if prev_date:
                    delay = (msg["date"] - prev_date).total_seconds() / 60
                    # Plus l'écart entre deux messages successifs est court, plus il y a un acharnement en même temps
                    # À l'inverse, plus l'écart est grand, plus le cyberharcèlement n'est "plus d'actualité"
                    if delay > n_elapsed_time:
                        coef = math.exp(-delay)
                channels[i]["bully_p"] += coef
                prev_date = msg["date"]

        # Cela donne la proportion de messages haineux parmi les n_previous_messages derniers messages
        if num_msg > 0:
            channels[i]["bully_p"] /= num_msg

    con.close()


# On trie les channels par ordre décroissant de proportion de messages haineux
channels = sorted(channels, key=lambda x: x["bully_p"], reverse=True)

# On trie les potentiels harceleurs par ordre décroissant de nombre de messages haineux
bullies = dict(sorted(bullies.items(), key=lambda x: x[1], reverse=True))

# Utilisez st.title() pour ajouter le titre centré
st.title("Dashboard Econfident")

col1, col2 = st.columns(2)

with col1:
    st.markdown("<div id='param'>", unsafe_allow_html=True)
    st.write("## Paramètres")
    subcols = st.columns(2)
    n_previous_messages = subcols[0].slider("Nombre de messages par salon", 0, 200, 50)
    n_elapsed_time = subcols[1].slider("Fréquence successive (minutes)", 0, 300, 30)
    query_db_info()
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("## Analyse des salons")
    subcols = st.columns(2)
    for i, channel in enumerate(channels):
        i_col = i % 2
        with subcols[i_col]:
            st.markdown("<h4 style='text-align:center;'>Salon #{}</h4>".format(channel["name"]), unsafe_allow_html=True)
            if channel["num_users"] == 1:
                st.markdown(
                    "<p style='text-align:center;font-size:1.3rem;'>{} utilisateur</p>".format(channel["num_users"]),
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    "<p style='text-align:center;font-size:1.3rem;'>{} utilisateurs</p>".format(channel["num_users"]),
                    unsafe_allow_html=True)
            fig = go.Figure()
            fig.update_layout(
                margin=dict(l=15, r=15, t=20, b=20),
                height=180
            )
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=channel["bully_p"] * 100,
                number={"suffix": "%", "font": {"color": 'green' if channel["bully_p"] < 0.3 else (
                    'orange' if channel["bully_p"] < 0.7 else 'red')}},
                gauge={
                    'axis': {'range': [0, 100], 'nticks': 20},
                    'bar': {'color': 'green' if channel["bully_p"] < 0.3 else (
                        'orange' if channel["bully_p"] < 0.7 else 'red')},
                    'steps': [
                        {'range': [0, 30], 'color': "lightgreen"},
                        {'range': [30, 70], 'color': "rgb(255, 255, 150)"},
                        {'range': [70, 100], 'color': "rgb(255, 150, 150)"}
                    ]
                },
                domain={'row': 0, 'column': 1}))

            st.plotly_chart(fig, use_container_width=True)

with col2:
    st.write("## Statistiques")
    # Update dashboard
    cols = st.columns(3)
    cols[0].metric(label="Nombre de messages", value=len(messages))

    # TODO : Traiter les messages ici pour voir s'il y a cyberharcèlement
    num_hate = len([1 for msg in messages if msg["label"].split(" ")[-1] == "hateful"])
    cols[1].metric(label="Nombre de messages haineux", value=num_hate)

    num_users = len(set([msg["user_id"] for msg in messages]))
    cols[2].metric(label="Nombre d'utilisateurs", value=num_users)

    categories = [msg["label"] for msg in messages if msg["label"].split(" ")[-1] == "hateful"]
    categories_count = {}
    for cat in categories:
        category = cat.split(" ")[0]
        categories_count[category] = categories_count.get(category, 0) + 1 / len(categories) * 100

    st.write("#### Liste des potentiels harceleurs")
    bullies_array = [
        {
            "Utilisateur": x,
            "Nombre de messages haineux": y
        } for x, y in bullies.items()
    ]
    st.table(pd.DataFrame.from_dict(bullies_array))

    # Conversion des données pour le diagramme en camembert
    df = pd.DataFrame({
        "Catégories détectées": list(categories_count.keys()),
        "Pourcentage": list(categories_count.values())
    })

    # Création du diagramme en camembert
    fig = px.pie(
        df,
        names='Catégories détectées',
        values='Pourcentage',
        color='Catégories détectées',  # Assigner des couleurs différentes en fonction des catégories
        title="Répartition des Catégories de Messages Haineux"
    )

    # Mise à jour de la mise en page si nécessaire
    fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))

    # Affichage du graphique
    st.write("#### Répartition des catégories de messages haineux")
    st.plotly_chart(fig, use_container_width=True)





