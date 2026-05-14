# Project Stage After Job Source Production Readiness Audit

## Stage

The Hermes Japan job-hunt project is now in the **job source production readiness audit stage**.

## What this adds

A repeatable check for the real-world source layer:

```text
data/job_sources.json
fetch/source monitor output
public careers extraction output
dedup output
ranking output
Telegram render output
```

## Why it matters

After the local pipeline closes, production failures are most likely to come from:

```text
job sites changing page structure
network source producing no snapshots
adapter extracting too many low-quality fragments
dedup suppressing all candidates
ranking producing zero notifications for too long
```

## Recommended next step

Run the audit after every scheduled watch-cycle deployment and before adding a new public job source.
