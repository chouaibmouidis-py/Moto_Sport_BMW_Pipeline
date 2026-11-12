# BMW Motorsport data pipeline

Projet personnel de data engineering construit comme une mission de stage
simulée : transformer des rapports officiels de compétition en données
traçables et contrôlées, puis analyser les engagements BMW et leurs arrêts.
Le projet n'est ni affilié, ni approuvé, ni sponsorisé par BMW ou IMSA.
La [fiche de mission](docs/mission_stage_personnel.fr.md) définit le périmètre,
les livrables et les critères d'acceptation.

## Ce que le projet traite aujourd'hui

Vingt-deux documents JSON du portail officiel
[IMSA / Al Kamel](https://imsa.results.alkamelcloud.com/) sont configurés dans
[`config/sources.json`](config/sources.json) : onze rapports « Pit Stops Time
Cards » et onze classements Official, pour Road America, Long Beach, Daytona,
Laguna Seca, Detroit, Sebring, Watkins Glen, Canadian Tire Motorsport Park et
VIR, Indianapolis et Road Atlanta 2025. Les rapports finaux sont
retenus pour Daytona (heure 24), Sebring (heure 12) et Watkins Glen (heure 6),
ainsi qu'Indianapolis (heure 6) et Road Atlanta (heure 10), sans additionner les
états horaires. Les onze courses du calendrier sont intégrées pour ces deux
familles de rapports ; le
[suivi de couverture](docs/imsa_2025_season_coverage.fr.md) distingue les lots.

| Rapport 2025 | Entrées de voitures | Entrées de pilotes | Arrêts | Arrêts BMW |
| --- | ---: | ---: | ---: | ---: |
| Road America, Race | 50 | 100 | 137 | 15 |
| Long Beach, Race | 26 | 52 | 32 | 3 |
| Daytona, Race, heure 24 | 69 | 265 | 1 622 | 144 |
| Laguna Seca, Race | 37 | 74 | 88 | 13 |
| Detroit, Race | 22 | 44 | 36 | 10 |
| Sebring, Race, heure 12 | 64 | 192 | 716 | 66 |
| Watkins Glen, Race, heure 6 | 57 | 151 | 387 | 34 |
| Canadian Tire Motorsport Park, Race | 35 | 70 | 111 | 8 |
| VIR, Race | 23 | 46 | 54 | 7 |
| Indianapolis, Race, heure 6 | 63 | 167 | 376 | 31 |
| Road Atlanta, Race, heure 10 | 61 | 183 | 558 | 57 |
| **Total** | **507** | **1 344** | **4 117** | **388** |

Ces volumes sont des références pour ce jeu de données, pas des constantes
métier imposées aux prochaines courses. Une entrée source n'est pas forcément
une voiture distincte : un même numéro peut apparaître dans plusieurs fragments.
Tous les concurrents sont conservés ; le lecteur du mart filtre ensuite BMW.

Les classements et la synthèse contiennent **469 participations, dont 48 BMW** :

| Classement 2025 | Participants | Participations BMW | `count_mismatch` | Pourcentage |
| --- | ---: | ---: | ---: | ---: |
| Road America | 48 | 5 | 2 | 4,17 % |
| Long Beach | 27 | 3 | 0 | 0 % |
| Daytona, heure 24 | 61 | 5 | 14 | 22,95 % |
| Laguna Seca | 36 | 5 | 1 | 2,78 % |
| Detroit | 22 | 4 | 0 | 0 % |
| Sebring, heure 12 | 56 | 5 | 8 | 14,29 % |
| Watkins Glen, heure 6 | 55 | 5 | 6 | 10,91 % |
| Canadian Tire Motorsport Park | 35 | 3 | 0 | 0 % |
| VIR | 23 | 3 | 0 | 0 % |
| Indianapolis, heure 6 | 53 | 5 | 4 | 7,55 % |
| Road Atlanta, heure 10 | 53 | 5 | 3 | 5,66 % |

Ces totaux comptent les participations par course, pas des voitures uniques
sur l'ensemble des événements.

À Road America, le rapport d'arrêts décrit 50 fragments pour 47 numéros
distincts. La comparaison conserve les 48 participants du classement : la
voiture `70` déclare zéro arrêt mais n'a aucun détail ; son statut est
`zero_reported_no_detail`, avec un comptage observé `NULL` conservé.
À Long Beach, la voiture `34` déclare un arrêt sans détail retrouvé : elle
reste présente avec `missing_stop_details`. À Daytona, les 61 numéros sont
présents dans les deux rapports ; les 69 entrées du rapport d'arrêts sont des
fragments. La BMW `48` présente 29 arrêts déclarés contre 30 détaillés.
À Laguna Seca, la voiture `70` déclare quatre arrêts contre trois détaillés.

Une durée d'arrêt publiée ne mesure pas nécessairement un ravitaillement, le
travail des mécaniciens ou une perte nette de temps en piste. La couverture
mondiale auto et moto sur 2022–2026 reste un objectif d'exploration, pas une
couverture acquise.

## Installation et lancement

Prérequis : Python 3.12 ou supérieur, uv et accès Internet pour installer les
dépendances et télécharger les sources initiales. Depuis la racine du projet :

```bash
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked python run_pipeline.py
```

La commande unique exécute dans cet ordre :

1. `inspect_manifest.py` : sélection des rapports activés de type `pit_stops`,
   téléchargement si nécessaire, ou vérification SHA-256 des fichiers locaux.
2. `build_bronze.py` : conservation des blocs JSON dans Parquet et comparaison
   des contenus et volumes avec le document source.
3. `inspect_classification.py` : sélection des classements activés, vérification
   du Raw existant ou téléchargement avec métadonnées.
4. `build_classification_bronze.py` : conservation et comparaison des trois
   racines `session`, `fastest_lap` et `classification` dans une Bronze distincte.
5. `analyze_bronze.py` : transformations, contrôles, écriture des douze résultats
   dans un nouveau dossier d'exécution, puis activation de cet ensemble.

Si une étape termine en erreur, le lanceur s'arrête avant la suivante.
`Pipeline completed successfully.` n'est affiché qu'après les cinq réussites.
Les chemins des étapes sont construits depuis les scripts.

Exemple de lancement depuis un autre dossier, avec un chemin à adapter :

```bash
uv run --locked --project /chemin/vers/Moto_Sport_BMW_Pipeline python /chemin/vers/Moto_Sport_BMW_Pipeline/run_pipeline.py
```

Les fichiers déjà présents sont réutilisés. Pour retélécharger volontairement
les rapports configurés et enregistrer de nouvelles métadonnées, puis reconstruire :

```bash
uv run --locked python inspect_manifest.py --refresh
uv run --locked python inspect_classification.py --refresh
uv run --locked python run_pipeline.py
```

Pour afficher les tableaux détaillés de l'analyse :

```bash
uv run --locked python analyze_bronze.py --verbose
```

`--verbose` appartient à `analyze_bronze.py` ; le lanceur ne transmet pas encore
cette option. Les contrôles bloquants et les compteurs essentiels s'exécutent
aussi sans elle.

## Données et résultats

```text
data/
├── raw/<source_id>/
│   ├── <document source .JSON>
│   └── metadata.json
├── bronze/<source_id>/document.parquet
├── runs/<run_id>/
│   ├── silver/
│   │   ├── sessions.parquet
│   │   ├── car_entries.parquet
│   │   ├── driver_entries.parquet
│   │   ├── pit_stops.parquet
│   │   └── classification.parquet
│   ├── quality/
│   │   ├── session_quality_summary.parquet
│   │   ├── total_pit_duration_quality.parquet
│   │   ├── total_pit_duration_comparison.parquet
│   │   ├── classification_pit_stop_comparison.parquet
│   │   └── classification_count_quality.parquet
│   └── marts/
│       ├── enriched_pit_stops.parquet
│       └── race_car_summary.parquet
└── current.json
```

- **Raw** : document téléchargé et métadonnées de provenance, date de
  téléchargement et empreinte SHA-256. Cette empreinte vérifie l'identité des
  octets locaux ; elle ne prouve pas la justesse du contenu de la source.
- **Bronze** : une ligne par document. Les rapports d'arrêts conservent
  `session` et `pit_stop_analysis` en JSON ; le classement conserve `session`,
  `fastest_lap` et `classification`. Les transformations métier se font dans Silver.
- **Silver** : contexte de session par document, entrées de voitures, entrées
  de pilotes, arrêts et participants au classement séparés. Les numéros textuels
  gardent leurs zéros. La Silver du classement ne projette pour l'instant que
  les clés, le numéro, le constructeur, le modèle, la position générale, la classe, le nombre d'arrêts
  déclaré et `not_finished` ; les autres champs restent conservés en Bronze.
- **Qualité** : absence et échec de conversion distingués ; comparaison entre
  somme des durées et dernier cumul déclaré par source, version et numéro de
  voiture, avec les statuts `matched`, `incomplete` et `mismatch`.
  Un rapport distinct rapproche aussi les comptages du classement et des arrêts.
- **Marts** : arrêts enrichis avec les noms des pilotes d'entrée et de sortie,
  sans multiplier les lignes par le nombre de pilotes ; synthèse par participant
  réunissant classement, comptages, statut de comparaison et statistiques de durée.

`bronze_sha256` identifie les octets du fichier Bronze utilisé. Les relations
vers les entrées de voitures utilisent aussi `source_id` et
`source_entry_index`. Cet indice est une position dans une version du document,
pas un identifiant permanent de voiture.

### Rapprochement classement et arrêts

Les documents sont associés via le manifeste sur `championship`, `season`,
`event_id` et `session_id`. Chaque classement doit avoir exactement un rapport
d'arrêts candidat ; une correspondance absente ou multiple bloque le traitement.
Le traitement commun charge les classements activés dans une même table Bronze
temporaire, en conservant l'identifiant et l'empreinte de chaque document.
Les transformations et les jointures séparent les sources et leurs versions.
Le lot doit comprendre tous les classements activés. Si un fichier Bronze est
absent, le chargeur lève `FileNotFoundError` en indiquant la source et le chemin
attendu. Le traitement s'arrête sans publier un lot partiel ni activer un
nouveau run ; les documents déjà chargés restent dans la connexion temporaire.
Un test couvre ce refus après le chargement d'un premier document valide.

Les arrêts sont comptés par source, empreinte Bronze et numéro textuel de
voiture, tous fragments confondus. Un `LEFT JOIN` depuis le classement conserve
les participants sans arrêt détaillé. La version du rapport chargé participe à
la jointure ; les empreintes du classement et du rapport d'arrêts sont conservées
séparément. Le nombre de participants avant et après jointure est contrôlé.

La synthèse `race_car_summary` ajoute les statistiques du résumé des arrêts
par source du rapport d'arrêts, empreinte Bronze et numéro de voiture.
Elle conserve les participants sans détail ; leurs statistiques restent `NULL`.
Avant publication, `validate_race_car_summary` refuse les clés manquantes ou
dupliquées et compare les clés participantes au classement dans les deux sens.
Sa granularité est une ligne par `source_id`, `bronze_sha256`, `car_number`
du classement. Les tests couvrent notamment une substitution de participant
à volume identique, les sources et versions concurrentes, et le cas valide.
La durée moyenne décrit les valeurs disponibles dans le rapport ; elle ne
mesure pas à elle seule la performance des mécaniciens.

| `comparison_status` | Signification |
| --- | --- |
| `matched` | Comptages déclaré et observé égaux. |
| `zero_reported_no_detail` | Zéro déclaré, aucune ligne détaillée retrouvée. |
| `missing_stop_details` | Comptage déclaré disponible et non nul, aucun détail retrouvé. |
| `count_mismatch` | Comptages disponibles mais différents. |
| `unavailable_reported_count` | Comptage déclaré absent ou non convertible. |
| `missing_pit_stop_report` | Rapport correspondant non retrouvé dans la Bronze chargée. |

Ces statuts décrivent les données ; ils ne corrigent pas les nombres sources et
ne constituent pas une explication sportive. Les écarts de comptage sont publiés
pour investigation, sans être à eux seuls bloquants. Le cas zéro sans détail
n'est pas automatiquement une erreur. Le rapprochement utilise les documents
sélectionnés ; il ne démontre pas qu'ils ont été publiés simultanément.

### Responsabilités du code

`analyze_bronze.py` coordonne les fonctions de chargement, les transformations
Silver, les contrôles de rattachement, les rapports et la publication.
`analyze_classification.py` fournit le chargement et la transformation du
classement ; son lancement isolé reste une exploration du seul pilote Road America.
`silver_writer.py` écrit et vérifie un fichier ; `run_publication.py` active
l'ensemble et permet aux lecteurs de retrouver le run courant. Les requêtes
SQL restent distinctes pour permettre leur test indépendant. La séparation
en fonctions est engagée ; le lanceur d'analyse contient encore des blocs
d'exploration et sera progressivement simplifié.

## Consulter les résultats actifs

Après un lancement réussi :

```bash
uv run --locked python inspect_quality.py
uv run --locked python inspect_marts.py
```

Chaque lecteur affiche `Reading run: ...`, lit `current.json` une seule fois,
puis utilise le dossier sélectionné pour ses fichiers.

- Le lecteur qualité affiche les informations de session manquantes ou invalides
  et les temps cumulés non convertis. Dans le jeu actuel, les deux températures
  de Long Beach sont manquantes ; aucun temps cumulé n'est non converti.
- Il affiche aussi les comparaisons classement/arrêts autres que `matched`.
  À Road America, les voitures `22` et `88` apparaissent avec
  `count_mismatch` : respectivement 1 arrêt déclaré contre 2 détaillés, et
  4 déclarés contre 3 détaillés. La voiture `70` apparaît avec
  `zero_reported_no_detail`. À Long Beach, la voiture `34` est signalée avec
  `missing_stop_details`. À Daytona, 14 participants présentent un
  `count_mismatch`, dont la BMW `48`. Les valeurs ont été relues dans les Raw ;
  la cause des écarts n'est pas établie et aucune correction n'est appliquée.
- Le lecteur du mart affiche les 388 arrêts BMW et les pilotes associés, avec
  un arrondi d'affichage à trois décimales.
- Il affiche aussi les **48 participations BMW** des onze classements,
  regroupées par source puis position. Les treize colonnes comprennent la source,
  le constructeur, le modèle, la position, la classe, les comptages d'arrêts,
  la moyenne, les compteurs de durées valides et invalides, la couverture et le
  statut. Les deux tableaux sont lus depuis le même run actif. La synthèse
  sauvegardée contient les 469 participants ; le filtre BMW est propre au lecteur.
- Le lecteur qualité affiche aussi un bilan par source et version du classement :
  le nombre total de participants, le nombre de `count_mismatch` et leur
  pourcentage. Onze lignes sont produites : Road America (48, 2, 4,17 %),
  Long Beach (27, 0, 0 %), Daytona (61, 14, 22,95 %), Laguna Seca (36, 1, 2,78 %)
  Detroit (22, 0, 0 %), Sebring (56, 8, 14,29 %), Watkins Glen (55, 6, 10,91 %),
  Canadian Tire Motorsport Park (35, 0, 0 %), VIR (23, 0, 0 %),
  Indianapolis (53, 4, 7,55 %) et Road Atlanta (53, 3, 5,66 %).
  Cet indicateur mesure uniquement les écarts de comptage. Les autres statuts
  restent inclus dans le total des participants, sans être comptés comme
  `count_mismatch`. Le bilan à 0 % de Long Beach ne signifie donc pas
  l'absence de toute anomalie : le détail signale la voiture `34`.

Un tableau d'anomalies vide signifie qu'aucune ligne ne respecte le filtre
considéré, pas que le fichier ne contient aucune donnée. Le rapport de
comparaison des cumuls est sauvegardé, mais n'est pas encore affiché par
`inspect_quality.py`.

## Publication et gestion des échecs

Chaque fichier est d'abord écrit dans un Parquet temporaire, relu et comparé
aux données attendues avant remplacement dans le dossier candidat.
Les douze fichiers sont écrits dans `data/runs/<run_id>/`. Leur présence est
vérifiée avant d'écrire une référence JSON temporaire et de remplacer
`data/current.json`.

Un échec avant l'activation laisse l'ancienne référence inchangée. Le dossier
candidat incomplet et certains fichiers temporaires peuvent rester disponibles
pour le diagnostic. Le nettoyage automatique n'est pas implémenté ; ne pas
supprimer un dossier encore utilisé par un lecteur.

Le prochain lancement recommence les transformations ; il ne reprend pas
exactement à la dernière étape réussie. Les fichiers Raw existants sont
vérifiés et réutilisés. Le premier lancement qui échoue avant activation ne
crée aucune exécution active ; les lecteurs signalent alors la référence absente.

La vérification de présence lors de l'activation complète les contrôles de
contenu effectués pendant les écritures ; elle n'est pas, seule, une validation
Parquet. Les scénarios simulés ne démontrent pas une récupération après coupure
machine, une durabilité après panne matérielle ou une gestion de publications
concurrentes.

## Vérifications et limites actuelles

La suite de tests couvre notamment les erreurs HTTP et JSON, la conservation
des fichiers précédents, les conversions et le passage de minuit, les clés,
les relations, les versions, les cumuls, l'arrêt du lanceur et l'activation.
Les données de test sont synthétiques ; les données des rapports sont réelles.

Les dates des rapports sont interprétées sans attribuer un fuseau non confirmé.
Le calcul des durées à partir des heures de passage suppose un arrêt inférieur
à 24 heures ; les écarts sont diagnostiqués, sans remplacer la durée source.
Les durées numériques utilisent `DOUBLE` : de faibles écarts de représentation
binaire sont possibles. Les comparaisons utilisent une tolérance explicite.

L'association entre une Bronze reconstruite et les fichiers Raw actuellement
présents n'est pas un historique immuable de toutes les versions sources.
`--refresh` remplace la copie Raw et ses métadonnées ; le couple n'est pas publié
en une transaction unique. Le pipeline ne détecte pas encore automatiquement
les changements distants. La vérification SHA-256 locale ne consulte pas le serveur.
Les dates à tirets, le message officiel, la météo et `fastest_lap` du classement
sont conservés en Bronze ; ils ne sont pas encore normalisés dans ses tables Silver.
Les anciens chemins `data/silver`, `data/quality` et `data/marts` peuvent encore
exister localement : les lecteurs actuels utilisent les dossiers sous `runs`.

## GitHub Actions et réutilisation

Le workflow manuel **Validate and extract IMSA source** exécute la suite de tests,
puis l'ancien parcours `download.py` → `inspect_source.py` sur Road America.
Il ne lance pas encore `run_pipeline.py` et n'archive pas les résultats.
La validation complète et la publication décrites ici sont locales.

`data/`, les environnements virtuels et les fichiers de secrets sont exclus de
Git. L'accès public aux rapports ne constitue pas une autorisation générale
pour redistribuer les données ; leurs conditions de réutilisation restent à
vérifier avant publication des fichiers. La licence du code est un sujet
séparé ; aucune licence n'est encore annoncée ici.

## Prochain jalon

Compléter le contrat des données de classement et leur contexte documentaire,
puis étendre les sources par lots vérifiés. La future couche Gold doit être
documentée et exploitable depuis SQL ou un notebook ; son usage par une application
d'IA reste à démontrer. L'orchestration avancée, la détection des changements
distants et l'archivage des versions Raw restent au backlog. L'expérimentation
de stockage objet local et cloud viendra dans un périmètre distinct, avec budget défini.
