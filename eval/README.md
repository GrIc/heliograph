# Agent Hub — Eval Harness

> Mesurer ce qu'Agent Hub apporte **vraiment**, en conditions réelles, de
> façon reproductible.

Ce dossier implémente le doc stratégique
[`strategy/agent-hub/strategy/07_EVAL_FIRST.md`](https://github.com/GrIc/strategy/tree/main/agent-hub/strategy/07_EVAL_FIRST.md) (private repo).

---

## Objectif

Répondre à une seule question, avec des chiffres :

> **Agent Hub améliore-t-il un agent IA qui code, par rapport au même agent
> sans Agent Hub ?**

Et, secondairement :

- Quelle config de modèles est optimale (cf. `strategy/agent-hub/strategy/05_MODELS_AND_RETRIEVAL.md` dans le repo `GrIc/strategy`) ?
- Une modif du code casse-t-elle une métrique-clé ?
- Quels tools MCP tirent vraiment leur poids ?

---

## TL;DR — comment tester aujourd'hui

> ⚠️ **État** : ce dossier est un **scaffold prêt à l'emploi** (structure,
> scripts, configs). L'implémentation des runners est volontairement laissée
> en stub explicite — on les remplit dans l'ordre des benchmarks qui nous
> intéressent. Voir la section "État d'implémentation" plus bas.

```bash
# 1. Préparer l'environnement (1x)
cd eval
./scripts/setup.sh

# 2. Lancer la baseline (agent SANS Agent Hub)
./scripts/run_baseline.sh

# 3. Démarrer Agent Hub (autre terminal)
docker compose up -d                                # depuis racine repo

# 4. Lancer avec Agent Hub
./scripts/run_with_hub.sh

# 5. Comparer
./scripts/compare.sh
```

Le rapport markdown atterrit dans `results/<timestamp>/REPORT.md`.

---

## Les 4 axes de mesure

| Axe | Métriques | Sources de données |
|-----|-----------|---------------------|
| **Retrieval quality** | Recall@5, Recall@10, MRR, citation precision | RepoBench-R, fixtures internes |
| **Answer quality** | Exact-match, F1, LLM-judge, faithfulness | CodeRAG-Bench, fixtures internes |
| **Task success** | % patches qui passent les tests cachés | SWE-bench Lite, SWE-bench Verified |
| **Ops** | p50/p95 latence, tokens, coût $, fraîcheur index | Mesuré par le runner |

---

## Structure du dossier

```
eval/
├── README.md                 # ce fichier
├── pyproject.toml            # deps Python isolées du repo principal
├── benchmarks/               # adaptateurs vers chaque benchmark public
│   ├── __init__.py
│   ├── _base.py              # interface commune
│   ├── swebench_lite.py
│   ├── repobench_r.py
│   ├── coderagbench.py
│   └── internal.py
├── harness/
│   ├── __init__.py
│   ├── runner.py             # boucle principale
│   ├── scorer.py             # toutes les métriques
│   ├── reporter.py           # markdown + CSV + JSON
│   └── agent_adapters/
│       ├── __init__.py
│       ├── _base.py
│       ├── raw_mcp.py        # appelle directement Agent Hub MCP, sans LLM agent
│       ├── claude_code.py    # pilote Claude Code en mode headless
│       └── aider.py          # pilote Aider (open, scriptable)
├── configs/
│   ├── default.yaml
│   ├── ci-quick.yaml         # ~5 min, subset pour PR
│   ├── nightly.yaml          # tous les benchs
│   └── ablation.yaml         # mêmes cases, différents settings Agent Hub
├── fixtures/
│   ├── README.md
│   ├── agent-hub-internal/   # nos Q/A maison sur ce repo
│   │   ├── questions.jsonl
│   │   └── tasks.jsonl
│   └── repos/                # cloné lazy par setup.sh, gitignored
│       └── .gitkeep
├── scripts/
│   ├── setup.sh              # pull benchs, build envs, télécharge datasets
│   ├── run_baseline.sh
│   ├── run_with_hub.sh
│   ├── run_ablation.sh       # boucle sur configs/ablation.yaml
│   ├── compare.sh
│   └── doctor.sh             # diag rapide (ports, modèles, deps)
└── results/
    ├── .gitkeep
    └── README.md             # convention de nommage
```

---

## Benchmarks intégrés (cibles)

| Bench | Pourquoi | Source | Statut scaffold |
|-------|----------|--------|-----------------|
| **SWE-bench Lite** | Test ultime task success bout-en-bout | `princeton-nlp/SWE-bench_Lite` (HF) | ✅ adaptateur stub |
| **SWE-bench Verified** | Variante propre, human-validated | `princeton-nlp/SWE-bench_Verified` (HF) | ✅ stub partagé |
| **RepoBench-R** | Retrieval cross-file pur (axe 1) | `tianyang/repobench-r` (HF) | ✅ stub |
| **CodeRAG-Bench** | RAG-spécifique multi-tasks | `code-rag-bench/coderagbench` (HF) | ✅ stub |
| **Interne** | Questions curées sur ce repo | `eval/fixtures/agent-hub-internal/` | ✅ format figé |

Le `setup.sh` télécharge tout via `huggingface_hub` (auth optionnelle pour
les datasets ouverts).

