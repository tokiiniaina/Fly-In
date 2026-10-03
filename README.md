# Fly-in

Projet Python de lecture et de validation de cartes de zones et de connexions.

## Installation

```sh
make install
```

## Utilisation

```sh
make run MAP=maps/valid/example.map
```

Le format d'une carte est organisé en blocs :

```text
[metadata]
name = Demo

[zones]
Paris = city
Lyon = city

[connections]
Paris -> Lyon = 10
```

Les zones acceptent les types `city`, `airport` et `station`. Chaque ligne de
règle doit être autonome ; les lignes vides et les commentaires commençant par
`#` sont ignorés.

## Développement

```sh
make test
make lint
make debug MAP=maps/valid/example.map
```

Le cheminfinding, la simulation et l'affichage sont réservés aux prochaines
étapes.