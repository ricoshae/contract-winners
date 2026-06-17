# AusTender Contract Winners Scanner

Scans recently awarded Australian Government contracts via the AusTender OCDS API for e-learning/LMS-related projects. Outputs supplier details to CSV for outreach.

## Usage

```bash
pip install -r requirements.txt
python contract_winners.py
```

Results are written to `results.csv`.

## Automation

A GitHub Actions workflow runs weekly (Sunday 7am AEST) and commits updated results to the repo. Can also be triggered manually via `workflow_dispatch`.
