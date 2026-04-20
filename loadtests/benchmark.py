import argparse
import json
import math
import mimetypes
import os
import platform
import random
import statistics
import string
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def random_suffix(length: int = 8) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100) * (len(sorted_values) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return sorted_values[low]
    weight = rank - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def summarize_latencies(latencies: list[float], duration_s: float) -> dict:
    if not latencies:
        return {
            "count": 0,
            "failures": 0,
            "mean_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "max_ms": 0.0,
            "throughput_rps": 0.0,
        }
    return {
        "count": len(latencies),
        "mean_ms": round(statistics.mean(latencies), 2),
        "p50_ms": round(percentile(latencies, 50), 2),
        "p95_ms": round(percentile(latencies, 95), 2),
        "p99_ms": round(percentile(latencies, 99), 2),
        "max_ms": round(max(latencies), 2),
        "throughput_rps": round(len(latencies) / max(duration_s, 0.001), 2),
    }


def best_effort_memory_gb() -> float | None:
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True,
            check=True,
        )
        return round(int(result.stdout.strip()) / (1024 ** 3), 2)
    except Exception:
        return None


def build_pdf_bytes(title: str, body_text: str, page_count: int = 3) -> bytes:
    objects: list[bytes] = []

    def add_object(data: str) -> int:
        objects.append(data.encode("latin-1"))
        return len(objects)

    catalog_id = add_object("<< /Type /Catalog /Pages 2 0 R >>")
    pages_placeholder_id = add_object("<< /Type /Pages /Kids [] /Count 0 >>")
    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_ids: list[int] = []
    content_ids: list[int] = []

    for page_index in range(page_count):
        safe_lines = [
            f"{title} Page {page_index + 1}",
            body_text,
            "semantic retrieval distributed systems scalability queue worker",
            "docker compose minio qdrant redis postgresql concurrency testing",
            "software engineering refactoring performance optimization search",
        ]
        text_commands = ["BT", "/F1 12 Tf", "72 750 Td"]
        for line_index, line in enumerate(safe_lines):
            escaped_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if line_index == 0:
                text_commands.append(f"({escaped_line}) Tj")
            else:
                text_commands.append(f"0 -18 Td ({escaped_line}) Tj")
        text_commands.append("ET")
        stream = "\n".join(text_commands)
        content_id = add_object(
            f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream"
        )
        page_id = add_object(
            "<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )
        content_ids.append(content_id)
        page_ids.append(page_id)

    pages_obj = (
        "<< /Type /Pages "
        f"/Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] "
        f"/Count {len(page_ids)} >>"
    )
    objects[pages_placeholder_id - 1] = pages_obj.encode("latin-1")

    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode("latin-1")
    )
    return bytes(pdf)


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _request(self, path: str, method: str = "GET", data: bytes | None = None, headers: dict | None = None) -> tuple[int, str]:
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers or {},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def json_request(
        self,
        path: str,
        method: str = "GET",
        payload: dict | None = None,
        token: str | None = None,
    ) -> tuple[int, dict | list | None]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        status, body = self._request(path, method=method, data=data, headers=headers)
        return status, json.loads(body) if body else None

    def signup_and_login(self, username_prefix: str, password: str) -> tuple[str, str]:
        username = f"{username_prefix}_{random_suffix()}"
        signup_status, signup_body = self.json_request(
            "/auth/signup",
            method="POST",
            payload={"username": username, "password": password},
        )
        if signup_status != 200:
            raise RuntimeError(f"signup failed for {username}: {signup_status} {signup_body}")

        login_status, login_body = self.json_request(
            "/auth/login",
            method="POST",
            payload={"username": username, "password": password},
        )
        if login_status != 200:
            raise RuntimeError(f"login failed for {username}: {login_status} {login_body}")

        return username, login_body["token"]

    def upload_pdf(self, token: str, filename: str, content: bytes) -> tuple[int, dict, float]:
        boundary = f"----LoadTestBoundary{random_suffix(12)}"
        content_type = mimetypes.guess_type(filename)[0] or "application/pdf"
        parts = [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode(),
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
        body = b"".join(parts)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }

        start = time.perf_counter()
        status, response_body = self._request("/documents", method="POST", data=body, headers=headers)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return status, json.loads(response_body), elapsed_ms

    def list_documents(self, token: str) -> list[dict]:
        status, payload = self.json_request("/documents", token=token)
        if status != 200:
            raise RuntimeError(f"list documents failed: {status} {payload}")
        return payload

    def wait_until_ready(self, token: str, document_id: str, timeout_s: int = 180) -> tuple[str, float]:
        start = time.perf_counter()
        while time.perf_counter() - start < timeout_s:
            docs = self.list_documents(token)
            target = next((doc for doc in docs if doc["document_id"] == document_id), None)
            if target and target["status"] in {"ready", "failed"}:
                return target["status"], time.perf_counter() - start
            time.sleep(2)
        return "timeout", time.perf_counter() - start

    def search(self, token: str, query: str) -> tuple[int, list, float]:
        encoded_query = urllib.parse.urlencode({"q": query})
        start = time.perf_counter()
        status, payload = self.json_request(f"/search?{encoded_query}", token=token)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return status, payload, elapsed_ms


