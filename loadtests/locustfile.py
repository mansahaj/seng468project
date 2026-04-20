import json
import os
import threading
from pathlib import Path

from locust import HttpUser, between, task

from loadtests.common import build_pdf_bytes, random_suffix

SCENARIO = os.getenv("LOCUST_SCENARIO", "uploads")
SEARCH_QUERY = os.getenv("LOCUST_SEARCH_QUERY", "semantic retrieval scalability")
UPLOAD_SIZE_MB = int(os.getenv("LOCUST_UPLOAD_SIZE_MB", "1"))
UPLOAD_FILE_BYTES = build_pdf_bytes(
    "Locust Upload Test",
    (
        "This generated PDF is used for concurrent upload load testing. "
        "It contains repeated semantic retrieval and scalability text."
    ),
    page_count=3,
    target_size_bytes=UPLOAD_SIZE_MB * 1024 * 1024,
)

UPLOAD_USERS_FILE = Path(os.getenv("LOADTEST_UPLOAD_USERS_FILE", "loadtests/results/locust_seed/upload_users.json"))
SEARCH_USERS_FILE = Path(os.getenv("LOADTEST_SEARCH_USERS_FILE", "loadtests/results/locust_seed/search_users.json"))
MIXED_USERS_FILE = Path(os.getenv("LOADTEST_MIXED_USERS_FILE", str(SEARCH_USERS_FILE)))

_LOCK = threading.Lock()
_POOLS = {}
_INDICES = {}


def load_credentials(path: Path) -> list[dict]:
    if not path.exists():
        raise RuntimeError(f"Credential file not found: {path}")
    return json.loads(path.read_text())


def next_credential(pool_name: str, path: Path) -> dict:
    with _LOCK:
        if pool_name not in _POOLS:
            _POOLS[pool_name] = load_credentials(path)
            _INDICES[pool_name] = 0
        creds = _POOLS[pool_name]
        if not creds:
            raise RuntimeError(f"No credentials available in {path}")
        index = _INDICES[pool_name] % len(creds)
        _INDICES[pool_name] += 1
        return creds[index]


class BaseTokenUser(HttpUser):
    abstract = True
    wait_time = between(0.5, 1.5)

    def assign_credential(self, pool_name: str, path: Path) -> None:
        credential = next_credential(pool_name, path)
        self.credential = credential
        self.token = credential["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

class UploadUser(BaseTokenUser):
    abstract = SCENARIO != "uploads"

    def on_start(self) -> None:
        self.assign_credential("upload", UPLOAD_USERS_FILE)

    @task
    def upload_document(self) -> None:
        files = {
            "file": (
                f"locust_upload_{random_suffix()}.pdf",
                UPLOAD_FILE_BYTES,
                "application/pdf",
            )
        }
        with self.client.post(
            "/documents",
            headers=self.headers,
            files=files,
            name="POST /documents",
            catch_response=True,
        ) as response:
            if response.status_code != 202:
                response.failure(f"expected 202, got {response.status_code}")
            else:
                response.success()

class SearchUser(BaseTokenUser):
    abstract = SCENARIO != "search"

    def on_start(self) -> None:
        self.assign_credential("search", SEARCH_USERS_FILE)

    @task
    def search_documents(self) -> None:
        with self.client.get(
            "/search",
            params={"q": SEARCH_QUERY},
            headers=self.headers,
            name="GET /search",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"expected 200, got {response.status_code}")
                return
            try:
                payload = response.json()
            except Exception as exc:
                response.failure(f"invalid JSON response: {exc}")
                return
            if not payload:
                response.failure("search returned no results for seeded query")
            else:
                response.success()

class MixedUser(BaseTokenUser):
    abstract = SCENARIO != "mixed"

    def on_start(self) -> None:
        self.assign_credential("mixed", MIXED_USERS_FILE)

    @task(2)
    def search_documents(self) -> None:
        with self.client.get(
            "/search",
            params={"q": SEARCH_QUERY},
            headers=self.headers,
            name="GET /search",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"expected 200, got {response.status_code}")
                return
            try:
                payload = response.json()
            except Exception as exc:
                response.failure(f"invalid JSON response: {exc}")
                return
            if not payload:
                response.failure("search returned no results for seeded query")
            else:
                response.success()

    @task(1)
    def upload_document(self) -> None:
        files = {
            "file": (
                f"locust_mixed_{random_suffix()}.pdf",
                UPLOAD_FILE_BYTES,
                "application/pdf",
            )
        }
        with self.client.post(
            "/documents",
            headers=self.headers,
            files=files,
            name="POST /documents",
            catch_response=True,
        ) as response:
            if response.status_code != 202:
                response.failure(f"expected 202, got {response.status_code}")
            else:
                response.success()
