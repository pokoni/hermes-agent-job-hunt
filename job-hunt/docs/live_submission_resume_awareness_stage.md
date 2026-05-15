# Live Submission Adapter Resume Awareness Stage

This stage does not change the frozen pipeline. It strengthens the existing `live-submission-adapter` so it consumes the resume-aware output of `submission-review-gate`.

## Why this stage exists

After `submission-review-gate` starts linking resume/CV artifacts in:

```text
outputs/logs/<job_basename>_submission_decision.json
```

the live adapter should use those references and stop reporting stale blockers such as:

- resume/CV files missing
- resume_version is null
- outputs/resumes/ directory does not exist

when the actual resume artifacts exist.

## Frozen pipeline remains unchanged

```text
job-normalizer
→ job-fit-scorer
→ resume-tailor
→ jp-application-writer
→ application-tracker
→ browser-apply-assistant
→ submission-review-gate
→ live-submission-adapter
```

## Required behavior

`live-submission-adapter` must:

1. read `outputs/logs/<job_basename>_submission_decision.json`,
2. use `resume_version`, `resume_file`, and `cv_file` from that decision JSON,
3. verify the referenced files exist,
4. avoid stale resume/CV-missing blockers when files exist,
5. keep real blockers visible, such as inaccessible platform forms or missing credentials,
6. keep explicit human approval boundary visible.

## Recommended command

Inside Hermes:

```text
/live-submission-adapter Create a controlled live submission dry-run package for data/jobs/02_avilen_semiconductor_cv_ai_intern_2026.json using available artifacts under outputs/, including outputs/logs/02_avilen_semiconductor_cv_ai_intern_2026_submission_decision.json and linked resume artifacts. Write outputs/logs/02_avilen_semiconductor_cv_ai_intern_2026_live_submission_dry_run_plan.md, outputs/logs/02_avilen_semiconductor_cv_ai_intern_2026_live_submission_field_mapping.md, outputs/logs/02_avilen_semiconductor_cv_ai_intern_2026_live_submission_authorization_request.md, and outputs/logs/02_avilen_semiconductor_cv_ai_intern_2026_live_submission_result_stub.json. Do not submit by default. Stop before final submission. Require explicit human approval before any submit action. The authorization request must include the exact line "Explicit approval is required."
```

## Tests

```bash
cd job-hunt
JOB_HUNT_TEST_BASENAME=02_avilen_semiconductor_cv_ai_intern_2026 ../.venv/bin/python -m pytest tests/test_live_submission_resume_awareness.py -q
```

Then run all tests:

```bash
JOB_HUNT_TEST_BASENAME=02_avilen_semiconductor_cv_ai_intern_2026 ../.venv/bin/python -m pytest tests -q
```

## Expected remaining blockers

Even after this stage passes, live submission may remain blocked because of real platform or review issues, such as:

- Wantedly login credentials unavailable,
- form inaccessible through browser automation,
- user has not provided explicit approval,
- application content still requires human review.

These blockers are valid and should not be hidden.