def run_concurrent_uploads(client: ApiClient, concurrent_users: int, password: str) -> dict:
    users = [client.signup_and_login("upload_user", password) for _ in range(concurrent_users)]
    pdf_bytes = build_pdf_bytes(
        "Concurrent Upload Test",
        "This PDF is generated for concurrent upload load testing.",
        page_count=4,
    )

    barrier = threading.Barrier(len(users))
    latencies = []
    failures = 0
    processing_durations = []
    processing_failures = 0
    document_refs: list[tuple[str, str]] = []

    def upload_worker(token: str, index: int):
        barrier.wait()
        status, body, latency_ms = client.upload_pdf(
            token,
            f"upload_test_{index}.pdf",
            pdf_bytes,
        )
        return token, status, body, latency_ms

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(users)) as executor:
        futures = [
            executor.submit(upload_worker, token, index)
            for index, (_, token) in enumerate(users)
        ]
        for future in as_completed(futures):
            token, status, body, latency_ms = future.result()
            if status == 202:
                latencies.append(latency_ms)
                document_refs.append((token, body["document_id"]))
            else:
                failures += 1
    duration_s = time.perf_counter() - start

    for token, document_id in document_refs:
        ready_status, ready_duration = client.wait_until_ready(token, document_id)
        if ready_status == "ready":
            processing_durations.append(round(ready_duration, 2))
        else:
            processing_failures += 1

    summary = summarize_latencies(latencies, duration_s)
    summary["failures"] = failures
    summary["processing_ready_mean_s"] = round(
        statistics.mean(processing_durations), 2
    ) if processing_durations else 0.0
    summary["processing_ready_max_s"] = round(
        max(processing_durations), 2
    ) if processing_durations else 0.0
    summary["processing_failures"] = processing_failures
    summary["target_under_500ms_pass"] = all(lat <= 500 for lat in latencies) if latencies else False
    return summary


def seed_search_users(client: ApiClient, user_count: int, password: str) -> list[tuple[str, str, str]]:
    seeded = []
    for index in range(user_count):
        username, token = client.signup_and_login("search_user", password)
        pdf_bytes = build_pdf_bytes(
            f"Search Seed {index}",
            (
                "semantic retrieval scalable architecture distributed systems "
                "docker compose object storage vector search concurrency"
            ),
            page_count=3,
        )
        status, body, _ = client.upload_pdf(token, f"search_seed_{index}.pdf", pdf_bytes)
        if status != 202:
            raise RuntimeError(f"seed upload failed: {status} {body}")
        ready_status, _ = client.wait_until_ready(token, body["document_id"])
        if ready_status != "ready":
            raise RuntimeError(f"seed document did not become ready for {username}")
        seeded.append((username, token, body["document_id"]))
    return seeded


def run_concurrent_searches(
    client: ApiClient,
    concurrent_users: int,
    searches_per_user: int,
    password: str,
) -> dict:
    seeded_users = seed_search_users(client, concurrent_users, password)
    barrier = threading.Barrier(len(seeded_users))
    queries = [
        "semantic retrieval",
        "distributed systems",
        "docker compose scalability",
        "object storage vector search",
        "software performance optimization",
    ]
    latencies = []
    failures = 0

    def search_worker(token: str, worker_index: int):
        barrier.wait()
        results = []
        for iteration in range(searches_per_user):
            query = queries[(worker_index + iteration) % len(queries)]
            status, payload, latency_ms = client.search(token, query)
            results.append((status, payload, latency_ms))
        return results

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(seeded_users)) as executor:
        futures = [
            executor.submit(search_worker, token, index)
            for index, (_, token, _) in enumerate(seeded_users)
        ]
        for future in as_completed(futures):
            for status, payload, latency_ms in future.result():
                if status == 200 and payload:
                    latencies.append(latency_ms)
                elif status == 200 and payload == []:
                    failures += 1
                else:
                    failures += 1
    duration_s = time.perf_counter() - start

    summary = summarize_latencies(latencies, duration_s)
    summary["failures"] = failures
    summary["total_requests"] = concurrent_users * searches_per_user
    summary["p95_under_2s_pass"] = percentile(latencies, 95) < 2000 if latencies else False
    return summary


