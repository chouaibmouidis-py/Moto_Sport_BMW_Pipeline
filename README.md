# BMW Motorsport data pipeline

Projet personnel pédagogique d'extraction de données publiques de chronométrage
IMSA, avec un premier périmètre sur les engagements BMW à Road America 2025.
Ce projet n'est ni affilié, ni approuvé, ni sponsorisé par BMW, BMW M Motorsport
ou IMSA.

## Source et périmètre

Le document provient du
[portail de résultats IMSA](https://imsa.results.alkamelcloud.com/?evvent=16_Road+America&season=25_2025).
La source sélectionnée est le JSON « Pit Stops Time Cards » de la course du
3 août 2025. L'extraction conserve le document complet ; l'exploration locale
affiche les engagements dont le constructeur est BMW.

Les données observées sont réelles, pas simulées. Une durée d'arrêt publiée
n'est pas nécessairement une durée de ravitaillement ou une perte de temps
par rapport à un véhicule resté en piste. Aucune donnée interne BMW, mesure
d'usure ou prédiction n'est fournie.

L'accès public ne constitue pas une autorisation générale de redistribution.
Les conditions de réutilisation restent à vérifier avant de republier les
fichiers bruts. Ce dépôt n'inclut ni ces fichiers ni les artefacts d'extraction.

## Exécution locale avec uv

Depuis la racine du projet :

```bash
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked python download.py
uv run --locked python inspect_source.py
```

`download.py` effectue une requête HTTP avec timeout, vérifie le statut,
écrit un fichier `.part`, vérifie la syntaxe JSON puis remplace le fichier final.
Une erreur HTTP, un timeout ou un JSON invalide laisse le fichier final précédent
intact dans les scénarios testés. Le script retélécharge la source à chaque
lancement ; il n'implémente ni reprise partielle, ni historique, ni contrôle
de fraîcheur ou de schéma métier complet.

`inspect_source.py` lit le fichier local sans nouvelle requête. Les données se
trouvent sous `data/raw/`, relativement au dossier d'exécution. Elles sont
exclues de Git, comme les fichiers `.env` et l'environnement virtuel.

## GitHub Actions

Le workflow **Validate and extract IMSA source** est uniquement manuel :

1. Publier le dépôt avec le workflow sur sa branche par défaut.
2. Ouvrir **Actions**, sélectionner le workflow, puis **Run workflow**.
3. Vérifier les étapes de tests, de téléchargement et d'inspection.

Il utilise un runner standard Ubuntu, Python 3.12, uv 0.13.0 et `uv.lock`.
Les cinq tests utilisent des réponses HTTP simulées ; seule l'étape
d'extraction contacte la source. Aucun secret Azure ou autre abonnement cloud
n'est requis. Le jeton GitHub a uniquement le droit de lire le dépôt.

Le fichier téléchargé reste sur le disque temporaire du runner et ne constitue
pas un archivage. Il n'est ni commité, ni publié comme artefact. Le chargement
vers un stockage persistant sera une étape séparée. L'écriture temporaire
protège un lancement, pas la persistance entre runners.

Les conditions de gratuité des runners et les quotas GitHub peuvent évoluer :
vérifier le type de dépôt, le plan et les paramètres de facturation avant usage.
La source historique est déclenchée manuellement pour éviter des téléchargements
planifiés sans objectif de collecte défini.

## Prochaines étapes

- Vérifier un premier lancement réel sur GitHub Actions.
- Séparer les paramètres d'événement du code de téléchargement.
- Ajouter des contrôles de structure et une trace de provenance.
- Préparer un chargement indépendant du fournisseur de stockage.
- Construire les transformations SQL et leurs contrôles qualité.

Aucune licence de réutilisation du code n'a encore été choisie ; un dépôt public
ne remplace pas une licence open source. La licence du code et les conditions
d'utilisation des données sont deux sujets distincts.
