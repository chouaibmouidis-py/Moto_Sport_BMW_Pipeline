# Architecture et journalisation

Refactorisation du 13 novembre 2026. Elle organise les responsabilités et les
messages d'exécution ; elle n'intègre pas 2023 dans le run JSON et n'étend pas
la couverture des saisons. Les requêtes SQL métier restent inchangées.

## Lire le projet par responsabilité

Les commandes historiques à la racine restent utilisables. Les fonctions
partagées résident dans `src/moto_sport_bmw_pipeline`. Les petits scripts
d'ingestion et d'inspection restent à la racine ; leurs imports ne lancent
plus de téléchargement ni de lecture de données.

| Besoin | Module propriétaire | Commande ou façade historique |
| --- | --- | --- |
| Coordonner les cinq étapes JSON | `orchestration.py` | `run_pipeline.py` |
| Construire et activer un candidat JSON | `pipeline.py` | `analyze_bronze.py` |
| Résoudre les chemins du projet | `paths.py` | Partagé par les lanceurs |
| Télécharger un Raw JSON | `raw_download.py` | `download.py` |
| Contrôler les empreintes Raw | `integrity.py` | `file_integrity.py` |
| Valider les identifiants du manifeste | `manifest.py` | `manifest_validation.py` |
| Charger les Bronze et métadonnées | `source_loading.py` | Fonctions réexportées par les anciens scripts |
| Transformer et contrôler les clés Silver | `silver.py` | Fonctions historiques conservées |
| Apparier les sources, contrôler les liens et participants | `quality.py` | Appelé par le pipeline |
| Produire les diagnostics de durée | `duration_quality.py` | Appelé par le pipeline |
| Construire les enrichissements et synthèses | `marts.py` | Appelé par le pipeline |
| Déclarer et publier les douze sorties | `publication.py` | Registre `OUTPUT_VIEWS` unique |
| Vérifier et remplacer un Parquet | `parquet_writer.py` | `silver_writer.py` |
| Activer ou lire une référence de run | `run_reference.py` | `run_publication.py` |
| Reconnaître les blocs et arrêts du PDF | `pdf_parser.py` | Réexporté par `explore_pit_stop_pdf.py` |
| Convertir, contrôler et publier un couple CSV/PDF | `exploration.py` | `explore_pit_stop_pdf.py`, `explore_2023_season.py` |
| Afficher des tableaux de diagnostic | `diagnostics.py` | Activé par `--verbose` |
| Configurer les logs et le contexte de run | `logging_config.py` | Configuration aux points d'entrée |

Chaque module Python possède une docstring de tête expliquant son rôle.
Les fichiers SQL restent dans `sql/`, les manifestes dans `config/`, les
scénarios dans `tests/` et les données locales ignorées par Git dans `data/`.
Les façades évitent de casser les imports existants pendant la transition ;
le nouveau code doit importer directement le module propriétaire.

## Parcours des données

```text
run_pipeline.py
  ├── inspect_manifest.py → build_bronze.py
  ├── inspect_classification.py → build_classification_bronze.py
  └── analyze_bronze.py → pipeline.build_candidate_run
        chargement → Silver → contrôles → marts → publication → activation

explore_2023_season.py
  catalogue exploratoire → pdf_parser → exploration → Parquet exploratoires
```

Le registre des sorties requises est partagé par la publication et l'activation.
Un fichier oublié ne peut plus résulter d'une divergence entre deux listes.
Les règles de blocage, le comportement des NULL et les formules SQL sont conservés.
Les anciens tableaux pédagogiques propres à une voiture de 2025 ont été remplacés
dans l'analyse principale par des aperçus génériques des vues en mode verbose.

## Logs opérationnels

Les anciens `print()` de suivi sont remplacés par `logging`. Les `.show()`
restent destinés à afficher de vraies tables, notamment dans les lecteurs métier.

| Niveau | Usage |
| --- | --- |
| INFO | Début/fin d'étape, sources chargées, volumes et fichiers publiés |
| WARNING | Anomalie signalée qui ne bloque pas la publication |
| ERROR | Échec d'une étape ou d'un candidat, avec traceback |
| DEBUG | Empreintes, chemins temporaires et détails d'exploration |

Format : horodatage UTC, niveau, module, identifiant de run et message.
L'identifiant vaut `-` avant la création d'un candidat JSON et dans l'exploration.
Le contexte événement/session de l'exploration figure dans ses messages et ses données.
Les logs console vont sur stderr ; les tableaux vont sur stdout. Un fichier
optionnel UTF-8 est ouvert en ajout. Configurer une deuxième fois ne duplique
pas les handlers de l'application. Les imports ne configurent pas les logs.