def run_mixed_workload(
    client: ApiClient,
    concurrent_users: int,
    mixed_operations: int,
    password: str,
) -> dict:
    seeded_users = seed_search_users(client, concurrent_users, password)
    barrier = threading.Barrier(len(seeded_users))
    upload_pdf_bytes = build_pdf_bytes(
        "Mixed Workload Upload",
        "This PDF is created during mixed workload testing to stress the worker queue.",
        page_count=2,
    )
    upload_latencies = []
    search_latencies = []
    upload_failures = 0
    search_failures = 0

    def mixed_worker(token: str, worker_index: int):
        barrier.wait()
        results = []
        for iteration in range(mixed_operations):
            if iteration % 2 == 0:
                query = "semantic retrieval scalability"
                status, payload, latency_ms = client.search(token, query)
                results.append(("search", status, payload, latency_ms))
            else:
                status, payload, latency_ms = client.upload_pdf(
                    token,
                    f"mixed_upload_{worker_index}_{iteration}.pdf",
                    upload_pdf_bytes,
                )
                results.append(("upload", status, payload, latency_ms))
        return token, results

    start = time.perf_counter()
    uploaded_documents: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=len(seeded_users)) as executor:
        futures = [
            executor.submit(mixed_worker, token, index)
            for index, (_, token, _) in enumerate(seeded_users)
        ]
        for future in as_completed(futures):
            token, results = future.result()
            for kind, status, payload, latency_ms in results:
                if kind == "search":
                    if status == 200:
                        search_latencies.append(latency_ms)
                    else:
                        search_failures += 1
                else:
                    if status == 202:
                        upload_latencies.append(latency_ms)
                        uploaded_documents.append((token, payload["document_id"]))
                    else:
                        upload_failures += 1
    duration_s = time.perf_counter() - start

    processing_ready = 0
    processing_failures = 0
    for token, document_id in uploaded_documents:
        ready_status, _ = client.wait_until_ready(token, document_id, timeout_s=180)
        if ready_status == "ready":
            processing_ready += 1
        else:
            processing_failures += 1

    return {
        "duration_s": round(duration_s, 2),
        "upload": {
            **summarize_latencies(upload_latencies, duration_s),
            "failures": upload_failures,
        },
        "search": {
            **summarize_latencies(search_latencies, duration_s),
            "failures": search_failures,
        },
        "processing_ready": processing_ready,
        "processing_failures": processing_failures,
    }


def build_bottleneck_notes(results: dict) -> list[str]:
    notes = []
    uploads = results["concurrent_uploads"]
    searches = results["concurrent_searches"]
    mixed = results["mixed_workload"]

    if uploads["processing_ready_mean_s"] > 5:
        notes.append(
            "Background processing is materially slower than upload response latency, "
            "which suggests the worker embedding/indexing path is the main bottleneck."
        )
    if not uploads["target_under_500ms_pass"]:
        notes.append(
            "Concurrent upload responses exceeded the 500ms target, so the API upload path needs optimization."
        )
    if not searches["p95_under_2s_pass"]:
        notes.append(
            "Concurrent search P95 exceeded 2 seconds, which points to embedding/query cold starts or vector search contention."
        )
    if mixed["processing_failures"] > 0:
        notes.append(
            "Some mixed-workload uploads did not finish processing within the timeout, which suggests worker saturation."
        )
    if not notes:
        notes.append(
            "The baseline run did not show request failures under the chosen test sizes, but the single worker remains the most likely scaling bottleneck as load increases."
        )
    notes.append(
        "Cold starts from loading the sentence-transformer model can inflate the first search and first processing job in a fresh container."
    )
    return notes