---

## Agent adapters

Le harnais pilote 3 cibles, dans cet ordre de priorité :

### 1. `raw_mcp` (le plus simple — par où commencer)

Appelle directement les tools MCP d'Agent Hub via le SDK MCP Python.
**Aucun LLM agent dans la boucle**. Sert à mesurer la qualité brute du
retrieval / des tools, sans bruit lié au comportement d'un agent.

Permet de répondre à : *"Mes tools MCP sont-ils bons en isolation ?"*

### 2. `aider`

Aider est open, scriptable, supporte les serveurs MCP. Lancé en
sous-process headless, pilote son output, score le patch.

Permet de répondre à : *"Un agent open de référence fait-il mieux
avec Agent Hub ?"*

### 3. `claude_code`

Mode headless Claude Code (`claude -p "task" --output-format json`).
Plus cher, plus lent, mais SOTA actuel. Activé en nightly seulement.

Permet de répondre à : *"L'agent SOTA progresse-t-il avec Agent Hub ?"*

---

## Configs : comparer des paramétrages

Le harnais peut **ablater** les composants d'Agent Hub : embedding model,
reranker on/off, taille top-K, sub-agents activés, etc.

Exemple `configs/ablation.yaml` :

```yaml
matrix:
  - name: baseline-no-hub
    hub: off
  - name: hub-default
    hub: on
    embed: text-embedding-3-small
    rerank: ""
  - name: hub-nomic
    hub: on
    embed: nomic-ai/nomic-embed-code
    rerank: ""
  - name: hub-nomic-bge-rerank
    hub: on
    embed: nomic-ai/nomic-embed-code
    rerank: BAAI/bge-reranker-v2-m3
benchmarks:
  - repobench_r
  - internal
budget:
  max_cost_usd: 5
  max_wall_seconds: 1800
```

Lancé via `./scripts/run_ablation.sh`. Sortie : tableau comparatif markdown.

---

## Reporting

Chaque run produit dans `results/YYYY-MM-DD-HHMM_<run_name>/` :

- `REPORT.md` — résumé human-readable, tableaux, deltas vs baseline si dispo.
- `metrics.json` — tous les chiffres bruts.
- `cases/<bench>/<case_id>.json` — par cas : query, output agent, sources
  retournées, score, judge transcript.
- `cost.json` — tokens, $, GPU-secs.
- `env.json` — git SHA, config Agent Hub, modèles, versions.

`./scripts/compare.sh A B` diff deux runs.

---

## Tester sur ce repo lui-même

`eval/fixtures/agent-hub-internal/questions.jsonl` contient des Q/A
sur **ce repo**. Permet de dogfood : on indexe `agent-hub` avec
Agent Hub et on vérifie que ses propres tools répondent correctement.

Exemple de question :

```json
{
  "id": "ah-internal-001",
  "question": "Quels MCP tools sont déclarés dans src/mcp/tools/ ?",
  "expected_answer_contains": ["ask_expert", "find_code", "preview_impact"],
  "expected_sources": [{"path": "src/mcp/tools/", "kind": "dir-listing"}]
}
```

Aucun secret nécessaire si on utilise un modèle local. Idéal pour CI.

---

## État d'implémentation

| Item | Statut |
|------|--------|
| Structure complète | ✅ |
| Configs YAML | ✅ exemples |
| Scripts shell | ✅ runnables, exec stub si runner absent |
| Adapter `raw_mcp` | 🟨 squelette + TODO clair |
| Adapter `aider` | 🟨 squelette |
| Adapter `claude_code` | 🟨 squelette |
| Runner | 🟨 squelette commenté, prêt à remplir |
| Scorer (métriques) | 🟨 implémentation Recall@K et MRR seulement |
| Reporter | 🟨 markdown minimal |
| Adaptateurs benchs | 🟨 stubs avec datasets HF nommés |
| Fixtures internes | ✅ 10 questions seed |
| Tests du harnais | 🟨 stubs |

**Stratégie** : commencer par `raw_mcp` + `internal` fixtures + `repobench_r`.
C'est ce qui donne le ratio info / effort le plus élevé. SWE-bench attend
qu'on ait passé ce premier mur.

---

## Coût attendu

| Run | Durée | Coût LLM estimé (API) | Coût local (GPU) |
|-----|-------|------------------------|-------------------|
| `ci-quick.yaml` | ~5 min | < $0.50 | gratuit (CPU embed + petit LLM) |
| `nightly.yaml` | 30-90 min | $5-30 | 1-2h GPU |
| `swebench_lite` complet | 2-6h | $20-100 | 4-8h GPU |
| `ablation` (4 configs × repobench + internal) | ~30 min | $2-5 | 30-60 min GPU |

Plafond `budget:` dans configs YAML stoppe net si dépassé.

---

## Voir aussi

- `strategy/agent-hub/strategy/07_EVAL_FIRST.md` (in private repo
  [`GrIc/strategy`](https://github.com/GrIc/strategy)) — la doctrine
  derrière ce harnais.
- `strategy/agent-hub/strategy/08_KILLER_DEMOS.md` — les 3 démos cibles à
  automatiser dans le harnais une fois benchs OK.
