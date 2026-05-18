# Job Normalization Prompt Asset

Use this prompt asset when converting a raw job description under `data/raw_jobs/` into standardized JSON under `data/jobs/`.

## Goal

Produce a schema-compliant job JSON without inventing facts.

## Instructions

1. Read the raw job description carefully.
2. Extract only facts that are visible in the source.
3. Separate required skills from preferred skills.
4. Keep responsibilities as short atomic list items.
5. Preserve Japanese-market distinctions such as 必須 / 歓迎 / 業務内容.
6. If a field is unavailable, use a schema-safe empty value and explain the omission in `normalization_notes`.
7. Output valid JSON only when writing the normalized file.

## Do Not

- Do not fabricate salary, visa support, or hidden requirements.
- Do not merge required and preferred skills.
- Do not output prose where the schema expects arrays.
- Do not write normalized files outside `data/jobs/`.
