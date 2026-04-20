# Load Testing

This project now uses Locust as the primary load-testing tool.

Primary files:
- [locustfile.py](/Users/mansahaj/projects/seng468project/loadtests/locustfile.py:1)
- [seed_data.py](/Users/mansahaj/projects/seng468project/loadtests/seed_data.py:1)
- [run_locust_baseline.py](/Users/mansahaj/projects/seng468project/loadtests/run_locust_baseline.py:1)
- [summarize_locust.py](/Users/mansahaj/projects/seng468project/loadtests/summarize_locust.py:1)

The Locust setup covers the project scenarios:
- concurrent uploads
- concurrent searches
- mixed upload/search workload

There is also a custom benchmark helper in [benchmark.py](/Users/mansahaj/projects/seng468project/loadtests/benchmark.py:1), but Locust is the report/demo path.

## Run

Start the application stack first:

```bash
cp .env.example .env
docker compose down -v
docker compose up --build
```

If Locust is not installed locally:

```bash
python3 -m pip install -r loadtests/requirements.txt
```

Run the baseline Locust suite:

```bash
python3 loadtests/run_locust_baseline.py --base-url http://127.0.0.1:8080
```

## Outputs

- `loadtests/results/locust_uploads_stats.csv`
- `loadtests/results/locust_searches_stats.csv`
- `loadtests/results/locust_mixed_stats.csv`
- `loadtests/results/locust_summary.json`
- `loadtests/results/locust_summary.md`

These include:
- mean latency
- P50 / P95 / P99
- throughput
- failure counts
- bottleneck notes
