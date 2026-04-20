import json
import math
import mimetypes
import os
import platform
import random
import statistics
import string
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


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


def system_info() -> dict:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "memory_gb": best_effort_memory_gb(),
    }


def summarize_latencies(latencies: list[float], duration_s: float) -> dict:
    if not latencies:
        return {
            "count": 0,
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


def expand_text_to_size(base_text: str, target_size_bytes: int) -> str:
    encoded = base_text.encode("latin-1", errors="ignore")
    if len(encoded) >= target_size_bytes:
        return base_text

    repeated = []
    total = 0
    while total < target_size_bytes:
        repeated.append(base_text)
        total += len(encoded)
    return "\n".join(repeated)


def build_pdf_bytes(
    title: str,
    body_text: str,
    page_count: int = 3,
    target_size_bytes: int | None = None,
) -> bytes:
    if target_size_bytes:
        body_text = expand_text_to_size(body_text, max(1, target_size_bytes // max(page_count, 1)))

    objects: list[bytes] = []

    def add_object(data: str) -> int:
        objects.append(data.encode("latin-1", errors="ignore"))
        return len(objects)

    catalog_id = add_object("<< /Type /Catalog /Pages 2 0 R >>")
    pages_placeholder_id = add_object("<< /Type /Pages /Kids [] /Count 0 >>")
    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_ids: list[int] = []

    for page_index in range(page_count):
        lines = [
            f"{title} Page {page_index + 1}",
            body_text,
            "semantic retrieval distributed systems scalability queue worker",
            "docker compose minio qdrant redis postgresql concurrency testing",
            "software engineering refactoring performance optimization search",
        ]
        text_commands = ["BT", "/F1 10 Tf", "72 750 Td"]
        for line_index, line in enumerate(lines):
            escaped_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if line_index == 0:
                text_commands.append(f"({escaped_line}) Tj")
            else:
                text_commands.append(f"0 -14 Td ({escaped_line}) Tj")
        text_commands.append("ET")
        stream = "\n".join(text_commands)
        content_id = add_object(
            f"<< /Length {len(stream.encode('latin-1', errors='ignore'))} >>\nstream\n{stream}\nendstream"
        )
        page_id = add_object(
            "<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    objects[pages_placeholder_id - 1] = (
        "<< /Type /Pages "
        f"/Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] "
        f"/Count {len(page_ids)} >>"
    ).encode("latin-1")

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


class ApiSeeder:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _request(
        self,
        path: str,
        method: str = "GET",
        data: bytes | None = None,
        headers: dict | None = None,
        timeout: int = 120,
    ) -> tuple[int, str]:
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers or {},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
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

    def signup_and_login(self, username_prefix: str, password: str) -> dict:
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

        return {
            "username": username,
            "password": password,
            "token": login_body["token"],
            "user_id": login_body["user_id"],
        }

    def upload_pdf(self, token: str, filename: str, content: bytes) -> tuple[int, dict]:
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
        status, response_body = self._request("/documents", method="POST", data=body, headers=headers)
        return status, json.loads(response_body)

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
