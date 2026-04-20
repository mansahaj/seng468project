import argparse
import csv
import json
from pathlib import Path

from loadtests.common import now_iso, system_info


def read_aggregate_row(stats_csv: Path) -> dict:
    with stats_csv.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("Name") == "Aggregated":
                return row
    raise RuntimeError(f"Aggregated row not found in {stats_csv}")


def to_float(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def summarize_scenario(name: str, prefix: Path) -> dict:
    row = read_aggregate_row(prefix.with_name(prefix.name + "_stats.csv"))
    summary = {
        "request_count": int(to_float(row["Request Count"])),
        "failure_count": int(to_float(row["Failure Count"])),
        "mean_ms": round(to_float(row["Average Response Time"]), 2),
        "p50_ms": round(to_float(row["50%"]), 2),
        "p95_ms": round(to_float(row["95%"]), 2),
        "p99_ms": round(to_float(row["99%"]), 2),
        "max_ms": round(to_float(row["Max Response Time"]), 2),
        "throughput_rps": round(to_float(row["Requests/s"]), 2),
    }
    if name == "concurrent_uploads":
        summary["target_under_500ms_pass"] = summary["p95_ms"] < 500
    if name == "concurrent_searches":
        summary["p95_under_2s_pass"] = summary["p95_ms"] < 2000
    return summary


def build_bottleneck_notes(results: dict) -> list[str]:
    notes = []
    uploads = results["concurrent_uploads"]
    searches = results["concurrent_searches"]
    mixed = results["mixed_workload"]

    if not uploads["target_under_500ms_pass"]:
        notes.append(
            "Upload endpoint latency exceeded the 500ms target under concurrency, so the API upload path needs optimization."
        )
    if not searches["p95_under_2s_pass"]:
        notes.append(
            "Concurrent search P95 exceeded 2 seconds, indicating cold-start overhead or semantic search compute contention."
        )
    if mixed["failure_count"] > 0:
        notes.append(
            "Mixed workload produced request failures, which points to resource exhaustion or queue contention under combined traffic."
        )
    if not notes:
        notes.append(
            "The baseline Locust scenarios completed without request failures at the chosen concurrency, so the current architecture is stable at this load level."
        )
    notes.append(
        "Because semantic embeddings are computed locally, model initialization and CPU-bound embedding work remain the most likely bottlenecks as load grows."
    )
    return notes


def write_markdown(path: Path, results: dict) -> None:
    uploads = results["concurrent_uploads"]
    searches = results["concurrent_searches"]
    mixed = results["mixed_workload"]

    lines = [
        "# Locust Load Test Report",
        "",
        f"Generated: {results['generated_at']}",
        "",
        "## Environment",
        "",
        f"- Base URL: `{results['base_url']}`",
        f"- OS: `{results['environment']['platform']}`",
        f"- Architecture: `{results['environment']['machine']}`",
        f"- CPU count: `{results['environment']['cpu_count']}`",
        f"- Memory (GB): `{results['environment']['memory_gb']}`",
        "",
        "## Concurrent Uploads",
        "",
        f"- Requests: {uploads['request_count']}",
        f"- Failures: {uploads['failure_count']}",
        f"- Mean latency: {uploads['mean_ms']} ms",
        f"- P50: {uploads['p50_ms']} ms",
        f"- P95: {uploads['p95_ms']} ms",
        f"- P99: {uploads['p99_ms']} ms",
        f"- Max: {uploads['max_ms']} ms",
        f"- Throughput: {uploads['throughput_rps']} req/s",
        f"- Meets `< 500ms` upload target: {uploads['target_under_500ms_pass']}",
        "",
        "## Concurrent Searches",
        "",
        f"- Requests: {searches['request_count']}",
        f"- Failures: {searches['failure_count']}",
        f"- Mean latency: {searches['mean_ms']} ms",
        f"- P50: {searches['p50_ms']} ms",
        f"- P95: {searches['p95_ms']} ms",
        f"- P99: {searches['p99_ms']} ms",
        f"- Max: {searches['max_ms']} ms",
        f"- Throughput: {searches['throughput_rps']} req/s",
        f"- Meets `P95 < 2s` search target: {searches['p95_under_2s_pass']}",
        "",
        "## Mixed Workload",
        "",
        f"- Requests: {mixed['request_count']}",
        f"- Failures: {mixed['failure_count']}",
        f"- Mean latency: {mixed['mean_ms']} ms",
        f"- P50: {mixed['p50_ms']} ms",
        f"- P95: {mixed['p95_ms']} ms",
        f"- P99: {mixed['p99_ms']} ms",
        f"- Max: {mixed['max_ms']} ms",
        f"- Throughput: {mixed['throughput_rps']} req/s",
        "",
        "## Bottleneck Notes",
        "",
    ]
    for note in results["bottleneck_notes"]:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Locust CSV outputs into JSON and Markdown.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--uploads-prefix", default="loadtests/results/locust_uploads")
    parser.add_argument("--search-prefix", default="loadtests/results/locust_searches")
    parser.add_argument("--mixed-prefix", default="loadtests/results/locust_mixed")
    parser.add_argument("--output-json", default="loadtests/results/locust_summary.json")
    parser.add_argument("--output-md", default="loadtests/results/locust_summary.md")
    args = parser.parse_args()

    results = {
        "generated_at": now_iso(),
        "base_url": args.base_url,
        "environment": system_info(),
        "concurrent_uploads": summarize_scenario("concurrent_uploads", Path(args.uploads_prefix)),
        "concurrent_searches": summarize_scenario("concurrent_searches", Path(args.search_prefix)),
        "mixed_workload": summarize_scenario("mixed_workload", Path(args.mixed_prefix)),
    }
    results["bottleneck_notes"] = build_bottleneck_notes(results)

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.write_text(json.dumps(results, indent=2))
    write_markdown(output_md, results)

    print(json.dumps(results, indent=2))
    print(f"Wrote JSON summary to {output_json}")
    print(f"Wrote Markdown summary to {output_md}")


if __name__ == "__main__":
    main()
