# Project Stage After Public Careers Extraction Quality Audit

## Stage

The Hermes Japan job-hunt project is now in the **public careers extraction quality audit stage**.

## What this adds

A quality gate between source extraction and production use.

It helps catch cases where a public careers page is split into low-quality fragments:

```text
requirements
skills
short labels
generic technology names
```

instead of real internship/theme entries.

## Recommended next step

Use the audit output to harden one public source adapter at a time:

```text
NTT Labs
PFN
Wantedly
Rakuten
```

Start with the source that produces the most low-quality blocked candidates.
