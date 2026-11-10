# Manifeste de sources

`sources.json` est un inventaire initial, pas la liste complète des courses BMW.
Il est lu par les scripts d'inspection, de construction Bronze et d'analyse.
Ils sélectionnent les documents activés (`enabled: true`) de type `pit_stops`.
Les trois rapports IMSA 2025 — Road America, Long Beach et Daytona heure 24 —
ont traversé le pipeline local et contiennent des engagements BMW vérifiés.
Le manifeste seul ne déclenche rien : les téléchargements sont effectués par
`inspect_manifest.py`, directement ou via `run_pipeline.py`.

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

La validation complète du manifeste — champs obligatoires, unicité des
identifiants et formats autorisés — reste à ajouter. Les contrôles des données
du pipeline sont distincts des statuts descriptifs renseignés dans ce fichier.
