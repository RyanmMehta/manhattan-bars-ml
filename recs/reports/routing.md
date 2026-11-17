# Run My Night — routing optimality

> **Demo data — synthetic.** Trained/evaluated on randomly generated synthetic venue states (seed 42). Numbers describe the generator's structure, not real nightlife.

Objective (specs §5.12): Σ rank_score at arrival − 10 · walk_km; 4.5 km/h, 60-min dwell, total walk ≤ 30 min, no repeats, each stop must pass hard limits at its arrival time (closing hours, cover, line, distance).

Solver: greedy best-marginal insertion, then local search (segment reversal, swap-in of unused candidates, insertion) until no gain. Oracle: exhaustive search over all ordered 1–3-stop sequences of the candidates.

## 200 random cases (10 venues each, 3 stops)

| solver | within 5% of optimum | mean gap | worst gap | exactly optimal |
|---|---|---|---|---|
| greedy | 93% | 1.36% | 10.57% | 42% |
| greedy + local search (shipped) | 100% | 0.06% | 2.47% | 90% |

Mean solve time (greedy + local search): 1.5 ms. Target: within 5% on ≥ 90% of cases (PRD AC5.3).

Forecast at arrival: the observed state decays towards the crowd model's prediction (half-life 30 min); confidence only decays, so later stops lean less on stale reports. Without a model artifact the planner uses the current state with decaying confidence.
