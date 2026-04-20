import argparse
import os
import subprocess
from pathlib import Path


def run(command: list[str], env: dict | None = None) -> None:
    print("$", " ".join(command))
    subprocess.run(command, check=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run baseline Locust scenarios and summarize the results.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--users", type=int, default=4)
    parser.add_argument("--spawn-rate", type=int, default=4)
    parser.add_argument("--duration", default="30s")
    parser.add_argument("--output-dir", default="loadtests/results")
    parser.add_argument("--password", default="LocustLoadTestPass123!")
    parser.add_argument("--upload-size-mb", type=int, default=1)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    seed_dir = output_dir / "locust_seed"

    run(
        [
            "python3",
            "-m",
            "loadtests.seed_data",
            "--base-url",
            args.base_url,
            "--output-dir",
            str(seed_dir),
            "--upload-users",
            str(max(args.users * 2, 8)),
            "--search-users",
            str(max(args.users * 2, 8)),
            "--password",
            args.password,
        ]
    )

    env = os.environ.copy()
    env["LOADTEST_UPLOAD_USERS_FILE"] = str(seed_dir / "upload_users.json")
    env["LOADTEST_SEARCH_USERS_FILE"] = str(seed_dir / "search_users.json")
    env["LOADTEST_MIXED_USERS_FILE"] = str(seed_dir / "search_users.json")
    env["LOCUST_UPLOAD_SIZE_MB"] = str(args.upload_size_mb)

    scenarios = [
        ("uploads", output_dir / "locust_uploads"),
        ("search", output_dir / "locust_searches"),
        ("mixed", output_dir / "locust_mixed"),
    ]

    for tag, prefix in scenarios:
        env["LOCUST_SCENARIO"] = tag if tag != "uploads" else "uploads"
        run(
            [
                "locust",
                "-f",
                "loadtests/locustfile.py",
                "--headless",
                "--host",
                args.base_url,
                "-u",
                str(args.users),
                "-r",
                str(args.spawn_rate),
                "-t",
                args.duration,
                "--csv",
                str(prefix),
                "--only-summary",
            ],
            env=env,
        )

    run(
        [
            "python3",
            "-m",
            "loadtests.summarize_locust",
            "--base-url",
            args.base_url,
            "--uploads-prefix",
            str(output_dir / "locust_uploads"),
            "--search-prefix",
            str(output_dir / "locust_searches"),
            "--mixed-prefix",
            str(output_dir / "locust_mixed"),
            "--output-json",
            str(output_dir / "locust_summary.json"),
            "--output-md",
            str(output_dir / "locust_summary.md"),
        ]
    )


if __name__ == "__main__":
    main()
