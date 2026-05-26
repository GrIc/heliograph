# 02 — Architecture : du monolithe 29 tools vers un swarm MCP

## Le problème actuel

`src/mcp/tools/` contient ~20 tools sous un seul serveur MCP. Chaque tool est
indépendant côté API, mais ils partagent :

- Un seul process Python.
- Un seul cycle de vie de l'index Chroma.
- Une seule config de modèles.
- Une seule logique de logging / observabilité.

Conséquences :

- **Tests fragiles** — un tool casse l'init, tous tombent.
- **Évolution lente** — ajouter un nouveau pilier (ex : runtime traces) =
  toucher le monolithe.
- **Modèles mal alloués** — `find_code` (peu critique) tape sur le même budget
  que `expert_ask` (cher), pas de scheduling intelligent.
- **Pas de réutilisation cross-projet** — un autre repo qui voudrait juste
  "le graphe d'appel MCP" doit tout embarquer.

---

## Pattern cible : sub-agents MCP spécialisés

Inspiré des SDK agents 2025-2026 (Claude Agent SDK, OpenAI Swarm, Google ADK).
**Pas une révolution** — juste une décomposition propre par responsabilité.

```
┌──────────────────────────────────────────────────────────┐
│  Agent client (Claude Code, Cursor, Cline...)            │
└──────────────────────────┬───────────────────────────────┘
                           │ MCP
       ┌───────────────────┼───────────────────┐
       │                   │                   │
┌──────▼──────┐   ┌────────▼────────┐  ┌───────▼────────┐
│  retrieval  │   │  graph          │  │  history       │
│  (RAG)      │   │  (callers,      │  │  (changelog,   │
│             │   │   callees,      │  │   why-exists)  │
│             │   │   impact)       │  │                │
└─────┬───────┘   └────────┬────────┘  └────────┬───────┘
      │                    │                    │
      └────────────┬───────┴───────┬────────────┘
                   │               │
            ┌──────▼────┐   ┌──────▼────────┐
            │ indexer   │   │ runtime-trace │
            │ (Merkle,  │   │ (eBPF/OTel    │
            │ embed)    │   │  ingest)      │
            └───────────┘   └───────────────┘
```

Chaque case = **un binaire MCP autonome** parlant le protocole standard.
L'agent client compose ; il n'a pas besoin de connaître l'arrangement
interne.

---

## Découpage proposé (5 sub-agents)

| Sub-agent | Responsabilité unique | Tools exposés (exemples) |
|-----------|------------------------|--------------------------|
| `ah-retrieval` | Vector search + rerank + grounding | `ask_expert`, `find_code`, `find_similar`, `locate_feature` |
| `ah-graph` | Tout ce qui dérive du graphe AST | `get_callers`, `get_callees`, `get_module_dependencies`, `preview_impact`, `find_hub_modules` |
| `ah-history` | Git + temporal | `why_does_this_exist`, `what_changed_here`, `blame_plus`, `recent_changes`, `explain_change` |
| `ah-docs` | Pyramide L0→L3, wiki | `read_wiki_page`, `list_wiki_pages`, `explain_module` |
| `ah-indexer` | Pipeline d'ingestion (background) | Pas de tools MCP utilisateur ; expose `ping`/`status` |

Optionnel plus tard : `ah-runtime` (cf. doc 03), `ah-verify` (cf. doc 06).

---

## Bénéfices concrets

1. **Tests par sub-agent** — `pytest tests/retrieval/` ne charge pas le graphe.
   CI rapide, isolation des régressions.
2. **Choix de modèle par sub-agent** — `ah-retrieval` peut utiliser
   `voyage-code-3` + un petit rerank ; `ah-history` peut tourner sur du
   `Qwen3-1.5B` ; `ah-graph` n'a souvent pas besoin de LLM du tout.
3. **Déploiement granulaire** — sur petite machine, ne lance que `ah-retrieval`
   + `ah-graph`. Sur grosse machine, ajoute le reste.
4. **Adoption progressive** — un user peut tester juste `ah-graph` sans
   embarquer la pipeline Chroma complète.
5. **Compose avec d'autres MCP servers** — Z3, Serena, Context7, etc. au même
   niveau, sans hiérarchie cachée.

---

## Plan de migration (sans casser l'existant)

1. **Phase A (1 sem)** : extraire `src/mcp/tools/` en modules autonomes
   importables (`from agent_hub.tools.retrieval import ask_expert`). Pas de
   séparation de process encore.
2. **Phase B (1 sem)** : créer 5 entrypoints `src/mcp/servers/{name}.py` qui
   exposent un sous-ensemble de tools chacun. Le serveur monolithique actuel
   devient un wrapper qui re-exporte tous les sub-agents (compat).
3. **Phase C (2 sem)** : docker-compose option avec 5 containers + un proxy MCP
   (mcp-aggregator) qui ré-exporte tout sur un seul endpoint pour les clients
   qui veulent rester simples.
4. **Phase D** : déprécier le monolithe quand le harnais d'éval (doc 07) montre
   parité ou mieux.

À aucun moment l'utilisateur final n'est cassé — `localhost:8080/mcp/sse`
continue de marcher.

---

## Ce qu'on NE fait pas

- Pas de bus de messages custom. MCP suffit.
- Pas d'orchestrateur LLM interne ("meta-agent qui route"). C'est le rôle du
  client (Claude Code, Cursor). On n'ajoute pas une couche.
- Pas de "agent autonome qui décide quoi indexer". L'indexer reste
  déterministe et configurable.
