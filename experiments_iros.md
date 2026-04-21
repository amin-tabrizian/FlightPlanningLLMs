# Experiments — IROS

## Setup

### Scenario grid
- 9 polygon sets, grouped 3 easy / 3 medium / 3 hard.
- 5 origins, 5 destinations → 5 × 5 = 25 (origin, destination) pairs per polygon set.
- Total scenarios: 9 × 25 = **225**.
- Warmup consumes 9 scenarios (1 per polygon set); ablation runs on the remaining **216**.

### Warmup (per model)
- 9 runs: one per polygon set.
- Per difficulty (3 sets): 2 coach + 1 no-coach → **6 coach + 3 no-coach per model**.
- DB reset (`drop_all` + `create_all`) before each model so warmups do not cross-contaminate.
- Warmup assignments to pin down before running:
  - Which 2 polygon sets per difficulty get coach vs the 1 that gets no-coach (prefer the geometrically trickier sets for coach).
  - The (origin, destination) pair per warmup row — spread across the 5×5 grid rather than reusing the diagonal.
  - The 9 paired preferences — one per category from the preference pool.

### Models
- **Planner (5 total)**
  - Reasoning, closed × 3: `o4-mini`, `claude-sonnet-4-6` (extended thinking), `gemini-2.5-pro` (thinking).
  - Non-reasoning × 1: `gpt-4.1`.
  - Reasoning, open × 1: `deepseek-r1` (or `qwen3-32b` / `qwq-32b`).
- **Coach VLM (fixed)**: `gemini-2.5-pro` or `claude-sonnet-4-6`. Only the planner varies across conditions.

## Conditions

| Condition      | Flags               | Purpose                                  |
|----------------|---------------------|------------------------------------------|
| baseline       | (none)              | Prompt-only, no retrieval.               |
| rag            | `--rag N`           | Problem-only retrieval.                  |
| rag_coach      | `--rag_coach N`     | Coach-augmented retrieval.               |
| random-rag     | random top-N        | Control: isolates similarity retrieval.  |
| oracle-rag     | nearest valid       | Upper bound on RAG.                      |
| geom-only coach| no VLM text         | Isolates the VLM's contribution.         |

Retrieval depth sweep: **N ∈ {1, 3, 5}** for `rag` and `rag_coach`. `filter_by_validity` sweep: on vs off.

## Metrics logged per run (already in `runs.csv`)

- Validity (binary) + component failures: endpoint match, flyzone containment, polygon intersection.
- `planner_inference_time_s`.
- `vlm_aligned`, `vlm_evaluation`, `vlm_reasoning`.
- Distance: total path length (km), ratio to great-circle distance (derived offline).
- Waypoint count, #waypoints outside flyzone, #violated polygons.
- Token / $ cost (prompt + completion tokens × per-model price, logged offline).
- Retrieval metadata: top-k neighbor IDs, embedding distances.

## Claims and analyses

**Claim A — RAG beats baseline.**
- Conditions: `baseline`, `rag N=3`, `rag_coach N=3`.
- Metric: validity rate (primary), distance ratio (secondary).
- Test: paired McNemar on validity (same scenario across conditions).

**Claim B — Coach-augmented retrieval beats problem-only retrieval.**
- `rag` vs `rag_coach` at matched N.
- Break down by preference category; expect larger gain on vague / natural-language preferences.

**Claim C — Retrieval depth saturates.**
- Line plot of validity vs N ∈ {1, 3, 5}, per model, per rag variant.

**Claim D — Similarity retrieval is load-bearing.**
- Compare `rag` vs `random-rag` at matched N. Delta = the contribution of embedding similarity (as opposed to just "more examples").

**Claim E — VLM coach signal is load-bearing.**
- Compare `rag_coach` vs `geom-only coach`. Delta = the contribution of the VLM's preference-alignment judgment above rule-based geometry alone.

**Claim F — Reasoning vs non-reasoning sensitivity.**
- Δ(rag_coach − baseline) per model, grouped by reasoning / non-reasoning. Expect non-reasoning models to benefit more from RAG.

## Additional analyses

- **Error taxonomy**: which geometries dominate failures (narrow corridors, overlapping polygons, origin-adjacent hazards).
- **Preference-category sensitivity**: alignment rate per preference category × condition.
- **Retrieval quality vs downstream quality**: correlation between top-1 embedding similarity and validity.
- **Failure carry-over**: when the retrieved example is invalid, does the planner inherit the failure? Motivates `filter_by_validity`.
- **Cost-quality frontier**: validity rate vs $ per run, across models and conditions.

## Tables and figures

1. **Main results table**: model × {baseline, rag, rag_coach} × {validity, distance ratio, alignment, cost}.
2. **Retrieval depth plot**: validity vs N per model.
3. **Preference heatmap**: alignment rate by preference category × condition.
4. **Cost-quality scatter**: validity vs $ per run.
5. **Paired delta plot**: per-scenario Δvalidity (baseline → rag_coach), sorted.
6. **Control comparison**: bar chart of `baseline`, `random-rag`, `rag`, `oracle-rag`, `rag_coach`, `geom-only coach`.
7. **Qualitative case studies**: 2-3 scenarios where baseline fails and `rag_coach` succeeds, with retrieved example and VLM review shown.

## Headline narrative

RAG with coach-augmented retrieval improves validity uniformly, but its effect concentrates on non-reasoning models and on preference-heavy prompts — RAG substitutes for reasoning capacity and for prompt specificity. The VLM coach signal contributes measurably above rule-based geometry, and similarity retrieval contributes measurably above random retrieval.
