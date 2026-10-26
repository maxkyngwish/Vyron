<div align="center">

<img src="vyron/assets/vyron-wordmark-xl.png" alt="VYRON" width="340">

**Un compagnon de jeu Windows lÃ©ger qui libÃ¨re vraiment des ressources.**

[![Plateforme](https://img.shields.io/badge/plateforme-Windows%2010%20%7C%2011-0C1712?style=flat-square&logo=windows11&logoColor=B6FF38)](#installation)
[![Python](https://img.shields.io/badge/python-3.10%2B-0C1712?style=flat-square&logo=python&logoColor=B6FF38)](https://www.python.org/downloads/)
[![Licence](https://img.shields.io/badge/licence-MIT-0C1712?style=flat-square)](LICENSE)
[![TÃ©lÃ©mÃ©trie](https://img.shields.io/badge/t%C3%A9l%C3%A9m%C3%A9trie-aucune-0C1712?style=flat-square)](README.md#confidentialitÃ©)

[English](README.md) Â· **FranÃ§ais**

</div>

![AperÃ§u de VYRON](docs/screenshots/01-overview.png)

VYRON dÃ©tecte le jeu que tu lances, lui rend du CPU et de la RAM, applique de
vrais rÃ©glages de performance Windows â€” et annule chacun d'eux quand tu arrÃªtes
de jouer. Pas de compte en ligne, pas de tÃ©lÃ©mÃ©trie, pas de droits
administrateur, pas de fenÃªtre de console.

**Made by Maxkingwish** Â· [RÃ¨gles d'attribution](ATTRIBUTION.md)

## Pourquoi VYRON

La plupart des Â« boosters Â» ferment trois processus et s'arrÃªtent lÃ . VYRON fait
le travail mesurable :

- dÃ©tecte le jeu tout seul (Steam, Epic, GOG, Xbox, Ubisoft, EA, Riot, jeux autonomes) ;
- passe les navigateurs, launchers et clients de synchro en **mode EfficacitÃ©**
  de Windows, vide leur mÃ©moire de travail et peut les **geler** pendant la partie ;
- monte le jeu en prioritÃ© Above Normal, avec tous les cÅ“urs et une I/O Ã©levÃ©e ;
- dÃ©sactive les optimisations plein Ã©cran et sÃ©lectionne le GPU performant pour
  ce jeu ;
- demande Ã  Windows une **minuterie 1 ms** pour stabiliser le frame pacing ;
- restaure prioritÃ©s, RAM, valeurs de registre, plan d'alimentation et minuterie
  Ã  la sortie du jeu â€” et mÃªme aprÃ¨s un crash.

## FonctionnalitÃ©s

### DÃ©tection des jeux
DÃ©tection automatique faÃ§on Discord, par nom d'exÃ©cutable ou dossier
d'installation, affichÃ©e dans la barre latÃ©rale, sur l'AperÃ§u et dans le Game
Center. Un sÃ©lecteur manuel Â« choisir une app en cours Â» reste disponible, et les
faux positifs peuvent Ãªtre ignorÃ©s avec **Pas un jeu** (restaurable dans
ParamÃ¨tres).

### Boost FPS (rÃ©versible)
- **Profil de jeu** â€” optimisations plein Ã©cran dÃ©sactivÃ©es, GPU performant,
  upgrade de swap-effect DXGI. Par jeu, `HKCU` uniquement, avec la valeur
  d'origine sauvegardÃ©e.
- **Applis en arriÃ¨re-plan** â€” regroupÃ©es comme le Gestionnaire des tÃ¢ches
  (`Microsoft Edge Â· 14 processus Â· 810 Mo`) avec **Optimiser** (mode EfficacitÃ©
  + prioritÃ© Below Normal + nettoyage de la mÃ©moire) et **Fermer** (confirmation
  d'abord).
- **Suspendre les applis lourdes en jeu** â€” les gÃ¨le complÃ¨tement ; l'appli sur
  laquelle tu passes se rÃ©veille en moins d'une seconde. Tout reprend Ã  la sortie
  du jeu. Une appli gelÃ©e est notÃ©e sur disque : mÃªme un kill forcÃ© est rÃ©parÃ© au
  prochain dÃ©marrage.
- **Minuterie systÃ¨me 1 ms** â€” demandÃ©e pendant la partie, relÃ¢chÃ©e aprÃ¨s.
- **RÃ©glage du processus du jeu** â€” prioritÃ© Above Normal, tous les cÅ“urs, I/O
  haute, et jamais en mode EfficacitÃ©.

### Surveillance
Anneaux CPU, RAM et stockage en direct ; usage et tempÃ©rature du GPU NVIDIA via
`nvidia-smi` (mis en cache et interrogÃ© seulement quand la page Performances est
visible).

### Serveurs
Teste les rÃ©gions de rÃ©fÃ©rence cloud en parallÃ¨le sur TCP/443 et les classe de la
plus rapide Ã  la plus lente, avec perte de paquets et Ã©tats inaccessibles.
**Il mesure l'aller-retour vers des points de rÃ©fÃ©rence, pas vers le serveur de
ton jeu, et VYRON ne crÃ©e pas de tunnel VPN.** Choisir une rÃ©gion enregistre
seulement ta prÃ©fÃ©rence.

### Comptes et bibliothÃ¨que
Comptes locaux uniquement : PBKDF2-HMAC-SHA256 + sel alÃ©atoire, aucun rÃ©seau.
BibliothÃ¨que de jeux par compte avec lancement en un clic. Le mode invitÃ© marche
pour tout sauf le moteur de boost.

### Six langues
Anglais, franÃ§ais, russe, italien, espagnol, portugais â€” changeables Ã  tout
moment.

## Le boost, honnÃªtement

| RÃ©glage | PortÃ©e | RestaurÃ© par |
| --- | --- | --- |
| Mode Jeu, DVR et capture dÃ©sactivÃ©s | `HKCU` | **Restaurer**, sortie de jeu, fermeture |
| Plan Performances Ã©levÃ©es | seulement en jeu, jamais sur batterie | sortie de jeu, fermeture |
| PrioritÃ© / affinitÃ© / I-O du jeu | processus du jeu | sortie de jeu |
| Profil plein Ã©cran + GPU | un jeu, `HKCU` | **Restaurer** ou dÃ©sactivation de l'option |
| Minuterie 1 ms | processus | sortie de jeu, fermeture |
| Applis bridÃ©es | processus utilisateur | sortie de jeu, **Restaurer les applis**, fermeture, `atexit` |
| Applis gelÃ©es | processus utilisateur | idem + prochain dÃ©marrage aprÃ¨s un crash |

VYRON ne dÃ©sactive jamais les services de sÃ©curitÃ©, n'utilise jamais la prioritÃ©
`REALTIME`, ne tue jamais un processus automatiquement et n'Ã©crit rien en dehors
de `HKCU` ou du dossier de l'utilisateur. Les gains dÃ©pendent du matÃ©riel, des
pilotes, des tempÃ©ratures et de ce qui tournait en fond ; aucun outil ne peut
promettre un nombre de FPS fixe.

## Captures d'Ã©cran

| Moteur de boost | FPS et applis de fond |
| --- | --- |
| ![Boost](docs/screenshots/02-boost.png) | ![Boost FPS](docs/screenshots/03-boost-fps.png) |

| Latence des rÃ©gions | |
| --- | --- |
| ![Serveurs](docs/screenshots/04-servers.png) | |

## Installation

### Option A â€” exÃ©cutable prÃªt Ã  l'emploi
TÃ©lÃ©charge `VYRON.exe` depuis les Releases et lance-le. Aucun Python nÃ©cessaire.

> L'exÃ©cutable n'est pas signÃ© : SmartScreen peut prÃ©venir la premiÃ¨re fois.
> Clique sur **Informations complÃ©mentaires â†’ ExÃ©cuter quand mÃªme**, ou compile-le
> toi-mÃªme depuis les sources.

### Option B â€” scripts en un clic (depuis les sources)
1. Installe [Python 3.10+](https://www.python.org/downloads/) en cochant
   **Add Python to PATH**.
2. Double-clique sur **`VYRON.vbs`** â€” lancement silencieux, sans console. Il
   installe les deux dÃ©pendances au premier lancement si besoin.
3. `INSTALL_VYRON.bat` affiche la sortie d'installation en cas de problÃ¨me ;
   `RUN_VYRON.bat` est un raccourci vers le lanceur silencieux.

### Option C â€” manuel
```powershell
git clone https://github.com/maxkyngwish/Vyron.git
cd Vyron
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

### Compiler l'exÃ©cutable
```powershell
BUILD_VYRON_EXE.bat
```
ou
```powershell
python -m pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name VYRON ^
  --icon "vyron\assets\vyron.ico" ^
  --add-data "vyron\assets;vyron\assets" --collect-all customtkinter main.py
```
RÃ©sultat : `dist\VYRON.exe` (icÃ´ne de fenÃªtre et de barre des tÃ¢ches incluse, pas
de console).

## Ce que VYRON Ã©crit sur ton PC

| Chemin | Contenu |
| --- | --- |
| `%USERPROFILE%\.vyron_settings.json` | langue, session mÃ©morisÃ©e, prÃ©fÃ©rences de boost |
| `%USERPROFILE%\.vyron_accounts.json` | comptes locaux (hashes PBKDF2) et bibliothÃ¨ques |
| `%USERPROFILE%\.vyron_suspended.json` | applis gelÃ©es, pour la rÃ©cupÃ©ration aprÃ¨s crash |
| `%USERPROFILE%\.vyron_crash.log` | erreurs de dÃ©marrage uniquement |
| `HKCU\Software\Microsoft\GameBar` | Mode Jeu, restaurÃ© par **Restaurer** |
| `HKCU\System\GameConfigStore` + `...\GameDVR` | DVR/capture, restaurÃ©s par **Restaurer** |
| `HKCU\...\AppCompatFlags\Layers` | indicateur plein Ã©cran, par jeu |
| `HKCU\Software\Microsoft\DirectX\UserGpuPreferences` | prÃ©fÃ©rence GPU et swap-effect, par jeu |

Rien n'est envoyÃ© nulle part. Supprime les quatre fichiers ci-dessus pour
rÃ©initialiser VYRON complÃ¨tement.

## ConfidentialitÃ©

- Aucune tÃ©lÃ©mÃ©trie, aucun analytics, aucun compte distant, aucun ping de mise Ã 
  jour.
- Seul trafic rÃ©seau : les tests de latence que tu lances, le test de ping
  optionnel, et le trafic de tes jeux.
- Comptes et rÃ©glages ne quittent jamais la machine.

## Structure du projet

```
main.py                 point d'entrÃ©e et dialogue d'erreur
vyron/
  app.py                interface, pages, polling, cÃ¢blage
  boost.py              registre, plan d'alimentation, minuterie, profil de jeu
  trim.py               applis de fond : groupes, bridage, suspension, restauration
  detection.py          dÃ©tection des jeux et exclusions
  system_info.py        snapshot lÃ©ger, GPU en cache, ping
  servers.py            rÃ©gions et tests de latence concurrents
  accounts.py           comptes locaux et bibliothÃ¨ques
  i18n*.py              chaÃ®nes en six langues
  processes.py          Ã©numÃ©ration des fenÃªtres/processus
  assets/               logo, wordmark et icÃ´ne
tools/
  make_assets.py        rÃ©gÃ©nÃ¨re les images de marque
  check_attribution.py  protÃ¨ge la mention Â« Made by Maxkingwish Â»
docs/screenshots/       images du README
```

DÃ©pendances d'exÃ©cution : **CustomTkinter** et **psutil** uniquement. Tout le
reste est la bibliothÃ¨que standard Python, et VYRON se place lui-mÃªme en prioritÃ©
Below Normal pour ne jamais concurrencer le jeu.

## DÃ©pannage

| SymptÃ´me | Solution |
| --- | --- |
| Rien ne se passe au double-clic | Lance `INSTALL_VYRON.bat` pour voir l'erreur, ou `python main.py` dans un terminal. |
| Â« Python 3.10 ou plus est requis Â» | RÃ©installe Python en cochant **Add Python to PATH**. |
| Certains rÃ©glages sont partiels / demandent admin | VYRON est conÃ§u pour un utilisateur standard ; les rÃ©glages restants nÃ©cessitent une session Ã©levÃ©e et sont ignorÃ©s proprement. |
| Le jeu n'est pas dÃ©tectÃ© | Utilise **Game Center â†’ choisir une app en cours**, ou ajoute le jeu manuellement. |
| Une appli de fond semble lente | Boost â†’ **Restaurer les applis**, ou dÃ©coche *Suspendre les applis lourdes*. |
| Erreur au dÃ©marrage | Voir `%USERPROFILE%\.vyron_crash.log`. |

## FAQ

**Est-ce que Ã§a augmente vraiment les FPS ?**
Ã‡a supprime de vrais freins : contention CPU/RAM en fond, composition plein
Ã©cran, granularitÃ© de la minuterie et choix du GPU. Le gain dÃ©pend du PC et de ce
qui tournait. VYRON reste honnÃªte et ne promet jamais un chiffre fixe.

**Faut-il Ãªtre administrateur ?**
Non. Tout est par utilisateur (`HKCU`, prioritÃ©s de processus). Les rares
rÃ©glages qui exigeraient admin sont ignorÃ©s avec un message clair.

**Est-ce que Ã§a ferme mes applis ?**
Jamais automatiquement. **Fermer** demande toujours confirmation. L'optimiseur
ne fait que ralentir ou geler, puis restaure.

**Peut-on tout annuler ?**
Oui : **Restaurer** sur la page Boost, la sortie du jeu, ou la fermeture de
VYRON. MÃªme un crash est rÃ©cupÃ©rÃ© au dÃ©marrage suivant.

**Mes donnÃ©es sont-elles envoyÃ©es ?**
Non. Les comptes sont locaux, hachÃ©s en PBKDF2-HMAC-SHA256.

## Contribuer

Les issues et pull requests sont bienvenues. Lis [AGENTS.md](AGENTS.md) (rÃ¨gles du
projet) et lance :

```powershell
py -m compileall -q vyron tools main.py
py tools/check_attribution.py
```

La mention **Made by Maxkingwish** doit rester visible et inchangÃ©e partout â€” voir
[ATTRIBUTION.md](ATTRIBUTION.md). Cela vaut aussi pour les forks et les
changements gÃ©nÃ©rÃ©s par IA.

## CrÃ©dits et attribution

CrÃ©Ã© et maintenu par **Maxkingwish**.

La mention `Made by Maxkingwish` est protÃ©gÃ©e : elle ne peut Ãªtre ni supprimÃ©e, ni
traduite, ni raccourcie, ni cachÃ©e, ni recouverte. DÃ©tails et vÃ©rification :
[ATTRIBUTION.md](ATTRIBUTION.md) Â· `tools/check_attribution.py`.

<img src="docs/screenshots/05-about.png" alt="La page Ã€ PROPOS affiche la mention protÃ©gÃ©e" width="760">

Construit avec [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) et
[psutil](https://github.com/giampaolo/psutil).

## Licence

[MIT](LICENSE) Â© 2026 Maxkingwish.
