# Qualification Canadian Tire Motorsport Park / VIR 2025

Inspection puis intégration du 12 novembre 2026. Quatre sources activées et
passées à `tested_locally` après confirmation des sorties par Chouaib :
363 participations, dont 38 BMW ; 3 183 arrêts rattachés, dont 300 BMW ;
neuf lignes de bilan qualité. La suite de tests n'a pas été rejouée par l'agent
pour cet ajout de configuration.

- [Session CTMP](https://imsa.results.alkamelcloud.com/Results/25_2025/15_Canadian%20Tire%20Motorsport%20Park/01_IMSA%20WeatherTech%20SportsCar%20Championship/202507131405_Race/)
- [Session VIR](https://imsa.results.alkamelcloud.com/Results/25_2025/17_VIRginia%20International%20Raceway/01_IMSA%20WeatherTech%20SportsCar%20Championship/202508241410_Race/)

Fichiers : `03_Results_Race_Official.JSON` et `20_Pit Stops Time Cards_Race.JSON`.
Les classements portent Official ; leurs racines sont session, fastest_lap,
classification. Les rapports d'arrêts conservent session et pit_stop_analysis.

| Référence | CTMP | VIR |
| --- | --- | --- |
| Session issue du dossier | 202507131405-race | 202508241410-race |
| Classes présentes | LMP2, GTDPRO, GTD | GTDPRO, GTD |
| Participants classés distincts | 35 | 23 |
| Participations BMW | 3 | 3 |
| Numéros BMW | 1, 48, 96 | 1, 96, 48 |
| Entrées d'arrêts | 35 | 23 |
| Entrées de pilotes | 70 | 46 |
| Arrêts détaillés | 111 | 54 |
| Arrêts BMW | 8 | 7 |
| Écarts de comptage inspectés | Aucun | Aucun |

Aucun numéro du rapport d'arrêts n'est absent du classement correspondant.
L'absence des BMW GTP 24 et 25 ne constitue pas un défaut de complétude : la
classe GTP ne figure dans aucun des deux classements. Ne pas imposer les cinq
BMW des courses toutes catégories comme constante de validation.
L'absence d'écart de comptage n'établit pas la qualité de tous les autres champs.

Références attendues après intégration aux sept courses : 363 participations,
dont 38 BMW ; 3 183 arrêts détaillés, dont 300 BMW ; neuf bilans qualité et
toujours douze familles de fichiers. Conversions, clés et liens à vérifier par
le pipeline avant de déclarer le lot validé.
