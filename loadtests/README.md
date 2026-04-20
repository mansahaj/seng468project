# Load Testing

This project includes a repo-local benchmark harness in [benchmark.py](/Users/mansahaj/projects/seng468project/loadtests/benchmark.py:1).

It exercises three scenarios against the running API:
- concurrent uploads
- concurrent searches
- mixed upload/search workload

The script:
- signs up and logs in test users
- uploads generated PDF files
- waits for asynchronous processing to complete when needed
- measures request latency and throughput
- writes JSON and Markdown reports under `loadtests/results/`

## Run

Start the application stack first:

```bash
cp .env.example .env
docker compose down -v
docker compose up --build
```

Then run the benchmark:

```bash
python3 loadtests/benchmark.py --base-url http://127.0.0.1:8080
```

Optional tuning:

```bash
python3 loadtests/benchmark.py \
  --concurrent-users 6 \
  --searches-per-user 5 \
  --mixed-operations 6
```

## Outputs

- `loadtests/results/latest.json`
- `loadtests/results/latest.md`

These include:
- mean latency
- P50 / P95 / P99
- throughput
- upload processing-to-ready timings
- initial bottleneck notes
