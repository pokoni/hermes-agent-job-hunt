# Ranking Quality Refinement Stage

## Purpose

The real public careers adapter can now extract many true research/job themes. The next issue is ranking quality.

This stage improves `run_batch_job_pipeline.py` so that concrete themes rank higher and generic skill fragments are held.

## Main changes

Concrete topics receive boosts, especially:

```text
生成モデル
Alignment
AIエージェント
LLM
プロンプト最適化
検索基盤
データリネージ
コンピュテーショナルイメージング
コンピュータビジョン
```

Generic fragments are penalized or held, for example:

```text
機械学習
深層学習・AI技術に対する関心
人工知能・機械学習、データサイエンス
Pythonによる機械学習モデル実装
```

## Updated files

```text
scripts/run_batch_job_pipeline.py
tests/test_ranking_quality_refinement.py
docs/ranking_quality_refinement_stage.md
docs/project_stage_after_ranking_quality_refinement.md
```

## Test

```bash
../.venv/bin/python -m pytest tests/test_ranking_quality_refinement.py -q
```

## Real flow

After extracting public careers jobs and deduplication, run:

```bash
../.venv/bin/python \
  scripts/run_batch_job_pipeline.py \
  --workspace . \
  --dedup-report outputs/logs/job_deduplication_report.json \
  --sources data/job_sources.json \
  --candidate-profile data/candidate_profile.json
```

Then inspect:

```bash
../.venv/bin/python - <<'PY'
import json
from pathlib import Path

d = json.loads(Path("outputs/logs/batch_job_pipeline_report.json").read_text(encoding="utf-8"))
for row in d.get("ranked_candidates", [])[:20]:
    print(row["fit_score"], row["ranking_decision"], row.get("topic_quality_label"), row.get("title"))
PY
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
