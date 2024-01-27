import logging
import os
import re
import discord
import json
import sys
import asyncio
import sqlite3

from datetime import datetime

from src.model import load_model, predict
from dashboard import query_db_info

load_model()

con = sqlite3.connect("discord.db")

link_ai = "https://moustapha14.github.io/projet-ipssi/"

# dictionnaire global pour suivre les messages haineux par canal
hateful_messages_count = {}  # Structure: { channel_id: [total_messages, hateful_messages] }

# Seuil pour déclencher l'alerte
SEUIL_POURCENTAGE = 0.05  # Par exemple, 20%

message = ("J'ai repéré des messages haineux dans ce salon. \nSi vous êtes témoin ou victime d'une situation "
           "de cyberharcèlement et que vous souhaitez parler, voici notre  chatbot qui répondra à toutes "
           "vos questions concernant votre situation :\n " + link_ai + ".")


def initialize_database():
    cur = con.cursor()
    rep = cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='channels'").fetchone()
    if rep[0] == 0:
        cur.execute("CREATE TABLE channels(channel_id TEXT PRIMARY KEY NOT NULL, name TEXT, num_users INTEGER)")
        cur.execute(
            "CREATE TABLE messages(msg_id TEXT PRIMARY KEY NOT NULL, channel_id TEXT NOT NULL, user_id TEXT, msg TEXT, "
            "label TEXT, score DOUBLE, date TEXT)")


initialize_database()


def insert_message(cursor, msg):
    prediction = predict(msg.content)[0]
    #logging.info(f"Message: {msg.content} - Prediction: {prediction}")
    # Mise à jour des compteurs de messages
    channel_id = msg.channel.id
    if channel_id not in hateful_messages_count:
        hateful_messages_count[channel_id] = [0, 0]
    hateful_messages_count[channel_id][0] += 1  # Incrémente le nombre total de messages

    # Vérifie si le message est haineux et met à jour le compteur
    if prediction["label"].split(" ")[-1] == "hateful":
        hateful_messages_count[channel_id][1] += 1  # Incrémente le nombre de messages haineux

    """
    Insère un nouveau message ou met à jour un ancien message dans la base.
    """

    cursor.execute(
        """
        INSERT INTO messages(msg_id, channel_id, user_id, msg, label, score, date)
        VALUES ('{msg_id}', '{channel_id}', ?, ?, '{label}', {score}, '{date}')
        ON CONFLICT(msg_id) DO UPDATE SET
            msg = ?,
            label = '{label}',
            score = {score}
        """
        .format(
            msg_id=msg.id,
            channel_id=msg.channel.id,
            label=prediction["label"],
            score=prediction["score"],
            date=msg.created_at.strftime("%Y-%m-%dT%H:%M:%S")
        ),
        [str(msg.author), msg.content, msg.content]
    )


# Fonction pour vérifier périodiquement les messages haineux
async def check_and_send_message():
    while True:  # Boucle infinie pour vérifier périodiquement
        for channel_id, (total, hateful) in hateful_messages_count.items():
            try:
                channel = client.get_channel(channel_id)
                if channel and (hateful / total) >= SEUIL_POURCENTAGE:
                    # Récupérer les 50 derniers messages pour vérifier si le message a déjà été envoyé
                    messages = channel.history(limit=50, oldest_first=False)
                    non_present = False
                    async for msg in messages:
                        if msg.content == message:
                            non_present = True
                            break
                    if not non_present:
                        # On envoie le message
                        await on_hate_message(channel_id)
            except Exception as e:
                logging.info(f"Erreur lors de la vérification du canal {channel_id}: {e}")

        await asyncio.sleep(60)  # Attendre 60 secondes avant de répéter


# Fonction d'alerte sur les messages haineux
async def on_hate_message(num_channel):
    try:
        channel = client.get_channel(num_channel)
        if channel:  # Vérifie si le canal existe
            await channel.send(message)
        else:
            print(f"Erreur : Canal introuvable avec l'ID {num_channel}")
    except Exception as e:
        print(f"Une erreur est survenue lors de l'envoi du message : {e}")


class EconfidentBot(discord.Client):
    callbacks = []

    def add_callback(self, callback):
        self.callbacks.append(callback)

    async def on_ready(self):
        logging.info(f"Connecté à Discord en tant que {self.user}!")
        cursor = con.cursor()

        for guild in client.guilds:
            # On récupère tous les channels de texte
            for channel in guild.text_channels:
                if channel.name in ["rules", "moderator-only"]:
                    continue
                cursor.execute(
                    """
                    INSERT INTO channels(channel_id, name, num_users)
                    VALUES ('{id}', ?, {num_users})
                    ON CONFLICT(channel_id) DO UPDATE SET
                        name = ?,
                        num_users = {num_users}
                    """
                    .format(
                        id=channel.id,
                        num_users=len(channel.members)
                    ),
                    [channel.name, channel.name]
                )
                con.commit()

                # On récupère tous les messages du channel
                messages = channel.history(limit=None, oldest_first=False)
                async for msg in messages:
                    # On refait une prédiction sur chaque ancien message au cas où on change de modèle
                    insert_message(cursor, msg)
                con.commit()

        # On lance la vérification des messages haineux
        await self.loop.create_task(check_and_send_message())

    async def on_message(self, msg):
        insert_message(con.cursor(), msg)
        con.commit()


intents = discord.Intents.default()
intents.message_content = True
client = EconfidentBot(intents=intents)
client.run(os.environ["DISCORD_TOKEN"]) # use  if you want to use the token from the environment variables
