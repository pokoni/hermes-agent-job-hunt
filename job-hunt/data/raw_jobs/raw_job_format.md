# raw_jobs file format

Use Markdown files with YAML front matter.

Why this format:
- Keeps the original source URL and capture date.
- Preserves human-readable context for later review.
- Works well with Hermes, git diffs, and manual editing.
- Avoids forcing early normalization before schema mapping.

## Recommended fields in front matter

```yaml
job_id: unique slug
capture_type: source_snapshot
retrieved_at: 2026-04-22
source_platform: preferred|wantedly|green|doda|linkedin|other
source_url: original job URL
source_title: original page title
company_name: company name
job_title: job title
employment_type: internship|full_time|contract|unknown
location: city/prefecture/remote info
language: ja
status: open|time_bounded|unknown
notes: short note about visibility limits or missing fields
```

## Body format

```md
# <job title>

## Source snapshot
- A short, faithful summary of what was visible on the source page.
- Keep this section close to the source.
- Prefer bullets over prose.

## Visible requirements
- Requirement 1
- Requirement 2

## Visible responsibilities
- Responsibility 1
- Responsibility 2

## Visible stack / keywords
- Python
- PyTorch
- OpenCV

## Missing or hidden information
- Salary hidden behind login
- Application process not visible
```

## Important rule

`raw_jobs/` should contain near-source snapshots, not your final interpreted schema output.
The normalized machine-readable version belongs in `jobs/*.json`.
