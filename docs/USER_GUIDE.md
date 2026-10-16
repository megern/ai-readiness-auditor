# AI Readiness Auditor — User guide

## Intended use

A structured workshop tool for consultants, delivery leads and internal AI teams. It converts five self-reported maturity ratings into an explicit weighted score and an ordered gap-closing conversation.

## Walkthrough

1. Open the app and complete the five maturity questions. Choose 0 (not established) through 5 (repeatedly improved).
2. For each dimension, enter evidence descriptions on separate lines. Use short references such as “Q3 risk review record”; do not paste confidential documents.
3. Run analysis. Inspect reported versus effective scores, evidence presence and weighted priorities.
4. Use the suggested actions to assign an owner, deadline and expected evidence in your own project system.
5. Export the questionnaire configuration to reuse it, or export the dated report including inputs and results. Importing a saved questionnaire marks it as your input, not a synthetic example.
6. Print / save PDF uses your browser's print dialog. The app does not generate an independently certified PDF.

## Method and interpretation

The rubric weights strategy 20%, data 25%, governance 20%, people 15% and infrastructure 20%. A score is divided by 5 and multiplied by its weight. Nonblank evidence descriptions preserve the self-reported score; missing evidence caps the effective score at 1. Scores of 80+ are labeled ready, 50–79.99 developing, lower scores foundational. These bands and weights are transparent heuristics, not an industry standard or certification.

Action priority is the weight multiplied by the gap from 5. This can rank a low governance rating above a larger gap in a lower-weight dimension. Evidence presence is not evidence verification: the tool does not visit links, audit policies, interview employees or check legal compliance.

## Examples and troubleshooting

Synthetic example: maturity scores 4,3,2,4,3 with short synthetic evidence descriptions yield 63/100 and a developing band. Governance is the highest weighted gap. Editing any field removes the synthetic provenance badge and invalidates previous results.

A high reported maturity with no evidence produces a low effective score. If import fails, check that all five dimensions exist, grades are integer 0–5, and evidence is a list of at most 20 strings. API clients may use fractional scores; the questionnaire UI uses discrete maturity levels.

## Resource and privacy limits

The HTTP guard bounds state-changing JSON bodies at 2 MiB and rejects excessive nesting, nonfinite numbers and numeric magnitudes beyond 1e100. CSV imports allow up to 50 unique columns and 10000 nonblank rows, with 10000-character cells. FlowPilot additionally caps each node at 10000 rows and conservatively bounds retained workflow outputs at 4 MiB. Browser previews and tables are bounded. Splitting files can change the analytical meaning: do not split event cases or evaluation splits arbitrarily.

The application is stateless and does not persist uploads. Your browser may retain downloads and form content; printed reports and configurations can contain the input data. No external resources or paid APIs are contacted. Requests go to the server you opened: self-host on a trusted machine. Authentication, multi-user access controls, secure ingress, rate limiting and operational backups are deployment responsibilities, not claims of this release.

## API and reuse

Open /docs for the complete schema. POST /analyze remains available for typed JSON inputs. CSV-based tools additionally provide POST /csv/preview and POST /csv/analyze. Configuration exports map directly to the relevant endpoint; readiness uses /analyze, the three CSV tools use /csv/analyze. Report exports contain application/version/date, synthetic provenance, original input and analytical output. They are data files, not executable programs.

All bundled examples are synthetic and are labeled. Editing or importing your own input resets that badge and clears stale results. Controls are locked during analysis; a generation check also prevents a late response replacing changed input results. Error messages identify the failed field or operation; correct it and rerun. Failed analyses never certify completion or preserve an old result as current.

## Local operation

Run docker compose up --build and open http://127.0.0.1:8000. Alternatively install requirements-dev.lock with hashes in a Python 3.12 environment and run uvicorn app.main:app --host 127.0.0.1 --port 8000. Change the host port to run multiple tools. No GPU is needed.
