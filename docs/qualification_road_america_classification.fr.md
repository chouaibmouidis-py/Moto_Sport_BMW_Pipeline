# Qualification — classement officiel de Road America 2025

Inspection initiale : 10 novembre 2026, avant intégration. Mise à jour du jalon :
11 novembre 2026. Les observations ci-dessous décrivent le document inspecté ;
la section finale distingue l'intégration réalisée du travail restant.

## Source et statut

- Championnat : IMSA WeatherTech SportsCar Championship.
- Événement : Motul SportsCar Grand Prix, Road America, Race.
- Document : `03_Results_Race_Official.JSON`.
- [Répertoire officiel](https://imsa.results.alkamelcloud.com/Results/25_2025/16_Road%20America/01_IMSA%20WeatherTech%20SportsCar%20Championship/202508031310_Race/).
- [JSON inspecté](https://imsa.results.alkamelcloud.com/Results/25_2025/16_Road%20America/01_IMSA%20WeatherTech%20SportsCar%20Championship/202508031310_Race/03_Results_Race_Official.JSON).
- `session.report_mark` vaut `Official`. Le répertoire expose aussi des versions
  Provisional et Unofficial : elles ne doivent pas être ingérées comme des
  courses supplémentaires.
- `session.creation_date` : `08-08-2025 10:12:17`, texte sans fuseau confirmé.

## Structure observée

Trois racines : `session`, `fastest_lap`, `classification`.

- `session` : contexte du document, météo, mode de fin, statut et message du rapport.
- `fastest_lap` : objet de référence du meilleur tour avec voiture, pilote,
  numéro du tour, durée et vitesse. À préserver séparément du classement.
- `classification` : 48 entrées et 48 numéros textuels distincts. Une ligne
  du tableau décrit un participant dans ce rapport de classement.
- Chaque participant contient une liste `drivers`. La déplier dans une table
  séparée évitera de multiplier les lignes du classement.

Champs renseignés au moins une fois dans les participants, hors liste drivers :
`status`, `not_finished`, `position`, `number`, `elapsed_time`,
`fastest_lap_number`, `fastest_lap_time`, `fastest_lap_kph`,
`fastest_lap_driver_number`, `time`, `gap_first`, `gap_previous`, `kph`,
`laps`, `pit_stops`, `team`, `class`, `group`, `vehicle`, `tires`, `manufacturer`.
Les alias apparents (`time`/`fastest_lap_time`, `kph`/`fastest_lap_kph`) restent
à comparer sur l'ensemble des lignes avant toute suppression de champ.

Types observés : `position` et `fastest_lap_driver_number` numériques,
`not_finished` booléen ; numéros de voiture, tours et nombre d'arrêts sont
représentés comme textes dans le JSON. Les écarts mêlent une indication
initiale `-` et d'autres représentations à inventorier avant conversion.

## Premiers résultats BMW

Les positions ci-dessous sont celles du classement général, pas des positions
recalculées dans chaque classe.

| Voiture | Position | Classe | Tours | Arrêts déclarés |
| --- | ---: | --- | ---: | ---: |
| 24 | 1 | GTP | 66 | 3 |
| 25 | 2 | GTP | 66 | 2 |
| 1 | 24 | GTDPRO | 62 | 3 |
| 96 | 31 | GTD | 62 | 3 |
| 48 | 41 | GTDPRO | 62 | 4 |

## Écarts à traiter avant les jointures

1. Le classement contient 48 participants ; le rapport d'arrêts contient
   50 fragments pour 47 numéros distincts. Tous les numéros des stands sont
   présents au classement. Le numéro `70` est présent uniquement au classement :
   quatre tours, zéro arrêt déclaré, `not_finished: true`.
2. Toutes les entrées du classement ont ici `status: Classified`, y compris
   la voiture 70. Ce statut ne suffit donc pas à déterminer si la voiture a
   terminé : conserver aussi le booléen `not_finished`.
3. La date de session est `03-08-2025 01:10`, contre `03/08/2025 01:10` dans
   le document des stands. Le parseur actuel `%d/%m/%Y` ne convient pas tel quel.
4. Les températures diffèrent : air/piste 25.22/35.56 ºC dans le classement,
   contre 17.89/21.11 ºC dans le rapport des stands. Ce sont des contextes de
   documents ; ne pas les écraser ou les traiter comme des mesures simultanées.
5. Le message du rapport officiel mentionne l'invalidation de certains tours
   pour dépassement des limites de piste. Il est renseigné et doit être conservé.
6. Les deux rapports ont des identifiants de source et des empreintes différents.
   La jointure entre familles ne peut pas exiger l'égalité de `source_id` ou
   de `bronze_sha256`. Définir une correspondance explicite championnat,
   saison, événement, session, puis numéro textuel de voiture, tout en gardant
   la provenance et la version de chaque document.

## Conséquences identifiées lors de la qualification initiale

- Le téléchargeur actuel impose le nom du fichier des arrêts. Il faudra rendre
  la destination configurable et tester que les familles ne s'écrasent pas.
- La construction Bronze actuelle fixe les racines `session` et
  `pit_stop_analysis`. Elle ne doit pas être appliquée au classement : préserver
  ses trois racines avec une ingestion adaptée, avant les projections Silver.
- Les scripts sélectionnent uniquement `document_type: pit_stops`. Ajouter une
  entrée au manifeste ne suffit pas à intégrer un classement.
- Le contexte de session doit conserver le statut, le message et la famille du
  rapport ; la règle d'exclusion des champs vides doit être réévaluée sur les
  documents effectivement pris en charge.
- Pour un futur mart de résultats, partir du classement et joindre les arrêts
  agrégés par voiture permet de conserver la voiture 70. Distinguer absence
  de rapport, absence de correspondance et zéro arrêt établi.

## Critères de réception proposés

- Document et métadonnées conservés sans altération, avec les trois racines.
- 48 participants et cinq engagements BMW dans le jeu de référence.
- Numéros textuels préservés, classe et position générale distinguées.
- Voiture 70 conservée avec zéro arrêt déclaré et indicateur de non-fin.
- Dates avec tirets testées ; version officielle et message conservés.
- Jointure entre familles documentée et testée sans multiplication de lignes.
- Non-régression du pipeline actuel des trois rapports d'arrêts.

## Écarts observés lors du rapprochement réel

Lecture des Raw locaux vérifiés le 11 novembre 2026 :

| Voiture | Arrêts déclarés au classement | Arrêts détaillés retrouvés | Statut |
| --- | ---: | ---: | --- |
| 22 | 1 | 2 (numéros 1 et 2) | `count_mismatch` |
| 88 | 4 | 3 (numéros 1, 2 et 3) | `count_mismatch` |
| 70 | 0 | Aucune ligne | `zero_reported_no_detail` |

Les deux écarts numériques sont présents dans les documents sources ; leur cause
reste à investiguer. Le contrôle signale la divergence et conserve les deux
versions documentaires, sans affirmer qu'un rapport est erroné ni réécrire les
comptages. La réussite des tests de code n'implique pas l'égalité de toutes les
valeurs issues de deux rapports publics différents.

## État d'intégration au 11 novembre 2026

- Source activée dans le manifeste avec son propre `source_id` et `filename`.
- Téléchargement paramétrable, métadonnées SHA-256, réutilisation du Raw vérifié
  et rafraîchissement explicite via `--refresh`.
- Bronze distincte : trois racines conservées, relues et comparées au JSON
  avant remplacement du fichier final.
- Silver de 48 participants avec provenance, index source, numéro textuel,
  position générale, classe, nombre d'arrêts déclaré et `not_finished`.
- Correspondance des rapports par championnat, saison, événement et session ;
  candidats multiples et rapport absent refusés. Comptages d'arrêts associés
  à la version chargée, puis jointure conservant les participants sans détail.
- Rapport de comparaison publié dans le run candidat et consulté par le lecteur
  qualité à partir de la même référence active que les autres résultats.
- Scénarios synthétiques : conservation du participant sans détail, exclusion
  d'une autre version, écart de comptage et détail absent avec comptage déclaré
  non nul. Des tests distincts couvrent la sélection et les contrôles de clés.

La projection Silver du classement reste partielle. La normalisation des dates
à tirets, le contexte météo, le message officiel, les pilotes du classement et
le meilleur tour ne sont pas encore intégrés à des tables Silver dédiées : ces
informations restent préservées en Bronze. Les critères de réception ci-dessus
ne sont donc pas tous satisfaits. Le parcours commun reste limité à un classement
activé ; une extension multi-classements doit adapter le chargement avant
d'élargir le manifeste.
