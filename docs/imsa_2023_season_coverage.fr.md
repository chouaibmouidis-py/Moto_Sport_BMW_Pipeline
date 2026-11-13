# Couverture exploratoire IMSA WeatherTech 2023

Qualification et publication exploratoire effectuées le 13 novembre 2026.
[Calendrier officiel](https://www.imsa.com/weathertech/weathertech-2023-schedule/).
[Index des résultats](https://imsa.results.alkamelcloud.com/Results/23_2023/).

Les onze couples CSV de classement Official / PDF d'arrêts sont décrits dans
`config/exploration_2023.json`. Les 22 fichiers ont été conservés localement
dans `data/raw` après téléchargement et contrôle de l'égalité des copies.
Ce catalogue est indépendant de `config/sources.json` : aucune source 2023
n'est activée dans le pipeline principal.

| Course | Session | Portée | Entrées classement | BMW | Arrêts extraits | Arrêts BMW |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Daytona | 202301281340-race | Heure 24 | 61 | 5 | 1 631 | 140 |
| Sebring | 202303181010-race | Heure 12 | 53 | 5 | 733 | 59 |
| Long Beach | 202304151405-race | Session | 28 | 5 | 28 | 6 |
| Laguna Seca | 202305141210-race | Session | 38 | 5 | 124 | 14 |
| Watkins Glen | 202306251040-race | Heure 6 | 57 | 5 | 383 | 29 |
| Canadian Tire | 202307091205-race | Session | 34 | 5 | 96 | 15 |
| Lime Rock | 202307221210-race | Session | 20 | 3 | 45 | 8 |
| Road America | 202308061010-race | Session | 45 | 5 | 116 | 9 |
| VIR | 202308271410-race | Session | 19 | 3 | 46 | 6 |
| Indianapolis | 202309171310-race | Session | 48 | 5 | 126 | 14 |
| Road Atlanta | 202310141140-race | Heure 10 | 52 | 5 | 625 | 67 |
| **Total** | | | **455** | **51** | **3 953** | **367** |

Long Beach inclut deux entrées Not started (80 et 93), avec position NULL.
Le terme « entrées classement » inclut ces non-partants ; il ne signifie pas
455 voitures ayant effectivement pris le départ.

## Vérifications réalisées

- Aucun doublon voiture/numéro d'arrêt ni arrêt sans participant correspondant
  repéré ; séquences d'arrêts contrôlées.
- Pour les neuf nouveaux PDF, comparaison de l'extraction par coordonnées avec
  une lecture textuelle sans restriction spatiale : listes identiques.
  Les deux lectures partagent les règles de reconnaissance ; ce n'est pas une
  validation indépendante de chaque ligne visuelle.
- Publication des onze synthèses par `publish_silver` avec contrôle du nombre
  de lignes et du contenu relu. Chaque synthèse contient le contexte de la
  course, le statut et les deux empreintes sources.
- Suite complète : 127 tests réussis. Un test vérifie deux publications avec
  contextes et dossiers distincts, pour prévenir la réutilisation du contexte
  Road America pour une autre course.

Absences de détail dans l'extraction : Long Beach 01/80/93 ; Laguna Seca 94 ;
Watkins Glen 51/24 ; Lime Rock 91/94 ; Road America 57 ; VIR 92 ; Indianapolis 93.
Les comptages restent NULL. Pour les nouvelles absences, l'absence visuelle
dans le PDF reste à confirmer : ne pas les interpréter comme zéro arrêt.

## Utilisation

```bash
uv run python explore_2023_season.py
```

Le lanceur vérifie la présence du lot local, puis appelle `explore_source_pair`
pour chaque course. Les sorties vont dans
`data/exploration/<event_id>-2023/car_summary.parquet`. Le catalogue conserve
les URL officielles, mais le lanceur ne télécharge pas les fichiers manquants.
Le lecteur PDF reste lié à la mise en page observée, sans garantie pour de
nouveaux formats. Le script individuel garde Road America comme contexte
d'exploration ; utiliser le catalogue pour les autres courses.

## Limites d'intégration

Cette couverture reste **hors du run actif 2024–2025** et de ses lecteurs.
Les classements ont un parcours Bronze/Silver isolé décrit ci-dessous ; les
synthèses CSV/PDF ne sont pas encore intégrées à ses sorties Gold.
Les CSV ne fournissent pas de
comptage déclaré indépendant ; les bilans count_mismatch du pipeline JSON
ne sont donc pas transposés. Noms de pilotes, heures d'entrée/sortie et totaux
cumulés du PDF ne sont pas encore exposés par ce lecteur.

Les onze publications sont contrôlées fichier par fichier, sans activation
atomique de l'ensemble exploratoire : un échec tardif peut laisser un lot
partiellement actualisé. `data/current.json` n'est jamais modifié.
Les empreintes identifient les versions lues ; le contexte du catalogue est
déclaratif, pas une vérification automatique de la course contenue dans le PDF.

## Structure commune des arrêts extraits du PDF

Tous les appels à `extract_stops` renvoient une liste de dictionnaires portant
les mêmes sept champs : `car_number`, `pit_number`, `pit_time_raw`,
`page_number`, `column_number`, `block_line_number` et `source_line`.
Les variantes retournant seulement trois valeurs et les filtres de voitures
codés dans le parseur ont été retirés. Le filtrage métier appartient aux lecteurs.

`extract_stop_blocks` organise les fragments en pages/colonnes ;
`parse_stop_blocks` est l'unique logique de reconnaissance des voitures et arrêts.
`convert_extracted_stops` conserve les sept champs et ajoute `pit_time_seconds`.
Les tests textuels sans document peuvent utiliser des repères page/colonne NULL ;
l'extraction d'un vrai PDF fournit des numéros à partir de 1.

`block_line_number` compte les lignes retenues du bloc extrait, pas les lignes
visuelles du PDF. `source_line` est le texte fourni par l'extraction, après les
opérations de sélection et de retrait des espaces externes ; il ne remplace pas
le PDF Raw. Ce schéma commun ne rend pas les coordonnées de lecture universelles.
Le constructeur `build_pdf_pit_stop_bronze`, dans `bronze.py`, publie ces sept
champs avec `source_id` et `pdf_sha256`, soit neuf colonnes. Le PDF Raw demeure
la référence ; Bronze conserve les champs sélectionnés par l'extracteur, pas
l'intégralité du contenu du document. Les durées restent textuelles.

Le pilote Road America est publié dans
`data/bronze/imsa-2023-road-america-race-pit-stops/document.parquet` : 116 arrêts,
repères et provenance relus et comparés à l'extraction. L'empreinte PDF est
distincte de celle du Parquet Bronze, qui sera calculée lors de son chargement.
Le constructeur refuse une source modifiée pendant l'extraction ; une erreur
du parseur ou d'écriture préserve une éventuelle sortie précédente.
Une extraction vide produit un schéma typé vide, sans inventer d'arrêt ; cela
ne prouve pas qu'un PDF inconnu a été correctement interprété.

Les onze courses disposent maintenant d'un Bronze et d'un Silver PDF. Le chargement
ajoute `bronze_sha256`, puis `34_silver_pdf_pit_stops.sql` ajoute
`pit_time_in_seconds` en réutilisant la macro de durée existante.
Le contrôle partagé de qualité refuse une provenance absente ou une clé répétée
(`source_id`, `bronze_sha256`, `car_number`, `pit_number`).

Le Silver pilote est sauvegardé dans
`data/exploration/road-america-2023/silver/pit_stops.parquet` : 116 lignes,
onze colonnes, aucune durée non convertie. Les champs Bronze et leurs repères
ont été comparés à la sortie ; les schémas et contenus ont été contrôlés après
publication. Le traitement par lot est disponible avec deux modes exclusifs :

```bash
uv run python explore_2023_season.py --pdf-bronze-only
uv run python explore_2023_season.py --pdf-silver-only
```

Le premier construit les onze Bronze depuis les PDF Raw locaux ; le second
construit les Silver depuis les Bronze existants. Vérification des sorties :
3 953 arrêts, dont 367 BMW, zéro durée non convertie. Les champs extraits et
repères sont identiques entre Bronze et Silver ; les empreintes PDF et Bronze
correspondent aux fichiers locaux. Aucun arrêt orphelin n'a été détecté face
aux classements Silver correspondants. La référence active reste inchangée.

Les modes `--classification-only`, `--pdf-bronze-only` et `--pdf-silver-only`
sont mutuellement exclusifs. La présence des entrées est vérifiée avant chaque
lot, mais une erreur tardive de contenu peut laisser les sorties précédentes
actualisées : aucune activation atomique de saison n'est fournie.

Les huit tests de lots Bronze/Silver PDF passent. Après correction du bloc
parasite dans silver_writer.py et renforcement du scénario Silver avec deux
courses, Chouaib confirme 170 tests réussis sur la suite complète.

## Rapprochement mart des onze courses

```bash
uv run python explore_2023_season.py --mart-only
```

Ce mode exclusif utilise les deux Silver déjà publiés pour chaque course et
appelle `publish_csv_pdf_race_summary` avec le contexte de cette seule course.
Il vérifie tous les chemins et refuse les identifiants dupliqués avant de
publier dans `data/exploration/<event_id>-2023/marts/race_car_summary.parquet`.
Il ne relit pas les Raw et ne reconstruit pas Bronze ou Silver.

Validation sur les onze sorties : 455 participations, dont 51 BMW, 3 953 arrêts
observés, dont 367 BMW. Les clés des participants sont identiques à celles des
classements Silver (EXCEPT ALL dans les deux sens). Les sessions et versions
CSV/PDF correspondent aux entrées ; les Silver et `data/current.json` sont
inchangés. Suite complète : 173 tests réussis.

Onze participations sont conservées sans détail d'arrêt, avec comptage observé
NULL : Long Beach (01, 80, 93), Laguna Seca (94), Watkins Glen (24, 51), Lime
Rock (91, 94), Road America (57), VIR (92) et Indianapolis (93).
Cette absence n'établit ni un zéro arrêt ni une cause sportive.

Tous les comptages déclarés restent NULL ; `comparison_status` vaut
`unavailable_reported_count`. Le champ indépendant `stop_detail_status`
distingue `available` de `no_stop_details`.

Trois tests de lot vérifient la séparation de deux courses ayant la même
voiture, le refus d'une entrée manquante avant publication et la préservation
d'un mart précédent si un Silver d'une autre source est placé dans le mauvais
dossier. La publication reste individuelle : une erreur tardive peut laisser
les courses précédentes actualisées. Le lot n'est pas activé atomiquement et
n'est pas intégré aux lecteurs du run principal.

### Historique du pilote Road America

La synthèse du pilote est publiée dans
`data/exploration/road-america-2023/marts/race_car_summary.parquet` : 45
participations conservées, 116 arrêts retrouvés, voiture 57 conservée avec
comptage observé NULL. Les comptages déclarés restent NULL et le statut vaut
`unavailable_reported_count` ; `stop_detail_status` distingue les détails
disponibles de leur absence. Les versions CSV et PDF sont conservées séparément.

`build_pit_stop_counts` alimente une vue commune `pit_stop_count_input` pour
réutiliser SQL 28 sur les deux formats. `build_csv_pdf_race_summary` réutilise
l'appariement SQL 29, refuse les versions multiples d'une même source et les
arrêts sans participant correspondant, puis applique le LEFT JOIN de SQL 35.
La même voiture dans deux sessions ne mélange pas leurs comptages.

Validation : 158 tests réussis ; comptages partagés vérifiés sur les 8 307 arrêts
JSON actifs, entrées Silver et référence active inchangées lors du pilote.
Ce pilote est désormais généralisé par `build_mart_batch` sans recopier la
logique SQL ; les limites de lecture PDF décrites plus haut restent applicables.

## Classements CSV : parcours Bronze/Silver isolé

```bash
uv run python explore_2023_season.py --classification-only
```

Cette option lit les onze `classification_path` du catalogue existant, sans
relire les PDF. Elle vérifie tous les chemins avant publication et refuse les
identifiants de course ou de source dupliqués. L'identifiant de source reprend
le nom du dossier Raw, conformément aux dossiers existants.

Pour chaque course :

1. Le CSV est lu en texte (`;`, en-tête, complétion des champs finaux absents
   par NULL), sans nettoyage des valeurs Bronze.
2. Le Parquet Bronze est publié dans `data/bronze/<source_id>/document.parquet`.
3. Le chargement ajoute `source_id` et l'empreinte SHA-256 du Parquet Bronze.
4. Les numéros manquants ou dupliqués après nettoyage bloquent la transformation.
5. La requête `33_silver_classification_csv.sql` normalise cinq champs.
6. Les sept colonnes Silver sont publiées et relues avec contrôle du contenu dans
   `data/exploration/<event_id>-2023/silver/classification.parquet`.

Validation réelle des onze classements : 455 participations, dont 51 BMW ;
seules les positions de 80 et 93 à Long Beach sont NULL (`Not started`).
Les schémas et contenus Bronze ont été comparés aux lectures CSV dans les deux
sens avec EXCEPT ALL. Les volumes et provenances Silver ont été vérifiés pour
chaque course, sans numéros manquants ou dupliqués. Les CSV Raw et la référence
`data/current.json` sont restés inchangés.

Cette commande publie les fichiers individuellement : un échec tardif peut
laisser des sorties de courses précédentes actualisées. Elle ne fournit ni
activation atomique de saison ni intégration aux sorties du run principal.
