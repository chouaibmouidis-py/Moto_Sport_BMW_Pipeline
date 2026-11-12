# Qualification Laguna Seca et Detroit 2024

Inspection et validation du 12 novembre 2026. Les quatre sources du manifeste
sont marquées `tested_locally` après publication complète et activation du run.

| Course | Session | Participants | BMW | Entrées voitures | Pilotes | Arrêts | Arrêts BMW | Écarts de comptage |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Laguna Seca | 202405121210-race | 34 | 4 | 34 | 68 | 85 | 9 | 1 (2,94 %) |
| Detroit | 202406011510-race | 21 | 3 | 21 | 42 | 35 | 4 | 2 (9,52 %) |

[Rapports Laguna Seca](https://imsa.results.alkamelcloud.com/Results/24_2024/08_Weathertech%20Raceway%20Laguna%20Seca/01_IMSA%20WeatherTech%20SportsCar%20Championship/202405121210_Race/).
[Rapports Detroit](https://imsa.results.alkamelcloud.com/Results/24_2024/09_Detroit%20Street%20Course/01_IMSA%20WeatherTech%20SportsCar%20Championship/202406011510_Race/).
Chaque session expose `03_Results_Race_Official.JSON` (marqué Official)
et `20_Pit Stops Time Cards_Race.JSON`.

Écarts déclarés/détaillés : Laguna Seca, voiture 34 (3/2) ; Detroit,
voiture 35 (2/1) et voiture 64 (1/2). Causes non établies ; valeurs conservées.
Les données source restent la référence pour le modèle exact, sans conversion
automatique de GT3 en GT3 EVO.

Références cumulées attendues avec 2025 et Road America 2024 :
571 participations dont 59 BMW, 4 400 arrêts dont 409 BMW,
611 entrées voitures, 1 552 entrées pilotes et 14 bilans qualité.
Ces volumes ne valident pas à eux seuls les conversions, clés et jointures.
La transformation et la publication complètes ont confirmé ces volumes ;
la lecture métier détaillée reste disponible dans les lecteurs du projet.

Validation effectuée par l'agent : les douze sorties ont été publiées et le run
`f0526cabb65d425b9007cec9ca5ab637` activé. La suite complète passe (105 tests).
Le contrôle exact a révélé deux instabilités de calcul flottant : somme des
durées et moyenne à la limite du demi-millième. Le total est arrondi à trois
décimales ; la moyenne utilise une somme en DECIMAL(18,3) avant division.
Le contrôle de contenu reste exact et son message identifie désormais la sortie.
