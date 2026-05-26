# Agent Hub — Stratégie Technique (v3, dev-tool pur)

> **Reset de cadrage** : ce dossier remplace toute lecture stratégique antérieure orientée
> business / GTM / regulated-industries. Agent Hub est ici considéré uniquement comme
> **un outil pour aider les développeurs à coder mieux et plus vite avec des agents IA**.
> Pas de pitch, pas de pricing, pas de personas commerciaux. Que de la technique utile.

---

## Pourquoi ce dossier existe

L'historique du repo (`docs/roadmap/STRATEGY.md`, `AGENT_HUB_KEY_FEATURES_V2.md`,
`docs/PITCH.md`) cadre Agent Hub comme un produit commercial avec quatre piliers
("trust substrate", verification formelle, regulated industries, etc.).

Cette posture entraîne deux dérives techniques :

1. **Sur-promesse sur Phase 6-7** (SMT verification, world model) — gourmand en
   R&D pour un usage dev quotidien faible.
2. **Sous-investissement dans les fondations** qui font *réellement* qu'un dev
   accepte de garder l'outil branché : qualité du retrieval, fraîcheur de
   l'index, latence, évaluation objective.

Ce dossier recadre les priorités sur ce qui **change la vie d'un dev** qui code
avec Claude Code / Cursor / Cline / Continue. Pas plus.

---

## Principe directeur unique

> **Tout ce qui n'améliore pas mesurablement la session de codage du dev,
> mesuré par un harnais d'évaluation reproductible, dégage du backlog.**

Conséquences :

- Pas de tool MCP sans test golden + delta mesuré sur eval harness.
- Pas de feature "stratégique" sans baseline numérique avant/après.
- Pas de phase planifiée à 9+ semaines sans MVP testable à 2 semaines.

---

## Ordre de lecture

| # | Document | Sujet | Verdict |
|---|----------|-------|---------|
| 01 | [`01_THESIS.md`](01_THESIS.md) | Le seul problème qu'on résout vraiment | Recadrage |
| 02 | [`02_ARCHITECTURE_SUBAGENTS.md`](02_ARCHITECTURE_SUBAGENTS.md) | Monolithe 29-tools → swarm MCP composable | Refactor |
| 03 | [`03_CODE_WORLD_MODEL.md`](03_CODE_WORLD_MODEL.md) | Graphe statique + traces runtime | Nouveau pilier |
| 04 | [`04_INCREMENTAL_INDEXING.md`](04_INCREMENTAL_INDEXING.md) | Merkle + content-addressed chunks | Killer ops |
| 05 | [`05_MODELS_AND_RETRIEVAL.md`](05_MODELS_AND_RETRIEVAL.md) | Embeddings 2026, rerankers, GraphRAG moderne | Mise à niveau |
| 06 | [`06_VERIFICATION_REALISTIC.md`](06_VERIFICATION_REALISTIC.md) | Typed effects au lieu de SMT général | Re-scope Phase 6 |
| 07 | [`07_EVAL_FIRST.md`](07_EVAL_FIRST.md) | Le harnais d'éval pilote tout le reste | **Le doc le plus important** |
| 08 | [`08_KILLER_DEMOS.md`](08_KILLER_DEMOS.md) | 3 flows qui doivent juste marcher | Définition de "done" |

---

## Ce qu'on NE fait plus

| Abandonné | Raison |
|-----------|--------|
| Pitch business, persona "CTO regulated", pricing tiers | Hors scope outil dev |
| "Hallucination rate <2% publié par install" comme métrique marketing | Garde la mesure, vire le marketing |
| Roadmap calée sur trimestre commercial | Cadence = quand l'éval valide |
| Phase 7 "adaptive intelligence" multi-customer | Pas de flywheel cross-user pour un outil local |
| 29 tools MCP comme argument | Compte les tools qui *bougent l'éval*, vire les autres |

---

## Ce qu'on garde de l'historique

- **Documentation pyramide L0→L3** : bonne idée, exécution correcte.
- **Tree-sitter graph statique** : socle solide.
- **Citations systématiques** dans les réponses MCP : non négociable.
- **MCP-first** : bon protocole, bon timing.
- **Self-hostable, OpenAI-compatible** : utile pour dev offline / modèles locaux.
