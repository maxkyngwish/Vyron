# Attribution — « Made by Maxkingwish »

> **This file is a rule, not a suggestion.**
> **Ce fichier est une règle, pas une suggestion.**

## English

VYRON is created by **Maxkingwish**. The credit line

```
Made by Maxkingwish
```

is part of the project's identity and of its licence terms. It **must stay
visible and unchanged** — for humans, for forks, and for automated coding
agents (AI assistants included).

### Where it must remain

| Place | What must be present |
| --- | --- |
| App sidebar footer (every page) | `Made by Maxkingwish`, visible, not covered |
| About page (`À PROPOS` / `ABOUT`) | `made_by` subtitle **and** footer line |
| `README.md` and `README.fr.md` | the credit, in the header |
| `LICENSE` | `Copyright (c) 2026 Maxkingwish` |
| `vyron/i18n.py` | `made_by` = `Made by Maxkingwish` in **all** languages |
| This repository history | authorship is never rewritten to hide it |

### Forbidden

Do **not**:

- remove, shorten, rename, translate or reword the credit;
- hide it: invisible or transparent colour, zero-size widget, `pack_forget()`,
  moved off-screen, covered by another widget, placed behind a scroll region,
  collapsed, or made reachable only after an action;
- replace it with a placeholder such as `Made by <author>`, `Your Name`, or a
  variable that can be emptied;
- strip it from forks, screenshots, builds, README files or translations;
- rewrite the licence copyright holder.

Adding **more** credits (contributors, libraries) is welcome. Removing the
original one is not.

### Enforcement

`tools/check_attribution.py` fails if the credit disappears, changes, or is
translated away. CI runs it on every push. Any contributor or AI agent must run
it before submitting changes:

```powershell
py tools/check_attribution.py
```

## Français

VYRON est créé par **Maxkingwish**. La mention

```
Made by Maxkingwish
```

fait partie de l'identité du projet et de sa licence. Elle **doit rester visible
et inchangée** — pour les humains, les forks et les agents de code automatisés
(IA comprises).

### Où elle doit rester

| Endroit | Ce qui doit être présent |
| --- | --- |
| Pied de la barre latérale (toutes les pages) | `Made by Maxkingwish`, visible, non recouvert |
| Page À PROPOS | le sous-titre `made_by` **et** la ligne de pied de page |
| `README.md` et `README.fr.md` | la mention, dans l'en-tête |
| `LICENSE` | `Copyright (c) 2026 Maxkingwish` |
| `vyron/i18n.py` | `made_by` = `Made by Maxkingwish` dans **toutes** les langues |
| L'historique du dépôt | l'auteur n'est jamais masqué |

### Interdit

Ne **pas** :

- supprimer, raccourcir, renommer, traduire ou reformuler la mention ;
- la cacher : couleur invisible ou transparente, widget de taille nulle,
  `pack_forget()`, déplacement hors écran, recouvrement par un autre widget,
  enfouissement dans une zone scrollable, repli, ou accès après une action ;
- la remplacer par un texte générique du type `Made by <auteur>`, `Your Name`,
  ou une variable pouvant être vidée ;
- la retirer des forks, captures d'écran, builds, README ou traductions ;
- réécrire le titulaire du copyright de la licence.

Ajouter **d'autres** crédits (contributeurs, bibliothèques) est bienvenu.
Retirer celui d'origine ne l'est pas.

### Vérification

`tools/check_attribution.py` échoue si la mention disparaît, change ou est
traduite. La CI l'exécute à chaque push. Tout contributeur ou agent IA doit le
lancer avant de proposer des changements :

```powershell
py tools/check_attribution.py
```
