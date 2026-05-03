#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_API_BASE_URL = "https://api.github.com"
TOKEN_ENV_NAMES = ("GITHUB_TOKEN", "GH_TOKEN", "GH_SOURCE_PAT")
GENERATED_FIELDNAMES = (
    "Collaborators_Count_Actual",
    "Collaborators",
    "Direct_Assign_Collaborators_Count",
    "Direct_Assign_Collaborators",
    "Collaborator_Inventory_Error",
    "direct_collaborators",
    "all_collaborators",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enrich a GitHub repository inventory CSV with collaborator information."
    )
    parser.add_argument(
        "csv_file",
        help="Repository inventory CSV path. The CSV must include Org_Name and Repo_Name columns.",
    )
    parser.add_argument(
        "--output",
        help="Output CSV path. Defaults to <input-file-stem>-updated.csv in the same folder.",
    )
    parser.add_argument(
        "--token",
        help="GitHub token. Defaults to GITHUB_TOKEN, GH_TOKEN, or GH_SOURCE_PAT environment variables.",
    )
    parser.add_argument(
        "--api-base-url",
        default=DEFAULT_API_BASE_URL,
        help="GitHub REST API base URL. Use https://api.github.com for GitHub.com.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP request timeout in seconds. Default: 30.",
    )
    parser.add_argument(
        "--wait-rate-limit",
        action="store_true",
        help="Wait until GitHub rate limit reset instead of recording an error when the limit is exhausted.",
    )
    return parser.parse_args()


def resolve_token(cli_token: str | None) -> str:
    if cli_token:
        return cli_token

    for env_name in TOKEN_ENV_NAMES:
        token = os.getenv(env_name)
        if token:
            return token

    raise SystemExit(
        "找不到 GitHub token。請使用 --token，或設定 GITHUB_TOKEN、GH_TOKEN、GH_SOURCE_PAT 其中之一。"
    )


def build_session(token: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-migration-guide-collaborator-inventory",
        }
    )

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def default_output_path(csv_path: Path) -> Path:
    return csv_path.with_name(f"{csv_path.stem}-updated{csv_path.suffix}")


def collaborator_payload(user: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "login": user.get("login"),
        "role_name": user.get("role_name"),
    }
    return {key: value for key, value in payload.items() if value is not None}


def request_page(
    session: requests.Session,
    url: str,
    params: dict[str, Any],
    timeout: int,
    wait_rate_limit: bool,
) -> requests.Response:
    while True:
        response = session.get(url, params=params, timeout=timeout)
        rate_limit_remaining = response.headers.get("x-ratelimit-remaining")
        rate_limit_reset = response.headers.get("x-ratelimit-reset")

        if (
            response.status_code == 403
            and rate_limit_remaining == "0"
            and wait_rate_limit
            and rate_limit_reset
        ):
            reset_at = int(rate_limit_reset)
            sleep_seconds = max(reset_at - int(time.time()) + 5, 1)
            print(
                f"GitHub API rate limit exhausted. Waiting {sleep_seconds} seconds before retrying.",
                file=sys.stderr,
            )
            time.sleep(sleep_seconds)
            continue

        return response


def fetch_collaborators(
    session: requests.Session,
    api_base_url: str,
    organization: str,
    repository: str,
    timeout: int,
    wait_rate_limit: bool,
    affiliation: str | None = None,
) -> list[dict[str, Any]]:
    encoded_org = quote(organization, safe="")
    encoded_repo = quote(repository, safe="")
    url = f"{api_base_url.rstrip('/')}/repos/{encoded_org}/{encoded_repo}/collaborators"
    page = 1
    collaborators: list[dict[str, Any]] = []

    while True:
        params: dict[str, Any] = {"per_page": 100, "page": page}
        if affiliation:
            params["affiliation"] = affiliation

        response = request_page(session, url, params, timeout, wait_rate_limit)
        if not response.ok:
            error_detail = response.text.strip().replace("\n", " ")
            raise RuntimeError(f"HTTP {response.status_code}: {error_detail}")

        page_items = response.json()
        if not isinstance(page_items, list):
            raise RuntimeError(f"Unexpected GitHub API response: {page_items}")

        collaborators.extend(collaborator_payload(item) for item in page_items)

        if "next" not in response.links:
            break

        page += 1

    return collaborators


def validate_columns(fieldnames: list[str] | None) -> list[str]:
    if not fieldnames:
        raise SystemExit("CSV 缺少 header row。")

    required_columns = {"Org_Name", "Repo_Name"}
    missing_columns = sorted(required_columns - set(fieldnames))
    if missing_columns:
        missing_columns_text = ", ".join(missing_columns)
        raise SystemExit(f"CSV 缺少必要欄位：{missing_columns_text}")

    return fieldnames


def enrich_rows(
    rows: list[dict[str, str]],
    session: requests.Session,
    api_base_url: str,
    timeout: int,
    wait_rate_limit: bool,
) -> list[dict[str, str]]:
    total_rows = len(rows)

    for index, row in enumerate(rows, start=1):
        organization = (row.get("Org_Name") or "").strip()
        repository = (row.get("Repo_Name") or "").strip()
        print(f"[{index}/{total_rows}] Fetching collaborators for {organization}/{repository}", file=sys.stderr)

        try:
            collaborators = fetch_collaborators(
                session,
                api_base_url,
                organization,
                repository,
                timeout,
                wait_rate_limit,
            )
            direct_collaborators = fetch_collaborators(
                session,
                api_base_url,
                organization,
                repository,
                timeout,
                wait_rate_limit,
                affiliation="direct",
            )

            row["direct_collaborators"] = json.dumps(direct_collaborators, ensure_ascii=False, separators=(",", ":"))
            row["all_collaborators"] = json.dumps(collaborators, ensure_ascii=False, separators=(",", ":"))
        except Exception as error:
            row["direct_collaborators"] = "[]"
            row["all_collaborators"] = "[]"
            print(f"  Error: {error}", file=sys.stderr)

    return rows


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv_file).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve() if args.output else default_output_path(csv_path)
    token = resolve_token(args.token)
    session = build_session(token)

    with csv_path.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        original_fieldnames = validate_columns(reader.fieldnames)
        rows = list(reader)

    added_fieldnames = [
        "direct_collaborators",
        "all_collaborators",
    ]
    original_fieldnames = [name for name in original_fieldnames if name not in GENERATED_FIELDNAMES]
    fieldnames = original_fieldnames + added_fieldnames

    enriched_rows = enrich_rows(rows, session, args.api_base_url, args.timeout, args.wait_rate_limit)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(enriched_rows)

    print(f"Updated CSV written to: {output_path}")


if __name__ == "__main__":
    main()