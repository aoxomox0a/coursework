# Evaluation Run 2026-05-04T09:00:26.660138+00:00

## Configuration
- **gold_path**: `data/gold/orkg_sciqa.jsonl`
- **item_count**: `5`
- **judge_enabled**: `False`

## Funnel

| Stage | Pass | Rate |
|-------|------|------|
| Syntax valid       | 5/5 | 100.0% |
| Executable         | 5/5 | 100.0% |
| Execution Match    | 0/5 | 0.0% |
| Algebra Match (corroborative) | 0/5 | 0.0% |

## Self-correction lift

- First-pass syntax valid:  5/5  (100.0%)
- After fix-prompt retry:   5/5  (100.0%)
- Delta:                    +0.0pp (0 queries recovered)

## Per-item summary

| ID | Syntax | Exec | EM | Algebra | Used retry |
|----|--------|------|----|---------|------------|
| AQ0002 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0007 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0015 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0021 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0023 | ✓ | ✓ | ✗ | ✗ |  |