```bash
# Parcours JSON complet, logs communs aux cinq processus
uv run python run_pipeline.py --log-file data/logs/pipeline.log

# Transformation/publication à partir des Bronze existants
uv run python analyze_bronze.py --log-file data/logs/analyze.log

# Détails DEBUG et tableaux, uniquement quand nécessaires
uv run python analyze_bronze.py --verbose --log-file data/logs/analyze-debug.log

# Saison 2023 exploratoire, hors current.json
uv run python explore_2023_season.py --log-file data/logs/exploration-2023.log

# Entrées équivalentes du lanceur JSON depuis ce checkout
uv run moto-sport-bmw-pipeline --help
uv run python -m moto_sport_bmw_pipeline --help
```

Le lanceur transmet `BMW_LOG_LEVEL` et, si demandé, `BMW_LOG_FILE` aux étapes.
Les petits scripts qui n'exposent pas ces options peuvent aussi hériter de ces
variables. Aucun service cloud de logs, rotation automatique ou mécanisme de
concurrence des fichiers de logs n'est ajouté par cette refactorisation.
Le projet reste validé depuis son checkout avec `config/`, `sql/` et les scripts
présents ; une distribution autonome par wheel n'est pas encore démontrée.

## Portée réelle du fail fast

Les contrôles existants détectent les erreurs qu'ils expriment : JSON invalide,
empreinte incorrecte, clés invalides, liens ambigus, comptage de participants
altéré ou contenu Parquet différent. Cela ne constitue pas un contrat exhaustif
de schéma fournisseur. Par exemple, renommer un champ optionnel peut produire
un NULL et une anomalie non bloquante ; un ajout de champ peut rester en Bronze
sans être projeté en Silver.

Avant 2026, qualifier les documents réels puis définir les champs requis et
compatibilités de schéma. Ne pas promettre une adaptation sans changement de
code avant cette qualification. Les hypothèses sportives expliquant une absence
d'arrêt ne deviennent pas des règles métier sans preuve source.

## Validation et lecture des tests

Les imports historiques restent disponibles. Un mock doit cependant viser le
module qui utilise réellement la dépendance : par exemple
`moto_sport_bmw_pipeline.publication.publish_silver` plutôt que l'ancien lanceur.
Les tests de logs couvrent absence de doublons, fichier UTF-8, niveau DEBUG,
contexte du run et transmission des options aux processus. Les imports des
lecteurs sont testés sans connexion ni téléchargement.

Les résultats doivent être comparés avant/après par schéma et différences de
lignes dans les deux sens ; un simple comptage ne prouve pas leur égalité.

Validation effectuée le 13 novembre 2026 : 132 tests réussis ; parcours JSON
complet à cinq étapes exécuté depuis les Raw locaux ; douze sorties comparées
exactement au run de référence avant refactorisation (schéma et EXCEPT ALL
dans les deux sens). Les onze synthèses 2023 ont également été régénérées puis
comparées à leurs références avec égalité exacte. Les lecteurs qualité et mart
ont été exécutés sur le même run actif. Les commandes d'aide du point d'entrée
console et du module Python sont fonctionnelles. Une installation vierge et
un téléchargement réseau initial n'ont pas été rejoués pour ce changement.

## Construction Bronze des arrêts PDF

Le module `bronze.py` construit les Parquet Bronze à partir de champs extraits
des sources. Son premier constructeur, `build_pdf_pit_stop_bronze`, réutilise
`pdf_parser.extract_stops` et la publication sécurisée de `parquet_writer`.
Il conserve les sept champs de chaque arrêt avec l'identifiant de source et
l'empreinte du PDF, sans conversion de durée. Il ne lance pas de saison et
n'active pas de run. Cette séparation évite de faire écrire le parseur lui-même.

## Langue et descriptions des fichiers

Les modules Python, les tests et les requêtes SQL maintenus portent un en-tête
en anglais décrivant leur rôle. Les identifiants, commentaires techniques et
messages opérationnels sont rédigés en anglais. La documentation pédagogique
peut rester en français. Les valeurs des sources conservent leur langue et le
test de journalisation utilise volontairement un message français pour vérifier
l'encodage UTF-8. Les copies de brouillon non suivies par Git sont exclues de
cette harmonisation.
