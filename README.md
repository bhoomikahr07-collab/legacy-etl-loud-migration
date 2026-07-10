# Legacy ETL Modernization Simulation (SSIS → Cloud) with CI/CD

Simulates migrating a legacy on-prem SSIS-style ETL workflow (SQL Server
extract → transform → load) to a cloud-native Python + AWS Glue pipeline,
with a documented source-to-target mapping spec, a lightweight data
catalog entry and runbook, and a GitHub Actions CI/CD pipeline that tests
and deploys the ETL job across dev/test/prod.

## Why this project exists

A lot of real-world data engineering work isn't greenfield — it's taking
something that already runs (often an SSIS package, a cron'd stored
procedure, or an Informatica workflow) and re-platforming it to the
cloud without changing what the business gets out of it. This project
simulates that: a legacy-style extract, a field-level mapping spec
(exactly what you'd hand to a reviewer before touching the target
schema), and the operational documentation a real migration needs.

## What this project demonstrates

- **Legacy → cloud migration** — a documented legacy SSIS-style workflow (`legacy/legacy_ssis_workflow.md`) re-implemented as a Python/AWS Glue pipeline (`src/extract.py`, `src/transform.py`, `src/load.py`, `src/glue_job.py`)
- **Source-to-target mapping spec** — field-level mapping doc used to drive (and test) the transform logic (`mapping_specs/source_to_target_mapping.md`)
- **Lightweight data catalog entry** — dataset metadata: owner, schema, lineage, refresh cadence, sensitivity (`catalog/data_catalog_entry.md`)
- **Runbook** — how to run it, monitor it, and recover from common failures, written for handover to someone who didn't build it (`runbook/RUNBOOK.md`)
- **CI/CD with GitHub Actions** — automated tests on every PR, and environment-gated deploys to dev/test/prod (`.github/workflows/ci.yml`, `.github/workflows/deploy.yml`)

## Why AWS Glue *Python Shell*, not Spark

The other two projects in this series (`retail-etl-aws`,
`retail-lakehouse-azure`) use PySpark for large, partitioned retail
datasets. This one intentionally uses a **Glue Python Shell job**
instead — plain Python, no Spark cluster — because that's the realistic
choice for migrating a modest legacy extract (a few hundred thousand
rows, not billions), and it's cheaper and faster to run. Knowing when
*not* to reach for Spark is part of the job.

## Repo structure

```
legacy-to-cloud-migration/
├── legacy/
│   └── legacy_ssis_workflow.md        # what the legacy workflow did (control flow, data flow, schedule)
├── mapping_specs/
│   └── source_to_target_mapping.md    # field-level source -> target mapping spec
├── data/
│   └── generate_legacy_source.py      # simulates the legacy SQL Server extract (with legacy quirks)
├── src/
│   ├── schema.py                       # target schema definition
│   ├── extract.py                      # reads the legacy-style extract
│   ├── transform.py                    # applies the mapping spec (renames, type/format conversions)
│   ├── load.py                         # writes target CSV/JSON (+ S3 upload path for prod)
│   ├── glue_job.py                     # AWS Glue Python Shell job entry point
│   └── utils.py
├── catalog/
│   └── data_catalog_entry.md
├── runbook/
│   └── RUNBOOK.md
├── tests/
│   └── test_transform.py               # unit tests for the mapping/transform logic
├── config/
│   └── config.yaml                     # per-environment (dev/test/prod) paths
└── .github/workflows/
    ├── ci.yml                          # lint + test on every PR
    └── deploy.yml                      # deploy to dev/test/prod by branch
```

## Running it locally

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python data/generate_legacy_source.py     # simulate the legacy extract
python src/extract.py --env local
python src/transform.py --env local
python src/load.py --env local
pytest tests/
```

This was run end-to-end while building this repo — see the sample output
below. No cloud account needed for local mode; `--env prod` (or `dev`/`test`)
switches the S3 paths in `config/config.yaml` and enables the boto3 upload
path in `src/load.py`.

## CI/CD flow

- **Any PR** → `ci.yml` runs `flake8` and `pytest`.
- **Push to `develop`** → `deploy.yml` deploys the Glue job script to the **dev** Glue job and runs it once as a smoke test.
- **Push to `test`** → deploys to **test** and runs the full test-environment validation.
- **Push to `main`** → deploys to **prod**, gated behind a GitHub Environment manual-approval rule (set this up in repo Settings → Environments → `production` → required reviewers).

## Deploying to AWS

1. Upload `src/*.py` to `s3://<bucket>/glue-scripts/legacy-migration/`.
2. Create a Glue **Python Shell** job (not Spark) pointing at
   `src/glue_job.py`, with `--EXTRA_PY_FILES` including `schema.py`,
   `extract.py`, `transform.py`, `load.py`, `utils.py`.
3. Set job parameters `--ENV`, `--SOURCE_PATH`, `--TARGET_PATH` per
   environment (see `config/config.yaml`).
4. Wire up `.github/workflows/deploy.yml` with AWS credentials as GitHub
   secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`)
   scoped to a deploy role with least-privilege Glue/S3 permissions.
