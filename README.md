# AI Readiness Auditor · 0.3.0

**Evidence-led organizational assessment.** A structured workshop tool for consultants, delivery leads and internal AI teams. It converts five self-reported maturity ratings into an explicit weighted score and an ordered gap-closing conversation.

The interface is a task-specific workbench, with labeled forms or CSV imports, previews, understandable diagnostics, charts/tables, actionable errors and reusable exports. It is a self-hosted engineering tool, not a claim of certified enterprise production readiness. Methods are deterministic and transparent; no paid service or GPU is required.

## Quickstart

```sh
docker compose up --build
```

Open http://127.0.0.1:8000. Click **Load synthetic example**, then **Run analysis**. Bundled data are explicitly synthetic. The full user guide is linked in the application at `/guide` and saved in [docs/USER_GUIDE.md](docs/USER_GUIDE.md). API schemas and examples are at `/docs`.

Run without Docker (Python 3.12):

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install --require-hashes -r requirements-dev.lock
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

For several apps, change the compose host port; each container listens on 8000. Stateless imports are processed in memory. Reports/configurations can contain your data and should be handled accordingly.

## Real functionality

The rubric weights strategy 20%, data 25%, governance 20%, people 15% and infrastructure 20%. A score is divided by 5 and multiplied by its weight. Nonblank evidence descriptions preserve the self-reported score; missing evidence caps the effective score at 1. Scores of 80+ are labeled ready, 50–79.99 developing, lower scores foundational. These bands and weights are transparent heuristics, not an industry standard or certification.

Action priority is the weight multiplied by the gap from 5. This can rank a low governance rating above a larger gap in a lower-weight dimension. Evidence presence is not evidence verification: the tool does not visit links, audit policies, interview employees or check legal compliance.

## Workflow and examples

1. Open the app and complete the five maturity questions. Choose 0 (not established) through 5 (repeatedly improved).
2. For each dimension, enter evidence descriptions on separate lines. Use short references such as “Q3 risk review record”; do not paste confidential documents.
3. Run analysis. Inspect reported versus effective scores, evidence presence and weighted priorities.
4. Use the suggested actions to assign an owner, deadline and expected evidence in your own project system.
5. Export the questionnaire configuration to reuse it, or export the dated report including inputs and results. Importing a saved questionnaire marks it as your input, not a synthetic example.
6. Print / save PDF uses your browser's print dialog. The app does not generate an independently certified PDF.

The typed JSON API remains supported:

```sh
curl --fail-with-body http://127.0.0.1:8000/analyze -H 'Content-Type: application/json' --data-binary @examples/synthetic.json
```

CSV-based applications also expose `/csv/preview` and `/csv/analyze`, documented in `/docs`. Importing CSV never executes spreadsheet formulas. Exported CSV from FlowPilot neutralizes formula-like text. Report/configuration export is JSON; browser print can save the result to PDF. No report is represented as an independent audit certification.

## Validation and evidence

```sh
python -m pytest -q
node --test tests/ui.test.mjs
python -m bandit -r app -ll
python -m pip_audit --disable-pip --no-deps --require-hashes -r requirements.lock
```

Historical 0.2 validation is retained under `evidence/rebuild/`; current 0.3 checks are recorded under `evidence/improvements-0.3/`. Older evidence documents the earlier implementation and must not be treated as proof of this interface. Meaningful existing arithmetic/security tests are retained. CI checks Python and frontend tests, dependency vulnerabilities, secret patterns, container vulnerabilities and real HTTP smoke operation. Require the `quality` check in repository branch protection to prevent merging failing revisions; a workflow alone cannot enforce that policy.

## Limits and troubleshooting

Synthetic example: maturity scores 4,3,2,4,3 with short synthetic evidence descriptions yield 63/100 and a developing band. Governance is the highest weighted gap. Editing any field removes the synthetic provenance badge and invalidates previous results.

A high reported maturity with no evidence produces a low effective score. If import fails, check that all five dimensions exist, grades are integer 0–5, and evidence is a list of at most 20 strings. API clients may use fractional scores; the questionnaire UI uses discrete maturity levels.

HTTP JSON requests are bounded at 2 MiB; CSV parsing is bounded at 50 columns/10000 rows. Requests are local CPU work, no outside actions. Authentication and HTTPS are required when deploying beyond a trusted localhost environment. See the user guide for detailed method/resource limitations. This release provides no authentication, durable history or multi-user access management.

## License

MIT. See LICENSE. Review transitive dependency licenses for your distribution. Contributors and review evidence are automated engineering work; no human reviewer is invented.

## Baseline comparisons in 0.3

Use “Import a previous configuration or report” to load a baseline without replacing the current questionnaire. Files exported by 0.2 and 0.3 are supported when they contain the original five dimension inputs. Exported totals are ignored: both inputs are recomputed using the same fixed weights and evidence cap. The current questionnaire remains independently editable.

Run analysis to see the baseline total, current total and signed delta, plus each dimension's effective score and weighted-point change. Evidence descriptions are trimmed and compared as sets. “Added” and “removed” refer to descriptions, not controls independently verified. Duplicate descriptions do not increase readiness. Replacing a description can show both an addition and removal while the score remains unchanged. Changes can be negative. These comparisons do not establish certification, regulatory compliance or a causal effect of an intervention.

Export configuration preserves the optional baseline, and report exports include the comparison result. Clear baseline returns to a single assessment. Importing a baseline or current configuration marks the run as your input, and stale asynchronous file reads cannot replace newer selections.

API: POST /compare with {"baseline": {"dimensions": ...}, "current": {"dimensions": ...}}. The response retains the current assessment fields and adds “comparison”. For a configuration containing a baseline, send its dimensions under “current” and its baseline under “baseline”; plain configurations without a baseline still map to /analyze. Prior report result scores are never accepted as an alternative to dimension inputs. The fixed rubric is unchanged.

Fresh 0.3 validation is saved in `evidence/improvements-0.3/`; older reports describe earlier versions and are not proof of these additions. This is automated developer work with separate release-manager and independent QA gates; no human review or enterprise certification is claimed.

The new synthetic request `examples/synthetic-improvements-03.json` demonstrates this version. POST it to `/compare`; all data are synthetic.
