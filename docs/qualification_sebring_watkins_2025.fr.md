# Qualification Sebring / Watkins Glen 2025

Inspection puis intégration du 12 novembre 2026. Quatre sources activées et
passées à `tested_locally` après exécution confirmée par Chouaib : run
`cf43b04e5ef849e38aafe0f07c16aec2`, 305 participations, dont 32 BMW,
3 018 arrêts rattachés et enrichis, dont 285 BMW. Les écarts ci-dessous sont
issus de la qualification des JSON ; la suite de tests n'a pas été rejouée
par l'agent pour cet ajout de configuration.

## Répertoires retenus

- [Sebring, heure 12](https://imsa.results.alkamelcloud.com/Results/25_2025/06_Sebring%20International%20Raceway/01_IMSA%20WeatherTech%20SportsCar%20Championship/202503151010_Race/12_Hour%2012/)
- [Watkins Glen, heure 6](https://imsa.results.alkamelcloud.com/Results/25_2025/14_Watkins%20Glen%20International/01_IMSA%20WeatherTech%20SportsCar%20Championship/202506221210_Race/06_Hour%206/)

Les index des sessions exposent respectivement douze et six sous-dossiers
horaires. Seul le couple final est retenu, sans concaténer les états antérieurs.
Fichiers : `03_Results_Race_Official.JSON` et `20_Pit Stops Time Cards_Race.JSON`.
Les classements portent `report_mark: Official` et une durée de fin de
43 200 / 21 600 secondes, cohérente avec douze / six heures.

| Référence | Sebring | Watkins Glen |
| --- | ---: | ---: |
| Participants classés distincts | 56 | 55 |
| Participations BMW | 5 | 5 |
| Entrées d'arrêts | 64 | 57 |
| Entrées de pilotes | 192 | 151 |
| Arrêts détaillés | 716 | 387 |
| Arrêts BMW détaillés | 66 | 34 |
| Écarts de comptage | 8 (14,29 %) | 6 (10,91 %) |

Numéros concernés à Sebring : 40, 52, 021, 63, 14, 19, 73, 18.
À Watkins Glen : 85, 14, 44, 25, 11, 52. Pour chacun, le classement déclare
un arrêt de plus que le détail inspecté. La BMW 25 de Watkins Glen déclare
cinq arrêts contre quatre détaillés. Causes non établies ; aucune correction.
Aucun numéro du détail des arrêts n'est absent du classement correspondant.

Les racines correspondent aux familles existantes ; la compatibilité complète
des conversions, clés, liens et durées reste à vérifier dans le pipeline.
Les identifiants de session proposés proviennent des dossiers :
`202503151010-race` et `202506221210-race`. Ils ne prouvent pas un fuseau horaire.

Après intégration aux cinq courses existantes, références attendues :
305 participations classées, dont 32 BMW, 3 018 arrêts détaillés, dont 285 BMW,
sept lignes de bilan et toujours douze familles de sortie.
