# Evidence

Raw reviewer, checks and worker output for the cases the README discusses. Local paths are replaced by `<workspace>`/`<path>`.

- `review-v1/`: the first review prompt. BENCH-03, -08 and -10 are the three false rejections, and BENCH-14 is the rule violation the reviewer approved. `branch.diff` is the worker's unmerged branch against `main`.
- `review-v2/BENCH-10/`: with the reviewer fixes. A different HIGH finding was fixed, then the change was approved and merged while still accepting `Decimal("1.500")`. The merged module is in `merged-installments.py`.
