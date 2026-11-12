# Manifeste de sources

`sources.json` est un inventaire initial, pas la liste complète des courses BMW.
Il est lu par les scripts d'inspection, de construction Bronze et d'analyse.
Ils sélectionnent les documents activés (`enabled: true`) par famille :
`pit_stops` pour les arrêts, `classification` pour les classements.
Les trois rapports IMSA 2025 — Road America, Long Beach et Daytona heure 24 —
ont traversé le pipeline local et contiennent des engagements BMW vérifiés.
Le classement Official de Road America 2025 est aussi intégré : 48 participants,
dont cinq BMW, rapprochés des comptages d'arrêts de la même session.
Le manifeste seul ne déclenche rien : les téléchargements sont effectués par
`inspect_manifest.py` et `inspect_classification.py`, directement ou via
`run_pipeline.py`.

Les classements doivent fournir `filename`, par exemple
`03_Results_Race_Official.JSON`. Le téléchargeur reçoit ce nom explicitement.
Le parcours des arrêts conserve son nom de fichier historique par défaut.
`pipeline_status` décrit l'état de qualification ; il ne sert pas à exclure
un document déjà testé des exécutions suivantes.

Le rapprochement associe les documents sur `championship`, `season`, `event_id`
et `session_id` ; `source_id` reste propre à chaque document. Un classement
sans rapport d'arrêts compatible, ou avec plusieurs candidats, est refusé.
Le constructeur commun accepte pour l'instant exactement un classement activé ;
le chargement de plusieurs classements dans une même exécution reste à implémenter.

Les saisons sont une cible de couverture, pas une preuve d'ingestion.
`documents` référence des fichiers précis. `catalogs_to_explore` contient des
portails à explorer et ne doit pas être traité comme une liste de JSON à lire.
Les autres championnats candidats restent recensés dans
`../docs/coverage_plan.fr.md`.

Le `session_id` provient du libellé de dossier source. Il ne prouve pas un
horodatage UTC. `publication_status` reste `unspecified` lorsque le nom du
rapport ne porte pas explicitement un statut. Hour 24 désigne un rapport
horaire, pas une course supplémentaire.

`source_id` est l'identité logique choisie pour un rapport. L'ingestion enregistre
la date de téléchargement et l'empreinte SHA-256 dans le fichier `metadata.json`
voisin du document Raw. Un rafraîchissement remplace ces fichiers ; cela ne
constitue pas un archivage immuable des révisions publiées à la même URL.
La date `as_of_date` est celle de cet inventaire, pas la date de récupération
de chaque fichier. Les résultats Silver conservent séparément l'empreinte du
fichier Bronze utilisé.

Avant de démarrer ses étapes, `run_pipeline.py` vérifie les `source_id` dans
toute la liste `documents`, y compris les entrées désactivées. Chaque identifiant
doit être présent, non nul, de type chaîne, non vide et non composé uniquement
d'espaces. Une valeur invalide déclenche une `ValueError` qui indique la
position du document dans la liste (index à partir de zéro) et la raison du refus.
Les doublons sont également refusés avec un message qui nomme l'identifiant.
Le validateur ne modifie pas les valeurs et ne vérifie pas le contenu des rapports.
Ces erreurs empêchent le démarrage des scripts.
Les lancements isolés de ces scripts ne passent pas
automatiquement par ce contrôle du lanceur.
La validation complète des champs obligatoires et des formats autorisés reste
à ajouter. Les contrôles des données du pipeline sont distincts des statuts
descriptifs renseignés dans ce fichier.
