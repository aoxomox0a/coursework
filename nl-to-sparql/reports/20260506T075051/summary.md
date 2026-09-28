# Evaluation Run 2026-05-06T08:07:54.918527+00:00

## Configuration
- **gold_path**: `data/gold/orkg_sciqa.jsonl`
- **item_count**: `49`
- **judge_enabled**: `True`

## Funnel

| Stage | Pass | Rate |
|-------|------|------|
| Syntax valid       | 46/49 | 93.9% |
| Executable         | 41/49 | 83.7% |
| Execution Match    | 0/49 | 0.0% |
| Algebra Match (corroborative) | 0/49 | 0.0% |

## Self-correction lift

- First-pass syntax valid:  46/49  (93.9%)
- After fix-prompt retry:   46/49  (93.9%)
- Delta:                    +0.0pp (0 queries recovered)

## Answer quality (LLM judge, 1-5)

- Judged items: 45/49
- Factual:        mean = 1.71
- Completeness:   mean = 1.78
- Fluency:        mean = 4.38
- Hallucination:  mean = 1.27  (5 = no invention)

## Per-item summary

| ID | Syntax | Exec | EM | Algebra | Used retry |
|----|--------|------|----|---------|------------|
| AQ0002 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0007 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0015 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0021 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0023 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0026 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0033 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0064 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0689 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0692 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0696 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0698 | ✓ | ✗ | ✗ | ✗ |  |
| AQ0712 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0713 | ✓ | ✓ | ✗ | ✗ |  |
| AQ0717 | ✓ | ✗ | ✗ | ✗ |  |
| AQ0721 | ✓ | ✓ | ✗ | ✗ |  |
| AQ1029 | ✓ | ✓ | ✗ | ✗ |  |
| AQ1844 | ✓ | ✓ | ✗ | ✗ |  |
| AQ1884 | ✓ | ✗ | ✗ | ✗ |  |
| AQ1886 | ✓ | ✓ | ✗ | ✗ |  |
| AQ1891 | ✓ | ✗ | ✗ | ✗ |  |
| AQ1945 | ✓ | ✓ | ✗ | ✗ |  |
| AQ1949 | ✓ | ✓ | ✗ | ✗ |  |
| AQ1953 | ✓ | ✓ | ✗ | ✗ |  |
| AQ1956 | ✓ | ✓ | ✗ | ✗ |  |
| AQ1964 | ✓ | ✓ | ✗ | ✗ |  |
| AQ1967 | ✓ | ✓ | ✗ | ✗ |  |
| AQ1971 | ✓ | ✓ | ✗ | ✗ |  |
| AQ2008 | ✓ | ✓ | ✗ | ✗ |  |
| AQ2455 | ✓ | ✓ | ✗ | ✗ |  |
| AQ2462 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0003 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0017 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0026 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0027 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0031 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0032 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0038 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0043 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0057 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0058 | ✗ | ✗ | ✗ | ✗ | ✓ |
| HQ0068 | ✗ | ✗ | ✗ | ✗ | ✓ |
| HQ0078 | ✗ | ✗ | ✗ | ✗ | ✓ |
| HQ0081 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0084 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0085 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0091 | ✓ | ✓ | ✗ | ✗ |  |
| HQ0097 | ✓ | ✗ | ✗ | ✗ |  |
| HQ0099 | ✓ | ✓ | ✗ | ✗ |  |
