# 07 — Eval-first : le harnais d'évaluation pilote tout

## L'affirmation centrale

> **Sans un harnais d'évaluation qui tourne en CI et produit des chiffres
> reproductibles, on ne sait pas si Agent Hub aide.**

Toutes les décisions techniques de ce dossier — sub-agents, world model,
embeddings, verification — sont à valider numériquement, sinon c'est du
vibe-driven engineering.

---

## Ce qu'on mesure (les 4 axes)

### 1. Retrieval quality

> *"Quand l'agent demande du contexte, est-ce que les chunks retournés sont
> les bons ?"*

Métriques :

- **Recall@K** : sur N questions de référence, combien de fois le chunk
  attendu est dans le top-K (K=5, K=10).
- **MRR (Mean Reciprocal Rank)** : à quelle position moyenne ?
- **Citation precision** : sur les sources citées, combien sont
  *effectivement* utilisées pour répondre (réannotation manuelle ou
  LLM-judge).

### 2. Answer quality (downstream)

> *"Les réponses LLM aux questions de code sont-elles correctes ?"*

Métriques :

- **Exact match / F1** sur questions à réponse courte ("dans quel fichier
  est défini X ?").
- **LLM-as-judge** (Claude/GPT scoring un set fixe de Q/A) sur questions
  ouvertes.
- **Faithfulness** : la réponse est-elle uniquement supportée par les
  sources citées ? (Détecteur d'hallucination, soit via Ragas, soit via
  un LLM judge).

### 3. Task success (end-to-end)

> *"L'agent armé d'Agent Hub résout-il plus de tickets ?"*

Le test ultime : **SWE-bench Lite** (et variantes).

- 300 tickets GitHub réels avec fix attendu.
- Mesure : % de patches qui passent les tests cachés.
- Comparaison : agent baseline (sans Agent Hub) vs agent + Agent Hub.

C'est *la* métrique qui compte. Tout le reste est diagnostique.

### 4. Ops / latency / cost

- p50, p95, p99 par tool MCP.
- Tokens consommés par session-type.
- Coût $ ou GPU-secondes par session.
- Index freshness : âge médian des chunks retournés.

---

## Datasets / benchmarks à intégrer

### Benchmarks publics (priorité haute)

| Bench | Quoi | Pourquoi |
|-------|------|----------|
| **SWE-bench Lite** | 300 issues Python réelles + patch attendu + tests cachés | Le gold standard. Mesure task success bout-en-bout. |
| **SWE-bench Verified** | 500 issues human-validated | Plus propre, moins de bruit |
| **RepoBench-R** | Retrieval cross-file | Mesure pure retrieval (axe 1) |
| **RepoBench-C** | Code completion next-line | Pas notre cible directe, mais utile |
| **CodeRAG-Bench** | RAG-spécifique, multi-tasks | Mesure axes 1 et 2 ensemble |
| **LongCodeArena** | Tâches long-context (call graph, etc.) | Stress test sur gros repos |
| **CrossCodeEval** | Multilingue cross-file | Vérifie polyglottisme |

### Datasets internes (priorité haute aussi)

Sur **ce repo agent-hub lui-même** :

- Set de 30-50 questions/réponses curées manuellement
  (`eval/fixtures/agent-hub-internal/questions.jsonl`).
- Set de 10 "tâches" type : "ajoute un tool MCP qui fait X", "trouve
  pourquoi le test Y casse".
- Avantage : on dogfood, on connaît la vérité terrain.

---

## Le harnais : architecture

```
eval/
├── README.md                  # comment lancer
├── benchmarks/                # adaptateurs vers les benchs publics
│   ├── swebench_lite.py
│   ├── repobench.py
│   ├── coderagbench.py
│   └── internal.py            # nos questions sur ce repo
├── harness/
│   ├── runner.py              # boucle : pour chaque case, lance l'agent, collecte
│   ├── agent_adapters/        # comment piloter chaque client
│   │   ├── claude_code.py
│   │   ├── cline.py
│   │   ├── continue_dev.py
│   │   └── raw_mcp.py         # appelle Agent Hub directement, sans agent
│   ├── scorer.py              # métriques (recall, MRR, F1, judge)
│   └── reporter.py            # markdown + CSV + comparaison runs
├── fixtures/
│   ├── agent-hub-internal/    # nos Q/A maison
│   └── repos/                 # gitmodules vers repos benchs
├── results/
│   └── YYYY-MM-DD-HHMM_<run>/ # snapshots horodatés
├── scripts/
│   ├── setup.sh               # télécharge benchs, prépare envs
│   ├── run_baseline.sh        # sans Agent Hub
│   ├── run_with_hub.sh        # avec Agent Hub
│   └── compare.sh             # diff deux runs
└── configs/
    ├── default.yaml
    ├── ci-quick.yaml          # subset pour PRs
    └── nightly.yaml           # full suite
```

---

## Workflow opérationnel

### Pour un dev qui veut tester son changement

```bash
cd eval
./scripts/setup.sh                       # 1x : pull benchs, build envs
./scripts/run_with_hub.sh --config ci-quick.yaml
./scripts/compare.sh results/baseline results/$(ls -t results | head -1)
```

→ Sortie : un rapport markdown avec deltas par métrique.

### Pour la CI

À chaque PR touchant `src/` :

1. Run `ci-quick.yaml` (~5 min, ~50 cases).
2. Bloque si régression > 5% sur n'importe quelle métrique-clé.
3. Commente la PR avec le delta vs main.

### Nightly

1. Run `nightly.yaml` (full SWE-bench Lite + interne).
2. Push résultats vers `eval/results/` dans une branche `eval-history`.
3. Génère un dashboard markdown (`eval/results/DASHBOARD.md`).

---

## Règles pour que ça reste sain

1. **Pas de feature qui se claim "améliore X" sans run avant/après**
   committé dans `eval/results/`.
2. **Le harnais lui-même est testé** (`tests/test_eval_harness.py`).
3. **Les fixtures internes sont versionnées** mais les outputs LLM
   peuvent varier — utiliser des judges avec seed/temperature=0 où
   possible.
4. **Coût visible** : chaque run logue $ et tokens. Pas de "j'ai lancé le
   bench 50 fois" silencieux.

---

## Ce qui rend ce doc différent des autres

Les 6 docs précédents proposent des directions techniques. **Ce doc-ci les
rend testables.** Sans lui, le reste est de l'opinion. Avec lui, c'est une
roadmap d'ingénierie.

**Si une seule chose doit être implémentée en priorité dans ce dossier,
c'est le harnais d'éval. Tout le reste suit.**
