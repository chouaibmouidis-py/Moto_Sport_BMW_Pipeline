# Qualification Road America 2024 — pilote intersaisons

Inspection et intégration du 12 novembre 2026. Les deux sources sont activées
et marquées `tested_locally` après confirmation par Chouaib des références :
516 participations, dont 52 BMW, 4 280 arrêts dont 396 BMW, douze bilans et
séparation des deux saisons. La suite de tests n'a pas été rejouée par l'agent
pour cet ajout de configuration.

[Répertoire officiel](https://imsa.results.alkamelcloud.com/Results/24_2024/14_Road%20America/01_IMSA%20WeatherTech%20SportsCar%20Championship/202408041410_Race/).
Fichiers : `03_Results_Race_Official.JSON` et `20_Pit Stops Time Cards_Race.JSON`.
Le classement porte Official. Identité de session proposée : saison 2024,
event_id road-america, session_id 202408041410-race, report_period session.

Racines inchangées : session/fastest_lap/classification pour le classement,
session/pit_stop_analysis pour les arrêts. Les champs Silver attendus sont
présents chez les 47 participants. Les clés du premier participant ont été
comparées à celles de Road America 2025, sans différence ; cela ne prouve pas
une égalité complète des schémas et des types sur toute l'année.

| Référence | Valeur |
| --- | ---: |
| Participants classés / numéros distincts | 47 / 47 |
| Participations BMW | 4 |
| Entrées du rapport d'arrêts | 49 |
| Entrées de pilotes | 98 |
| Arrêts détaillés | 163 |
| Arrêts BMW | 8 |
| Écarts de comptage | 4 (8,51 %) |

BMW : 24 (position 7), 1 (22), 96 (24), 25 (46).
Les GT sont libellées BMW M4 GT3, sans EVO ; conserver le modèle source.
Écarts : 023 (5 déclarés / 4 détaillés), 120 (4/3), 45 (2/3), 11 (2/1).
Causes non établies ; aucune correction automatique.
Date de session du classement : 04-08-2024 02:10, sans fuseau confirmé.

Références attendues après ajout aux onze courses 2025 : 516 participations,
dont 52 BMW ; 4 280 arrêts détaillés, dont 396 BMW ; douze bilans qualité,
toujours douze familles de sortie. Le parcours complet et les contrôles de
conversions, clés et rattachement restent à exécuter avant validation locale.
