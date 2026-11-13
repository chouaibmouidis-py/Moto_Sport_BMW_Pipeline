# Vérification automatique du dépôt

`Pipeline CI` démarre sur les push, les pull requests et les lancements manuels.
Il installe Python 3.12 et les dépendances verrouillées par `uv.lock`, puis
exécute les tests, vérifie les deux points d'entrée du package et contrôle les
identifiants du manifeste. Les exécutions précédentes de la même référence sont
annulées lorsqu'une nouvelle version arrive. Le jeton GitHub reste en lecture.

Les tests utilisent des données synthétiques, des fichiers temporaires et des
téléchargements simulés. Ils ne nécessitent pas les rapports dans `data/`.
L'installation des dépendances nécessite néanmoins un accès réseau.

Le workflow manuel `Manual IMSA source smoke check` conserve le téléchargement
réel d'une source historique. Ce contrôle ne constitue pas une exécution complète
des saisons et peut échouer lorsque le fournisseur est indisponible.

Ces workflows ne publient pas les Parquet et ne déploient pas le projet.
Après le push, vérifier leur résultat dans GitHub Actions. Pour rendre la CI
obligatoire avant fusion, configurer ensuite une règle de protection de branche
avec le contrôle `Python 3.12 tests` : le YAML seul n'impose pas cette règle.

La configuration suit la syntaxe officielle GitHub Actions et l'intégration uv :

- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- https://docs.astral.sh/uv/guides/integration/github/
