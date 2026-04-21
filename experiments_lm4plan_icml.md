# Experiments — LM4Plan (ICML Workshop)

## Setup

- **Scenario space**: 9 polygon sets (3 easy / 3 medium / 3 hard) × 5 origins × 5 destinations = 225 scenarios total.
- **Used in this study**: 3 polygon sets (1 easy + 1 medium + 1 hard) × 25 (origin, destination) pairs = **75 scenarios**.
- **DB reset** (`drop_all` + `create_all`) between models so each model has its own clean RAG store.
- **No VLM evaluation for now.** Coach/RAG records are seeded with geometric evaluation and (optional) human review only.

### Design (Option A — shared scenarios, held-out preferences)

Retrieval filters require exact match on (polygon set, origin, destination), so warmup and ablation must share scenarios. We hold out the **preference text**, not the geometry: warmup uses a generic preference; ablation uses 3 specific preferences that are each tied to a quantitative metric.

## Warmup (per model)

- **75 scenarios × 2 conditions (coach, no-coach) = 150 runs per model.**
- Preference for every warmup run: `"Propose the best flight plan from origin to destination avoiding hazardous polygons."`
- Seeds the DB with one coach record and one no-coach record for every (polygon, origin, destination) triple.

## Test preferences (for ablation)

Each preference maps to a single quantitative metric.


| #   | Preference text                                                           | Metric                     | Direction |
| --- | ------------------------------------------------------------------------- | -------------------------- | --------- |
| 1   | "Minimize total flight distance."                                         | `distance_km`              | lower     |
| 2   | "Minimize the number of waypoints — keep the path as simple as possible." | `num_waypoints`            | lower     |
| 3   | "Maximize clearance from hazardous polygons."                             | `min_polygon_clearance_km` | higher    |


## Ablation (per model)

- **75 scenarios × 3 preferences × 3 conditions = 675 runs per model.**

### Conditions


| Condition | Flags           | Description                         |
| --------- | --------------- | ----------------------------------- |
| baseline  | (none)          | Prompt-only, no retrieval.          |
| rag       | `--rag 3`       | Retrieve 3 no-coach warmup records. |
| rag_coach | `--rag_coach 3` | Retrieve 3 coach warmup records.    |


Fix **N = 3**. Optional single-figure sweep N ∈ {1, 3, 5}.

## Planners

- Reasoning, closed × 2: `o4-mini`, `o3-mini`.
- Non-reasoning, closed × 2: `gpt-4.1`, `claude-haiku-4-5`.
- Reasoning, open × 1: `deepseek-r1`.

## Metrics

- **Validity rate** (primary).
- **Preference-specific metric** (the one tied to the preference in use): `distance_km`, `num_waypoints`, or `min_polygon_clearance_km`.

## Claims

1. **RAG helps**: `rag` and `rag_coach` improve validity over `baseline`, paired across scenarios.
2. **Coach-augmented RAG helps more than problem-only RAG**, especially on preference-heavy prompts.
3. **Preference is actually honored**: the metric tied to the active preference improves under `rag_coach` relative to `baseline` for that preference only (not the other two).
4. **Gain is larger for non-reasoning than reasoning models**.

## Figures

1. **Main table**: model × {baseline, rag, rag_coach} × {validity, preference-specific metric}.
2. **Preference-honored plot**: for each test preference, the metric it targets, broken out by condition.
3. **Retrieval depth plot** (optional): validity vs N ∈ {1, 3, 5}, one panel per model.

## Totals

- Per model: 150 warmup + 675 ablation = **825 runs**.
- Across 5 models: **4125 runs**.

## Headline

Coach-augmented retrieval improves validity and preference-honoring across models, with the largest effect on non-reasoning planners and on preferences whose target metric is hard to satisfy without examples.