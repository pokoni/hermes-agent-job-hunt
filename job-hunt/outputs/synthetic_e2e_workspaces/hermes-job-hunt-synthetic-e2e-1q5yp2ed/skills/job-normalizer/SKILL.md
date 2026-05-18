---
name: job-normalizer
title: Japan Job Posting Normalizer
description: Normalize raw Japanese job descriptions into schema-compliant JSON under job-hunt/data/jobs/ using the stable project structure.
version: 1.1.0
author: OpenAI
metadata:
  tags:
    - japan-jobs
    - normalization
    - schema
    - recruitment
  requires_toolsets:
    - files
---

# Japan Job Posting Normalizer

Convert raw job descriptions in `data/raw_jobs/` into standardized JSON files in `data/jobs/`.

## When To Use

Use this skill when:
- a new job description has been added to `data/raw_jobs/`
- the user wants a hiring page converted into the shared job posting schema
- a previously normalized job JSON is missing fields or needs cleanup
- multiple job postings need consistent field naming and structure

Do **not** use this skill for resume tailoring, application drafting, or fit scoring.

## Stable Workspace Assumptions

This skill assumes the current working directory is `job-hunt/` and the project structure is fixed:

- `data/raw_jobs/` stores raw source material
- `data/jobs/` stores normalized JSON files
- `data/job_posting.schema.json` is the canonical schema (NOT `schemas/job_posting.schema.json`)
- `data/candidate_profile.json` is **not** used by this skill except for optional compatibility checks

Do not invent new directories.

## Inputs

Primary input sources:
- one raw job file under `data/raw_jobs/`
- optionally, a live job page URL supplied by the user
- optionally, an existing normalized JSON in `data/jobs/` that needs revision

Preferred raw file format:
- Markdown with YAML front matter
- source snapshot blocks
- visible requirements and responsibilities separated from missing information

## Output Contract

Write exactly one normalized JSON file per job posting to `data/jobs/`.

Filename convention:
- raw: `data/raw_jobs/01_company_role_year.md`
- normalized: `data/jobs/01_company_role_year.json`

The output must be valid JSON and pass `jsonschema.validate()` against `data/job_posting.schema.json`.

## Required Schema Fields (in the actual schema)

The schema uses field names that differ from the skill's earlier version. The canonical schema at `data/job_posting.schema.json` has these **required** properties:

- `source` (string) — platform name, e.g. "Wantedly", "Green", "doda"
- `url` (string, uri format) — direct URL to the posting
- `source_job_id` (string or null) — the platform's job/project ID
- `company_name` (string)
- `job_title` (string)
- `location` (object with required keys: `country`, `city`, `remote_policy`)
- `employment_type` (enum: internship, new_grad, full_time, contract, part_time, other)
- `language_requirement` (object with required keys: `japanese_level`, `english_level`; both are non-nullable strings, plus optional `notes`)
- `required_skills` (array of strings)
- `preferred_skills` (array of strings)
- `responsibilities` (array of strings)
- `application_method` (enum: platform_apply, email, external_ats, referral, other)
- `raw_description` (string)

**Additional (nullable) properties:**
- `company_profile`, `department`, `must_have_years_experience`, `compensation` (object), `visa_support` (object), `application_deadline` (date), `screening_process` (array), `keywords_normalized` (array), `fit_hints` (object), `fetched_at` (date-time)

**Critical constraint:** The schema uses `"additionalProperties": false`. You **cannot** add custom fields like `normalization_notes`, `job_id`, `status`, `language`, etc. Embed uncertainty notes inside `raw_description` instead.

## Normalization Rules

### 1. Preserve facts
- Never infer unavailable salaries, visa support, or hidden requirements.
- Never rewrite a preferred skill into a required skill.
- Never claim that a position is open indefinitely if the posting is date-bounded.
- When a language requirement is not mentioned, **do not** fabricate it. For `english_level` (which is a required non-nullable string), use `"not_specified (source does not mention English requirement)"` — do NOT use `"none"` or `null`.

### 2. Separate visible facts from missing information
- Only place directly supported facts in structured fields.
- Since `normalization_notes` is NOT a field in the schema (schema has `additionalProperties: false`), embed uncertainty and ambiguity into `raw_description` as a structured summary that notes what's missing.

### 3. Normalize lists cleanly
Use arrays for:
- `required_skills`
- `preferred_skills`
- `responsibilities`
- `keywords_normalized`

Prefer short atomic entries rather than paragraph-sized bullets.

### 4. Preserve Japanese-market semantics
Keep distinctions such as:
- 必須 / MUST -> `required_skills`
- 歓迎 / NICE TO HAVE / Better -> `preferred_skills`
- 業務内容 / 仕事内容 -> `responsibilities`
- 勤務地 / リモート / 出社条件 -> populate `location` object fields

### 5. Keep source traceability
Always keep enough traceability to reconstruct where the JSON came from:
- source URL → `url`
- source title → can be embedded in `raw_description`
- retrieval date → `fetched_at` (use ISO 8601 date-time format, e.g. "2026-04-22T00:00:00Z")
- notes for hidden or inferred omissions → include in `raw_description`

