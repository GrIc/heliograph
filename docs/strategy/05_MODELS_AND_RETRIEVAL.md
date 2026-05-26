# 05 — Modèles & retrieval : la mise à niveau 2026

## Pourquoi ce doc

Le `config.yaml` actuel utilise par défaut :

```yaml
models:
  embed: text-embedding-3-small
  rerank: ""        # désactivé
```

C'est la combinaison **la plus faible** disponible en 2026 pour du code. Coût
sous-optimal, qualité sous-optimale. C'est le levier n°1 d'amélioration "à
config près" — pas de code à écrire, juste swap + benchmark.

---

## Embeddings : pourquoi `text-embedding-3-small` ne tient plus

Ce modèle est :

- **Généraliste** (texte naturel surtout).
- Entraîné avant la vague code-specific 2024-2025.
- Pas optimisé pour les patterns AST, les identifiers, le polyglottisme.

### Alternatives recommandées (à benchmarker sur le harnais)

| Modèle | Dim | Forces | Tradeoffs |
|--------|-----|--------|-----------|
| `voyage-code-3` | 1024 | SOTA pour code en 2025, multilangue, fine-tuné sur 100+ langages | API payante (Voyage), pas auto-hébergeable |
| `nomic-embed-code` | 768 | Open weights, Apache 2.0, optimisé code, marche sur CPU dans une certaine mesure | Légèrement sous voyage-code-3 sur benchmarks |
| `Qwen3-Embedding-8B` | 4096 | Top-tier open weights 2025, multilingue, dim configurable (Matryoshka) | 8B params = GPU 16GB min recommandé |
| `BAAI/bge-m3` | 1024 | Bon généraliste open, déjà cité en exemples `config.yaml` | Pas spécifique code, mais robuste |
| `jina-embeddings-v3` | 1024 | Long context (8k tokens), code-aware, open | Plus jeune, moins benchmarké en France |

**Recommandation par défaut** : `nomic-embed-code` (open, Apache 2.0,
self-hostable via Ollama ou vLLM, qualité proche voyage). Migration triviale
côté config.

---

## Reranker : non-négociable pour la qualité

Sans reranker, le top-K vector search retourne souvent des chunks
syntaxiquement proches mais sémantiquement à côté ("query qui parle de
*auth*" ramène des fonctions contenant le mot "auth" sans rapport).

Un cross-encoder rerank réduit drastiquement ces faux positifs. **Impact
mesuré dans la littérature** : +15 à +30% sur metrics retrieval (MRR,
nDCG@10). Le gain se propage directement sur la qualité des réponses
`expert_ask`.

### Alternatives

| Reranker | Forces | Coût latence (top-K=20) |
|----------|--------|--------------------------|
| `BAAI/bge-reranker-v2-m3` | Open, multilingue, ~600M params | ~50ms CPU, ~10ms GPU |
| `Qwen3-Reranker-4B` | Plus précis, plus lourd | ~200ms GPU |
| `cohere-rerank-3.5` | API hosted, top qualité | ~100ms réseau + payant |
| `jina-reranker-v2-base-multilingual` | Compact, open | ~30ms CPU |

**Recommandation par défaut** : `bge-reranker-v2-m3` activé d'office.
Désactivable pour les profils ultra-low-latency.

---

## GraphRAG : moderniser l'approche

Le repo a un dossier `src/graph/` et un `search_graph` tool, mais la
combinaison RAG + graph est encore au stade "deux silos". L'état de l'art
2025-2026 :

### Microsoft GraphRAG

- Construit des **communautés hiérarchiques** sur le graphe d'entités.
- Génère des **summaries par communauté** avec un LLM.
- Au query time, choisit la granularité (entity / community / global) selon
  la question.
- Particulièrement fort sur les questions "globales" ("comment l'auth est
  architecturée ?") où le RAG plat échoue.

→ Bonne inspiration pour la pyramide L0-L3, mais à appliquer **au graphe**
pas juste aux fichiers.

### LlamaIndex PropertyGraphIndex

- Abstraction propre : nœuds typés + propriétés + edges typés.
- Permet de combiner vector search + Cypher query dans un même appel.
- Backend pluggable : Neo4j, Kùzu, NebulaGraph, ou in-memory.

→ À regarder comme remplaçant de `src/graph/store.py` actuel si on veut
moderniser sans tout réécrire.

### Neo4j GenAI Stack (vector + graph natif)

- Neo4j 5.x intègre les vector indexes nativement.
- Une seule base = embeddings + graph. Pas de double sync à maintenir.
- Cypher pour les traversées, similarity search pour le RAG.

→ Option ambitieuse mais cohérente si on accepte une dépendance Neo4j.

### Kùzu (alternative légère)

- Graph DB embarqué (style SQLite mais pour graphes).
- Cypher subset, très rapide, pas de serveur à gérer.
- Idéal pour un outil dev local.

→ **Recommandé pour Agent Hub** : pas de serveur, embarqué, performances
sérieuses, multi-langage.

---

## Pipeline de retrieval cible

```
Query
  │
  ▼
┌─────────────────────────────────────────┐
│ 1. Query expansion (light LLM, optional)│
│    "auth fail" → "authentication        │
│     failure middleware token expiry"    │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌──────────────┐  ┌──────────────────┐
│ Vector top-K │  │ Graph hops       │
│ (Chroma/     │  │ (Kùzu Cypher :   │
│  LanceDB)    │  │  neighbors of    │
│ K=50         │  │  query entities) │
└──────┬───────┘  └────────┬─────────┘
       │                   │
       └─────────┬─────────┘
                 │ fusion (RRF — Reciprocal Rank Fusion)
                 ▼
       ┌────────────────────┐
       │ Rerank cross-encoder│
       │ (bge-reranker-v2)   │
       │ top-K=8             │
       └─────────┬───────────┘
                 ▼
       ┌────────────────────┐
       │ Grounding check    │
       │ (citation_validator│
       │  existant)         │
       └─────────┬───────────┘
                 ▼
          Answer + sources
```

Étapes 1 et 2 en parallèle. Latence cible bout-en-bout : **< 1.5s** pour
`ask_expert`.

---

## Tableau récapitulatif des changements `config.yaml` proposés

```yaml
models:
  heavy:     mistralai/Magistral-Small-2-2509   # ou claude-sonnet-4-6 si API
  code:      Qwen/Qwen3-Coder-30B-A3B-Instruct  # ou mistralai/Devstral-2
  light:     Qwen/Qwen3-1.5B-Instruct
  reasoning: same as heavy
  embed:     nomic-ai/nomic-embed-code           # ↑↑ critique
  rerank:    BAAI/bge-reranker-v2-m3              # ↑↑ critique, activer
```

Migration : 1 ligne de config + reindex complet (1x). Bénéfice attendu
mesurable au harnais éval : +15 à +30% sur la pertinence des sources
retournées.
