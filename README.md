## Lisez-moi

Après avoir fait `pip install -r requirements.txt`, exécuter la commande suivante.

```python
python -m spacy download fr_core_news_sm
```

Pour exécuter le contenu Docker, il faut **définir la variable d'environnement `DISCORD_TOKEN`** qui contient le token d'authentification au serveur Discord.

```bash
docker run -p 8080:8080 -e  econfident:latest
```
