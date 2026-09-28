# Evaluation Run 2026-05-01T11:58:20.287731+00:00

## Configuration
- **gold_path**: `data/gold/orkg_sciqa.jsonl`
- **item_count**: `5`
- **judge_enabled**: `False`

## Funnel

| Stage | Pass | Rate |
|-------|------|------|
| Syntax valid       | 0/5 | 0.0% |
| Executable         | 0/5 | 0.0% |
| Execution Match    | 0/5 | 0.0% |
| Algebra Match (corroborative) | 0/5 | 0.0% |

## Self-correction lift

- First-pass syntax valid:  0/5  (0.0%)
- After fix-prompt retry:   0/5  (0.0%)
- Delta:                    +0.0pp (0 queries recovered)

## Per-item summary

| ID | Syntax | Exec | EM | Algebra | Used retry |
|----|--------|------|----|---------|------------|
| AQ0002 | ✗ | ✗ | ✗ | ✗ | ✓ |
| AQ0007 | ✗ | ✗ | ✗ | ✗ | ✓ |
| AQ0015 | ✗ | ✗ | ✗ | ✗ | ✓ |
| AQ0021 | ✗ | ✗ | ✗ | ✗ | ✓ |
| AQ0023 | ✗ | ✗ | ✗ | ✗ | ✓ |