def write_markdown_report(path: Path, results: dict) -> None:
    uploads = results["concurrent_uploads"]
    searches = results["concurrent_searches"]
    mixed = results["mixed_workload"]
    notes = results["bottleneck_notes"]

    report = f"""# Load Test Report

Generated: {results["generated_at"]}

## Environment

- Base URL: `{results["base_url"]}`
- OS: `{results["environment"]["platform"]}`
- Architecture: `{results["environment"]["machine"]}`
- CPU count: `{results["environment"]["cpu_count"]}`
- Memory (GB): `{results["environment"]["memory_gb"]}`

## Concurrent Uploads

- Requests: {uploads["count"]}
- Failures: {uploads["failures"]}
- Mean latency: {uploads["mean_ms"]} ms
- P50: {uploads["p50_ms"]} ms
- P95: {uploads["p95_ms"]} ms
- P99: {uploads["p99_ms"]} ms
- Max: {uploads["max_ms"]} ms
- Throughput: {uploads["throughput_rps"]} req/s
- Mean processing-to-ready: {uploads["processing_ready_mean_s"]} s
- Max processing-to-ready: {uploads["processing_ready_max_s"]} s
- Meets `< 500ms` upload target: {uploads["target_under_500ms_pass"]}

## Concurrent Searches

- Requests: {searches["total_requests"]}
- Failures: {searches["failures"]}
- Mean latency: {searches["mean_ms"]} ms
- P50: {searches["p50_ms"]} ms
- P95: {searches["p95_ms"]} ms
- P99: {searches["p99_ms"]} ms
- Max: {searches["max_ms"]} ms
- Throughput: {searches["throughput_rps"]} req/s
- Meets `P95 < 2s` search target: {searches["p95_under_2s_pass"]}

## Mixed Workload

### Upload

- Requests: {mixed["upload"]["count"]}
- Failures: {mixed["upload"]["failures"]}
- Mean latency: {mixed["upload"]["mean_ms"]} ms
- P95: {mixed["upload"]["p95_ms"]} ms
- Throughput: {mixed["upload"]["throughput_rps"]} req/s

### Search

- Requests: {mixed["search"]["count"]}
- Failures: {mixed["search"]["failures"]}
- Mean latency: {mixed["search"]["mean_ms"]} ms
- P95: {mixed["search"]["p95_ms"]} ms
- Throughput: {mixed["search"]["throughput_rps"]} req/s

### Processing Completion

- Ready: {mixed["processing_ready"]}
- Failures or timeouts: {mixed["processing_failures"]}

## Initial Bottleneck Notes

"""
    for note in notes:
        report += f"- {note}\n"

    path.write_text(report)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run baseline load tests for the semantic retrieval system.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--concurrent-users", type=int, default=4)
    parser.add_argument("--searches-per-user", type=int, default=4)
    parser.add_argument("--mixed-operations", type=int, default=4)
    parser.add_argument("--output-dir", default="loadtests/results")
    parser.add_argument("--password", default="LoadTestPass123!")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = ApiClient(args.base_url)
    root_status, _ = client._request("/")
    if root_status != 200:
        raise RuntimeError(f"API root is not reachable at {args.base_url}, got status {root_status}")

    results = {
        "generated_at": now_iso(),
        "base_url": args.base_url,
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "memory_gb": best_effort_memory_gb(),
        },
        "parameters": {
            "concurrent_users": args.concurrent_users,
            "searches_per_user": args.searches_per_user,
            "mixed_operations": args.mixed_operations,
        },
    }

    print("Running concurrent upload scenario...")
    results["concurrent_uploads"] = run_concurrent_uploads(
        client,
        args.concurrent_users,
        args.password,
    )

    print("Running concurrent search scenario...")
    results["concurrent_searches"] = run_concurrent_searches(
        client,
        args.concurrent_users,
        args.searches_per_user,
        args.password,
    )

    print("Running mixed workload scenario...")
    results["mixed_workload"] = run_mixed_workload(
        client,
        args.concurrent_users,
        args.mixed_operations,
        args.password,
    )

    results["bottleneck_notes"] = build_bottleneck_notes(results)

    json_path = output_dir / "latest.json"
    markdown_path = output_dir / "latest.md"
    json_path.write_text(json.dumps(results, indent=2))
    write_markdown_report(markdown_path, results)

    print(json.dumps(results, indent=2))
    print(f"Wrote JSON results to {json_path}")
    print(f"Wrote Markdown report to {markdown_path}")


if __name__ == "__main__":
    main()
