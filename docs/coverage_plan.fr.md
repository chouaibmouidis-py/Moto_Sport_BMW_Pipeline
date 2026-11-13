# Couverture BMW auto et moto, saisons 2022 à 2026

Objectif demandé : tester les courses avec participation BMW dans le monde,
programmes d'usine et équipes clientes compris. Les cinq saisons retenues sont
2022, 2023, 2024, 2025 et 2026 ; les données 2026 sont arrêtées aux publications
disponibles au 6 novembre 2026. Ce périmètre par saisons n'est pas une fenêtre
glissante exacte de cinq ans. Les archives 2021 sont une extension possible.

Ce document organise la recherche. Il ne prétend pas que toutes les courses
ci-dessous ont été recensées ou testées, ni que BMW est présent à chaque manche.

## Registre initial des familles à couvrir

| Discipline | Famille | Source de départ | État |
| --- | --- | --- | --- |
| Auto | IMSA WeatherTech | https://imsa.results.alkamelcloud.com/ | Onze courses 2024 et onze courses 2025 intégrées ; onze synthèses 2023 exploratoires hors run actif ; 2022 et 2026 à qualifier. Voir les suivis annuels. |
| Auto | IMSA Michelin Pilot Challenge, GT4 | Même portail IMSA | Archives par saison et participation à inventorier |
| Auto | FIA WEC | https://fiawec.alkamelsystems.com/ | Portail repéré ; accès actuel aux archives à résoudre |
| Auto | GT World Challenge Europe, Sprint et Endurance | https://www.gt-world-challenge-europe.com/results | Résultats publics repérés ; collecte et schémas à tester |
| Auto | GT World Challenge America, Asia, Australia | Portails officiels régionaux SRO | Sources et courses BMW à inventorier |
| Auto | Intercontinental GT Challenge | https://www.intercontinentalgtchallenge.com/results | Portail et rapport Suzuka 2025 repérés |
| Auto | DTM | https://www.dtm.com/ergebnisse/results?season=2025 | Résultats repérés ; extraction à tester |
| Auto | Nürburgring 24h et qualifications | https://www.24h-rennen.de/ergebnisarchiv/ | Archive officielle repérée |
| Auto | NLS | Organisateur officiel | Archives et schémas à identifier |
| Auto | GT4, GT nationaux et coupes BMW | Organisateurs par championnat | Registre à compléter, sans supposer un format SRO universel |
| Moto | WorldSBK | https://www.worldsbk.com/en/results | Portail repéré ; rapports par saison et sessions à tester |
| Moto | FIM EWC | https://www.fimewc.fr/results/ | Archive 2021–2023 repérée ; cette page ne démontre pas la couverture 2024–2026 |
| Moto | British Superbike et Superstock | https://www.britishsuperbike.com/ | Programme BMW client documenté ; fichiers à inventorier |
| Moto | IDM / EURO MOTO, FSBK, ESBK | Fédérations et organisateurs | Pistes BMW client ; participation à confirmer course par course |
| Moto | MotoAmerica, compétitions japonaises et autres séries nationales | Organisateurs officiels | Registre mondial à compléter |
| Moto | Road racing, dont TT et épreuves internationales | Organisateurs officiels | Sources, formats et participation à confirmer |

## Preuves de programme et points d'entrée

- [BMW : programmes prototypes WEC et IMSA en 2025](https://www.press.bmwgroup.com/global/article/attachment/T0446905EN/625752).
  Le M Hybrid V8 commence en IMSA en 2023 et en WEC en 2024 : ne pas attribuer
  automatiquement ce modèle aux saisons antérieures.
- [BMW : guide Motorrad 2025](https://www.press.bmwgroup.com/canada/article/detail/T0448209EN?forceSitePreference=DESKTOP).
- [BMW : bilan Motorrad 2025, usine et clients dans le monde](https://www.press.bmwgroup.com/global/article/attachment/T0454682EN/641940).
- [BMW : programmes Motorrad 2026](https://www.press.bmwgroup.com/usa/article/attachment/T0455315EN_US/643118).
- [Rapport officiel IGTC Suzuka 2025 avec BMW M4 GT3 EVO](https://www.intercontinentalgtchallenge.com/images/results/147/2025%20IGTC%20Suzuka%201000KM%20Aggregate%20Combined%20Classification%20Final.pdf).

Un communiqué prouve un programme annoncé ou des résultats rapportés ; il ne
remplace pas le calendrier, les engagés et les résultats de chaque course.

## Mesurer la couverture au lieu de promettre « toutes »

Construire un manifeste avec : discipline, organisateur, championnat, saison,
événement, date, circuit, session, preuve de participation BMW, type de preuve
(engagé, partant ou classé), URL source, famille du rapport, révision, période
couverte, format, statut d'accès, statut d'extraction et statut de validation.

Les statuts restent distincts : repéré, accessible, téléchargé, parsé, validé,
indisponible ou non applicable. Une URL HTTP 200 peut renvoyer du HTML au lieu
du document attendu. Un fichier manquant ne prouve pas l'absence de BMW.

La couverture est mesurée par championnat et saison : courses BMW confirmées,
courses aux documents disponibles, courses ingérées et courses validées.
Tant que les calendriers et engagements n'ont pas été réconciliés, le total
mondial attendu reste inconnu.

## Règles pour les tests et la modélisation

1. Tester un adaptateur par fournisseur et famille de document ; ne pas imposer
   `pit_stop_analysis` à WorldSBK, aux résultats ou à la météo.
2. Préserver chaque document et révision ; ne pas compter deux fois une course
   commune à plusieurs championnats, par exemple un événement GT et IGTC.
3. Distinguer course, manche et session. Une manche peut avoir plusieurs courses.
   DNS, DNF, DSQ, annulations et interruptions restent des faits à conserver.
4. Ne pas exiger d'arrêt au stand dans une course sprint moto. Séparer absent,
   inconnu et non applicable plutôt que remplir de zéros.
5. Identifier la compétition, saison et session avant de joindre les numéros
   de véhicule ou de pilote. Ne pas utiliser un numéro comme identité mondiale.
6. Conserver les concurrents non BMW pour les comparaisons ; sélectionner BMW
   dans les analyses, pas en supprimant prématurément les concurrents en Bronze.
7. Définir les unités et conventions temporelles par source : dates, fuseaux,
   minuit, durées, météo et révisions ne sont pas interchangeables.
8. Comparer source et sortie pour chaque document, avec contrôle du contenu
   et des types en plus des volumes ; tester les erreurs avant publication.
9. Garder `(50, 100, 137)` uniquement comme résultat attendu du fichier test
   Road America 2025, jamais comme obligation pour toutes les compétitions.
10. Vérifier les conditions d'utilisation par fournisseur, en particulier
    avant stockage automatisé ou redistribution de jeux de données publics.

## Séquence pédagogique

Concevoir dès maintenant le manifeste multi-saisons et multi-disciplines.
Valider ensuite un parcours complet auto et un parcours complet moto, puis
exécuter les mêmes contrôles sur les autres documents compatibles. Les formats
supplémentaires nécessitent leurs propres adaptateurs et tests. Cette séquence
ne réduit pas la cible mondiale ; elle évite de lancer une collecte de masse
avant de savoir interpréter les fichiers et mesurer les échecs.
