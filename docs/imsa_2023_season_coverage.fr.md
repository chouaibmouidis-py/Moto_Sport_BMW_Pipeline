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

Cette couverture est **exploratoire**, pas une intégration aux sorties Silver,
Gold ou aux lecteurs du run actif 2024–2025. Les CSV ne fournissent pas de
comptage déclaré indépendant ; les bilans count_mismatch du pipeline JSON
ne sont donc pas transposés. Noms de pilotes, heures d'entrée/sortie et totaux
cumulés du PDF ne sont pas encore exposés par ce lecteur.

Les onze publications sont contrôlées fichier par fichier, sans activation
atomique de l'ensemble exploratoire : un échec tardif peut laisser un lot
partiellement actualisé. `data/current.json` n'est jamais modifié.
Les empreintes identifient les versions lues ; le contexte du catalogue est
déclaratif, pas une vérification automatique de la course contenue dans le PDF.
