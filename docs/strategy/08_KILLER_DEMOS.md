# 08 — Les 3 démos qui doivent juste marcher

## Pourquoi des démos plutôt qu'une roadmap feature-par-feature

Une roadmap feature ("ajouter tool X, refactor Y, optimiser Z") laisse
toujours flotter la question : **est-ce que ça aide vraiment un dev ?**

Une démo concrète, scriptée, reproductible, donne une réponse binaire :
soit le flow marche en < 60s sur un repo réel, soit pas.

Définissons les 3 flows qui, s'ils marchent, prouvent qu'Agent Hub vaut
le coup. Tout investissement technique doit servir au moins un de ces 3
flows.

---

## Démo 1 — "Onboarding instantané sur un repo inconnu"

**Setup** : un dev clone un repo de 200k LOC qu'il n'a jamais vu.

**Avant Agent Hub** : 2-3h de lecture, navigation, grep, prise de notes
pour avoir une carte mentale.

**Avec Agent Hub** :

```
$ docker compose up -d           # 30s
$ ./scripts/index.sh ./repo      # 5 min cold index

# Dans Claude Code, branché sur l'endpoint MCP :
> Donne-moi une carte du système : modules principaux, points
  d'entrée, schémas de données, et 3 fichiers à lire en premier
  pour comprendre l'auth.
```

**Sortie attendue (< 30s)** :

- L0 résumé architectural (4-5 paragraphes).
- Liste des entrypoints (`main.py`, `cli.py`, route handlers...).
- Schéma data (depuis modèles SQLAlchemy/Pydantic détectés).
- 3 fichiers ranked par pertinence sur "auth", chacun avec `path:lineno`
  cliquable.

**Critère de succès** : le dev dit *"OK, je vois"* et commence à coder
en < 10 min après le clone.

**Bench correspondant** : RepoBench-R + LongCodeArena.

---

## Démo 2 — "Modification non destructrice dans un coin obscur"

**Setup** : un dev doit modifier une fonction utilisée à 12 endroits dans
4 services différents, sans rien casser.

**Sans Agent Hub** : grep, lecture des 12 callers, espoir.

**Avec Agent Hub** :

```
> Je veux modifier `process_order()` dans services/orders/handler.py
  pour ajouter un paramètre `dry_run`. Donne-moi :
  - tous les callers,
  - lesquels sont sur un chemin chaud (production),
  - les tests qui couvrent ces callers,
  - le patch minimal qui ajoute le paramètre avec default=False
    backward-compat, et les call sites à mettre à jour si je veux
    activer le dry_run pour les jobs cron.
```

**Sortie attendue (< 45s)** :

- `get_callers` → 12 sites listés avec path:lineno.
- `hot_path` → 3 sur chemin chaud (signalés ⚠️), 9 froids.
- `verify_patch_against_tests` → tests existants qui exercent ces
  callers.
- Patch unifié proposé, avec call sites mis à jour seulement pour les
  cron jobs.

**Critère de succès** : le patch passe les tests sans intervention
manuelle dans ≥ 70% des cas similaires.

**Bench correspondant** : SWE-bench Lite (les tâches "modify function
across files").

---

## Démo 3 — "Pourquoi ce code existe-t-il ?"

**Setup** : un dev tombe sur un bout de code bizarre, veut comprendre
l'historique.

**Sans Agent Hub** : `git blame`, ouvre le commit, lit le diff, cherche
le PR, lit les commentaires, parfois on trouve, souvent non.

**Avec Agent Hub** :

```
> Pourquoi `services/billing/retry.py:142-158` fait ce backoff
  bizarre avec `+ random.uniform(0, 5)` ? D'où ça vient ?
```

**Sortie attendue (< 15s)** :

- Commit qui a introduit ces lignes (via `blame_plus`).
- Message du commit + body.
- Issue / PR référencée si lien détecté (`#1234`).
- Si linked à un incident (label "postmortem" ou changelog enrichi) :
  résumé de l'incident.
- Liste des autres endroits du code modifiés dans le même PR (contexte
  de la décision).

**Critère de succès** : dans 80% des cas, le dev a la réponse sans
ouvrir GitHub.

**Bench correspondant** : interne (set de questions "why does this
exist" sur ce repo).

---

## Ce que ces 3 démos imposent comme priorités

Si on doit déployer le budget d'ingé sur 3 mois, voici le tri induit
par ces démos :

| Composant | Demo 1 | Demo 2 | Demo 3 | Priorité |
|-----------|--------|--------|--------|----------|
| Pyramide L0-L3 (existant) | ✅ critique | — | — | Garder, durcir |
| Indexation incrémentale (doc 04) | ✅ | ✅ | — | **P0** |
| Embeddings + rerank (doc 05) | ✅ | ✅ | ✅ | **P0** |
| Sub-agents (doc 02) | — | — | — | P2 (qualité interne) |
| Code World Model — coverage / hot path (doc 03) | — | ✅ critique | — | **P1** |
| Verify-patch-against-tests (doc 06) | — | ✅ | — | **P1** |
| Politiques Semgrep (doc 06) | — | optionnel | — | P2 |
| Changelog enrichi / incident linking (`blame_plus`) | — | — | ✅ critique | **P1** |
| Harnais d'éval (doc 07) | ✅ | ✅ | ✅ | **P0 absolu** |

**Aucune des démos ne demande SMT verification, world-model adaptatif,
ou regression-prediction**. Confirme le re-scope du doc 06.

---

## Comment "officialiser" ces démos

1. Chaque démo = un script reproductible sous `eval/demos/`.
2. Lancées en nightly contre un repo fixe (peut être ce repo lui-même au
   début).
3. Output diffé d'une nuit à l'autre.
4. Régression visible = alerte sur dashboard.

Quand les 3 démos marchent **toutes** de façon stable, Agent Hub a une
proposition de valeur défendable. Tant que ce n'est pas le cas, le reste
du backlog attend.
