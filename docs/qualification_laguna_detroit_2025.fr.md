# Qualification du lot Laguna Seca / Detroit 2025

Inspection du 12 novembre 2026, puis activation des quatre sources et validation
locale confirmée par Chouaib : 194 participations, dont 22 BMW, 1 915 arrêts
rattachés et enrichis. Bilan Laguna Seca : 36 participants, un écart (2,78 %) ;
Detroit : 22 participants, aucun écart de comptage. Le statut des quatre sources
est passé à `tested_locally`. La suite de 103 tests avait passé avant cet ajout ;
elle n'a pas été relancée par l'agent pour cette qualification.

## Sources officielles

- [Répertoire Laguna Seca](https://imsa.results.alkamelcloud.com/Results/25_2025/10_Weathertech%20Raceway%20Laguna%20Seca/01_IMSA%20WeatherTech%20SportsCar%20Championship/202505111210_Race/)
- [Répertoire Detroit](https://imsa.results.alkamelcloud.com/Results/25_2025/11_Detroit%20Street%20Course/01_IMSA%20WeatherTech%20SportsCar%20Championship/202505311640_Race/)

Chaque répertoire fournit `03_Results_Race_Official.JSON` et
`20_Pit Stops Time Cards_Race.JSON`. Les deux classements portent report_mark
Official. Les rapports d'arrêts ne sont pas supposés officiels sur la seule
base de leur présence dans ce répertoire.

| Référence | Laguna Seca | Detroit |
| --- | --- | --- |
| event_id proposé | laguna-seca | detroit |
| session_id issu du dossier | 202505111210-race | 202505311640-race |
| Participants classés / numéros distincts | 36 / 36 | 22 / 22 |
| Participations BMW | 5 | 4 |
| Entrées du rapport d'arrêts | 37 | 22 |
| Arrêts détaillés | 88 | 36 |
| Écarts de comptage observés | Voiture 70 : 4 déclarés, 3 détaillés | Aucun |

Racines des classements : session, fastest_lap, classification. Racines des
arrêts : session, pit_stop_analysis. Aucun numéro du rapport d'arrêts n'est
absent du classement correspondant. Les champs projetés par la Silver actuelle
sont présents dans les aperçus ; les contrôles de conversion, clés et liens
restent à exécuter sur le lot complet avant de conclure à son intégration.

Dates : Laguna Seca expose `11-05-2025 12:10` dans le classement et
`11/05/2025 12:10` dans les arrêts ; Detroit expose `31/05/2025 04:40` des deux
côtés. Ces textes ne prouvent pas un fuseau ou une convention 12/24 heures.
La jointure interdocuments doit utiliser les métadonnées explicites du manifeste.
La cause de l'écart de Laguna Seca n'est pas établie ; aucune correction prévue.

Après intégration, références attendues pour les cinq courses réunies :
194 participations classées, dont 22 BMW, 1 915 arrêts détaillés et cinq lignes
de bilan de comptage. Les douze familles de fichiers restent inchangées.
Ces références ne remplacent pas la validation des transformations et du run.
