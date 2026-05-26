# 03 — Code World Model : statique + runtime

## L'idée en une phrase

**Un graphe d'appel statique dit ce qui *peut* arriver. Une trace runtime dit
ce qui *arrive vraiment*. La fusion des deux donne un modèle du comportement
du système — c'est ça qui rend les réponses de l'agent fiables.**

---

## Pourquoi le statique seul ne suffit pas

Le graphe tree-sitter actuel (`src/graph/`) capture :

- Définitions de fonctions, classes, imports.
- Relations d'appel *syntaxiques* (foo() appelle bar()).
- Hiérarchies d'héritage.

Ce qu'il **rate** :

- **Dispatch dynamique** : `handler = HANDLERS[event_type]; handler(x)` → le
  graphe statique voit `handler(x)`, pas la fonction réelle appelée.
- **Frameworks par convention** : routes Flask/FastAPI, hooks React, signals
  Django, listeners Kafka. Reliés par strings ou décorateurs, invisibles à un
  AST naïf.
- **Hot path réel** : sur 800 fonctions, lesquelles tournent 10000 fois par
  seconde et lesquelles jamais ? Le statique l'ignore. C'est pourtant la
  donnée n°1 pour prioriser une review.
- **Latence, allocations, IO** : invisible sans profilage.

Conséquence : un agent qui ne s'appuie que sur le graphe statique
**sur-estime** les chemins improbables et **sous-estime** les chemins chauds.

---

## La fusion : Code World Model (CWM)

Concept popularisé en 2025 par les travaux Meta (CodeCompass), DeepMind
(AlphaCode traces), et la communauté Continue Dev ("Devtime").

```
┌──────────────────┐      ┌──────────────────┐
│  Static Graph    │      │ Runtime Traces   │
│  (tree-sitter)   │      │ (OTel, eBPF,     │
│                  │      │  language hooks) │
└─────────┬────────┘      └────────┬─────────┘
          │                        │
          └───────────┬────────────┘
                      ▼
          ┌─────────────────────────┐
          │  Enriched Graph         │
          │  - edges weighted by    │
          │    observed frequency   │
          │  - dispatch resolved    │
          │  - hot paths flagged    │
          │  - IO/latency annotated │
          └────────────┬────────────┘
                       │
                       ▼
          MCP tools : preview_impact, find_hub_modules, ...
          deviennent *vraiment* utiles
```

---

## Sources de traces utiles, par ordre d'effort croissant

| Source | Effort intégration | Valeur | Notes |
|--------|--------------------|--------|-------|
| **Logs structurés existants** | Très bas | Moyenne | Parser `logger.info` JSON déjà en place |
| **Stack traces d'erreurs** | Bas | Haute | Sentry export, ou parsing `*.log` en CI |
| **Test coverage** (pytest-cov, c8, jacoco) | Bas | Haute | Marque les chemins effectivement exercés |
| **OpenTelemetry spans** | Moyen | Très haute | Standard, multilangue, déjà adopté par 90% des stacks modernes |
| **eBPF (bcc, bpftrace, Parca)** | Élevé | Très haute | Profilage 0-instrumentation, niveau noyau, Linux only |
| **Replay debuggers** (rr, Pernosco) | Élevé | Maximale | Niche, mais permet de répondre à "que s'est-il passé à 14h32 ?" |

**Stratégie d'attaque** : commencer par **coverage + OTel spans**. C'est le
meilleur ratio valeur/effort. eBPF en option avancée.

---

## Tools MCP que ça débloque

| Nouveau tool | Question qu'il répond |
|--------------|------------------------|
| `hot_path` | "Quelles fonctions sont sur le chemin chaud de la requête X ?" |
| `actual_callers(fn)` | "Qui appelle cette fonction *en production*, pas juste en théorie ?" |
| `dead_code` | "Quelles fonctions n'ont jamais été exécutées en 30j de prod/tests ?" |
| `runtime_impact(patch)` | "Cette modif touche un chemin chaud ou tiède ?" |
| `regression_likely(patch)` | "Ce changement modifie-t-il une fonction historiquement liée à des incidents ?" |

Ces tools ne nécessitent **aucun LLM** pour répondre — c'est de la query sur
un graphe enrichi. Latence < 100ms. Coût ~0.

---

## Architecture d'ingestion runtime

Nouveau sub-agent `ah-runtime` (cf. doc 02) :

```
┌────────────────────────┐
│  Sources de traces     │
│  - OTel collector      │
│  - coverage.json       │
│  - eBPF profiles       │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  Normalizer            │
│  (vers schéma commun : │
│   span, fn_id, ts,     │
│   duration, parent)    │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  Graph merger          │
│  (joint sur fn_id      │
│   = file:lineno ou     │
│   FQN si dispo)        │
└──────────┬─────────────┘
           │
           ▼
   Enriched graph store (Kùzu, Neo4j, ou DuckDB)
```

Le **fn_id** est la clé. Doit être stable entre statique (tree-sitter) et
runtime (OTel attribute `code.function`, `code.filepath`, `code.lineno`
standardisés par OTel semantic conventions).

---

## Risques honnêtes

- **Privacy** — traces prod peuvent contenir des données sensibles. Default :
  on n'ingère que les *métadonnées* (fn_id, count, p50/p95), pas les payloads.
- **Bruit** — un repo qui n'a pas d'OTel n'aura pas ce pilier. C'est OK :
  feature *additive*, pas requise.
- **Multi-langage** — schéma OTel semantic conventions code est en
  stabilisation. Surveiller `opentelemetry-specification#code-attributes`.
