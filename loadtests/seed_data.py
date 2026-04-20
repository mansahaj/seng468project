import argparse
import json
from pathlib import Path

from loadtests.common import ApiSeeder, build_pdf_bytes, now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed users and documents for Locust load tests.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--output-dir", default="loadtests/results/locust_seed")
    parser.add_argument("--upload-users", type=int, default=8)
    parser.add_argument("--search-users", type=int, default=8)
    parser.add_argument("--password", default="LocustLoadTestPass123!")
    parser.add_argument("--seed-timeout", type=int, default=180)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    seeder = ApiSeeder(args.base_url)
    upload_credentials = []
    search_credentials = []

    for index in range(args.upload_users):
        creds = seeder.signup_and_login("locust_upload", args.password)
        upload_credentials.append(creds)

    seed_pdf = build_pdf_bytes(
        "Locust Search Seed",
        (
            "semantic retrieval scalability distributed systems docker compose "
            "object storage vector search qdrant minio redis postgresql"
        ),
        page_count=2,
        target_size_bytes=128 * 1024,
    )
    for index in range(args.search_users):
        creds = seeder.signup_and_login("locust_search", args.password)
        status, body = seeder.upload_pdf(
            creds["token"],
            f"locust_search_seed_{index}.pdf",
            seed_pdf,
        )
        if status != 202:
            raise RuntimeError(f"seed upload failed for {creds['username']}: {status} {body}")
        ready_status, ready_duration = seeder.wait_until_ready(
            creds["token"],
            body["document_id"],
            timeout_s=args.seed_timeout,
        )
        if ready_status != "ready":
            raise RuntimeError(
                f"seed document did not become ready for {creds['username']}: {ready_status}"
            )
        creds["seed_document_id"] = body["document_id"]
        creds["seed_ready_seconds"] = round(ready_duration, 2)
        search_credentials.append(creds)

    metadata = {
        "generated_at": now_iso(),
        "base_url": args.base_url,
        "upload_users": len(upload_credentials),
        "search_users": len(search_credentials),
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    (output_dir / "upload_users.json").write_text(json.dumps(upload_credentials, indent=2))
    (output_dir / "search_users.json").write_text(json.dumps(search_credentials, indent=2))

    print(json.dumps(metadata, indent=2))
    print(f"Wrote upload user credentials to {output_dir / 'upload_users.json'}")
    print(f"Wrote search user credentials to {output_dir / 'search_users.json'}")


if __name__ == "__main__":
    main()
