# Couverture de la saison IMSA WeatherTech 2025

Objectif défini le 12 novembre 2026 : couvrir les courses de la saison 2025,
tous circuits confondus, pour les deux familles classement et arrêts détaillés.
Ce périmètre concerne WeatherTech, pas l'ensemble des championnats IMSA.

## Référentiel des courses

Point de départ : [annonce officielle du calendrier de onze courses](https://www.imsa.com/news/2024/march/15/imsa-announces-2025-schedules-for-weathertech-championship-michelin-pilot-challenge).
Cette annonce antérieure à la saison sert à dresser la liste des événements ;
les sessions réellement disputées, dates définitives, classes et documents
doivent être vérifiés dans les résultats officiels. Les dates de l'annonce
ne sont pas utilisées pour fabriquer les chemins de téléchargement.

| Événement / circuit | Classement + arrêts | Prochaine vérification |
| --- | --- | --- |
| Daytona | Intégrés et validés localement | Conserver le couple de rapports heure 24 |
| Sebring | Intégrés et validés localement | Couple final heure 12, écarts conservés |
| Long Beach | Intégrés et validés localement | Cas sans détail conservé |
| Laguna Seca | Intégrés et validés localement | Voiture 70 : écart de comptage conservé |
| Detroit | Intégrés et validés localement | Aucun écart de comptage dans le lot inspecté |
| Watkins Glen | Intégrés et validés localement | Couple final heure 6, écarts conservés |
| Canadian Tire Motorsport Park | Intégrés et validés localement | LMP2 et GT ; trois BMW GT |
| Road America | Intégrés et validés localement | Écarts de comptage conservés |
| VIRginia International Raceway | Intégrés et validés localement | GT uniquement ; trois BMW |
| Indianapolis | Intégrés et validés localement | Couple final heure 6 |
| Road Atlanta / Petit Le Mans | Intégrés et validés localement | Couple final heure 10 |

Les onze courses sont intégrées pour les deux familles : classement et arrêts.
Le manifeste comporte vingt-deux documents activés. Le run actif
`57425c9ee72947108831adc8aa6232ad` a été relu par l'agent : 469 participations,
4 117 arrêts détaillés, dont 388 BMW, et onze bilans qualité. Chouaib confirme
48 participations BMW. Ce périmètre ne couvre pas les autres familles de
rapports ni les autres championnats IMSA.
Une absence de rapport doit être documentée, pas assimilée à zéro arrêt ou à
l'absence de BMW. Les engagements non BMW restent conservés.

## Progression par lots

1. Lot Laguna Seca et Detroit terminé : qualification puis exécution du pipeline
   et lecture des sorties confirmées par Chouaib le 12 novembre 2026. Les cinq
   courses réunissent 194 participations classées, dont 22 BMW, et 1 915 arrêts
   détaillés. Laguna Seca : un écart sur 36 (2,78 %) ; Detroit : aucun sur 22.
2. Lot Sebring et Watkins Glen intégré : rapports finaux heure 12 et heure 6,
   sans addition des cumuls horaires. Chouaib confirme le run
   `cf43b04e5ef849e38aafe0f07c16aec2` : 305 participations, dont 32 BMW,
   3 018 arrêts rattachés et enrichis, dont 285 BMW.
3. Lot Canadian Tire Motorsport Park et VIR intégré. Volumes confirmés par
   Chouaib : 363 participations, dont 38 BMW ; 3 183 arrêts, dont 300 BMW ;
   neuf bilans qualité. Absence de GTP conforme aux catégories des rapports.
4. Indianapolis et Road Atlanta intégrés. Les onze événements du référentiel
   sont représentés, chacun par un classement et un rapport d'arrêts final.
   Les écarts de comptage sont conservés et ne constituent pas une couverture
   manquante. La suite de tests est à rejouer pour clôturer la livraison.

Pour chaque lot : documents qualifiés, configuration explicite, exécution,
contrôles par course, documentation des écarts et commit local. Aucun volume
de participants ni seuil d'anomalies n'est supposé identique entre les courses.
Le pipeline conserve sa règle de refus des lots activés incomplets.
