# Naming proposals — successor to "agent-hub"

> Criteria : fidèle à ce que fait le projet (donner du contexte profond et
> fiable aux agents IA sur un codebase), distinctif, court, prononçable,
> pas saturé sur GitHub / PyPI. Pas de "Cortex", pas de "Codex".

Vérifs faites (au 2026-05-26) : `pypi.org/pypi/<name>/json` et
`api.github.com/repos/<name>/<name>`. GitHub a généralement *quelques* repos
avec le mot — l'objectif est d'éviter les projets dominants qui rendraient
la recherche pénible, pas le zéro absolu.

---

## Top 5 (recommandés)

### 1. **Trovus** ⭐
- **Sens** : du latin *trovare* / *invenire*, "trouver / mettre au jour".
  Renvoie à l'idée que l'outil **retrouve la connaissance enfouie** dans le
  repo.
- Court (6 lettres), prononçable EN/FR, sonne moderne.
- PyPI **libre**, aucun repo GH dominant trouvé.
- CLI naturelle : `trovus index`, `trovus ask`.

### 2. **Reliquus**
- **Sens** : latin "ce qui reste, ce qui subsiste". Métaphore du *savoir
  rémanent* du code (l'historique + la structure qui survivent aux devs).
- PyPI **libre**, GH **libre** (org).
- Un peu plus long mais très distinctif. Domain `.dev` probable.

### 3. **Heliograph**
- **Sens** : instrument du XIXᵉ qui transmettait des messages à distance par
  miroirs et soleil. Métaphore : "l'outil qui réfléchit / projette la vérité
  du code vers l'agent". Image forte et rare.
- PyPI **libre**, GH org **libre**.
- Plus long (10 lettres) mais très mémorisable. Logo facile.

### 4. **Canonis**
- **Sens** : "le canon" au sens de *référence faisant autorité*. L'outil qui
  donne la **version canonique** de ce que dit le code.
- PyPI **libre**, GH org **libre**.
- 7 lettres, prononçable, "ca-NO-nis".

### 5. **Trovus-Mind** / **Trovus-Lens** *(variants si Trovus seul trop court)*
- Compositions si on veut prévenir l'ambiguïté avec un nom commun futur.

---

## Honorables mentions (3-5)

### 6. **Syzygy**
- Astronomie : alignement de trois corps célestes. Symbolise *l'alignement*
  entre code, intention dev, et action agent.
- PyPI dispo, GH org dispo. Mais : prononciation difficile (SIZ-i-jee).
  Bonus de mémorabilité, malus d'oral.

### 7. **Tessera**
- Petit carreau de mosaïque romain ; aussi tessera hospitalis = jeton de
  reconnaissance. Métaphore : "chaque chunk de code = une tessera ; ensemble
  = la mosaïque (compréhension du repo)".
- PyPI dispo, GH org dispo.

### 8. **Gnomon**
- Tige du cadran solaire qui projette l'ombre. Métaphore : "petit objet
  inerte qui révèle la structure du système plus grand". Très image.
- PyPI dispo. GH : quelques projets mineurs.

### 9. **Capstan**
- Treuil vertical de marin qui *enroule* les cordages pour soulever
  l'ancre. Métaphore : "remonte le contexte enfoui".
- PyPI dispo, GH org dispo.

### 10. **Lodestone**
- Pierre magnétique naturelle — la première boussole. "Le repère qui
  oriente l'agent dans le repo".
- PyPI dispo, GH org dispo. Mais : un peu plus connu, sonne plus
  "marketing".

---

## À éviter (vérifié)

| Nom | Pourquoi non |
|-----|--------------|
| Cortex, Codex | Trop saturés (demande explicite) |
| Dossier | 5000+ repos GH (top: reasoncorp/dossier) |
| Stratum | Repo `stratum/stratum` existe au top |
| Gitlore | 34+ repos GH dont un CodAlpha visible |
| Palantir | Marque commerciale très connue |
| Oikos | 462 repos, signifiant grec déjà très utilisé |

---

## Recommandation finale

**Trovus** (premier choix) ou **Heliograph** (second) :

- Trovus = direct, court, action ("trouver") = aligné usage.
- Heliograph = plus poétique, plus mémorable visuellement, mais plus long.

Action si on tranche : réserver `trovus` ou `heliograph` sur PyPI
(`twine register`) et créer l'org GH correspondante avant qu'un autre
projet ne prenne le nom.