## Procedure

### Step 1: Read the raw job file
Open the selected file under `data/raw_jobs/`.
Extract:
- company name
- job title
- source platform
- source URL
- visible role summary
- visible requirements
- visible preferred skills
- visible responsibilities
- visible work conditions
- anything explicitly missing or hidden

### Step 2: Map content into the schema
Translate the extracted content into the schema fields.

**Key mapping rules:**
- `source_platform` (frontmatter) → `source` (string)
- `source_url` (frontmatter) → `url` (string)
- Extract the platform's project/job ID from the URL → `source_job_id` (string or null)
- `location` (frontmatter string like "Tokyo") → `location` object: `{country: "Japan", city: "...", remote_policy: "unknown"|"onsite"|"hybrid"|"remote"}`
- `language_requirement`: map JLPT mentions from requirements → `japanese_level`. For `english_level`, ONLY set a value if the source explicitly mentions English, otherwise use `"not_specified (source does not mention English requirement)"`
- `employment_type` must be one of the enum values

### Step 3: Fill missing fields safely
If the source does not show a field:
- use `null` for nullable fields (company_profile, department, compensation, visa_support, etc.)
- use `[]` for array fields that have no content (keywords_normalized)
- For `english_level` (non-nullable required string): use a descriptive fallback, never null
- Mention the missing context inside `raw_description`

### Step 4: Write the normalized JSON
Save the output to the paired filename under `data/jobs/`.

### Step 5: Self-check before finishing
Verify:
- valid JSON syntax
- passes `jsonschema.validate()` against `data/job_posting.schema.json`
- no fabricated salary, visa, or language claims
- `required_skills` vs `preferred_skills` distinction preserved
- `english_level` is a non-null string (schema constraint)
- output path matches the fixed project structure

## Recommended JSON Shape

The schema at `data/job_posting.schema.json` defines the exact shape, but conceptually:

```json
{
  "source": "Wantedly",
  "source_job_id": "2407303",
  "url": "https://www.wantedly.com/projects/2407303",
  "company_name": "株式会社AVILEN",
  "company_profile": null,
  "job_title": "半導体製造現場で画像処理AIを0から作る｜実務直結のAIエンジニア体験",
  "department": null,
  "location": {
    "country": "Japan",
    "city": "Tokyo",
    "remote_policy": "unknown"
  },
  "employment_type": "internship",
  "language_requirement": {
    "japanese_level": "ビジネスレベル (JLPT N1相当以上)",
    "english_level": "not_specified (source does not mention English requirement)",
    "notes": null
  },
  "must_have_years_experience": null,
  "required_skills": [
    "基本的な統計学・データ分析の知識",
    "プログラミング経験",
    "週20時間以上稼働可能"
  ],
  "preferred_skills": [
    "プログラミングの実務経験",
    "AIに関する深い知識（研究、資格、個人開発など）"
  ],
  "responsibilities": [
    "現場ヒアリングと要件整理のサポート",
    "製造工程に使う画像処理アルゴリズムの構築",
    "精度検証などAI実装に向けた技術サポート"
  ],
  "compensation": null,
  "visa_support": null,
  "application_method": "platform_apply",
  "application_deadline": null,
  "screening_process": null,
  "keywords_normalized": [
    "半導体",
    "画像処理",
    "AI",
    "インターン"
  ],
  "fit_hints": null,
  "raw_description": "Summary of visible source content including salary/tech stack gaps.",
  "fetched_at": "2026-04-22T00:00:00Z"
}
```

## Pitfalls

Common mistakes to avoid:
- merging required and preferred skills into one list
- treating a company profile page as a job description page
- filling hidden compensation fields from memory or unrelated pages
- writing outputs outside `data/jobs/`
- **setting `english_level` to `null` or `"none"`** — the schema requires a non-null string. When English isn't mentioned, use `"not_specified (...)"` rather than fabricating an absence
- **adding custom fields like `normalization_notes`, `status`, `job_id`, `language`** — the schema uses `additionalProperties: false`, so these will fail validation
- **using the wrong schema path** — the schema is at `data/job_posting.schema.json`, not `schemas/job_posting.schema.json`
- **using `language_requirements` as an array** — the schema defines `language_requirement` as an object with `japanese_level` and `english_level` strings
- **treating `location` as a flat string** — it must be an object with `country`, `city`, and `remote_policy`
- **setting `application_method` to arbitrary strings** — it's an enum limited to: `platform_apply`, `email`, `external_ats`, `referral`, `other`

## Verification

The task is complete only if all of the following are true:
- the raw job has a matching JSON in `data/jobs/`
- the JSON is syntactically valid
- the JSON passes `jsonschema.validate()` against `data/job_posting.schema.json`
- every nontrivial claim is traceable to the raw source or explicitly noted in `raw_description`
- no new project directories were introduced
- `english_level` is a non-null string (fabricating "none" counts as hallucination)
- no extra fields beyond the schema's defined properties
