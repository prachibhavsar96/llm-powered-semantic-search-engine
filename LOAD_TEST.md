# Load Testing /search

A minimal Locust load test that logs in once per simulated user, then
repeatedly calls `POST /search` with a realistic query from a small sample
set, waiting 1-3 seconds between requests.

## Prerequisites

- The API running locally (e.g. `uvicorn app.main:app`).
- `locust` installed: `pip install -r requirements.txt`.

## Interactive run (with web UI)

```
locust -f locustfile.py --host=http://localhost:8000
```

Then open http://localhost:8089, set the number of users and spawn rate,
and start the test from the UI.

## Headless run (fixed duration, CSV output)

```
locust -f locustfile.py --host=http://localhost:8000 --users 50 --spawn-rate 5 --run-time 2m --headless --csv=results
```

This runs 50 simulated users (ramping up at 5/sec) for 2 minutes and writes
`results_stats.csv`, `results_stats_history.csv`, and `results_failures.csv`.

## Results

Results: <run locally and paste real numbers here>
