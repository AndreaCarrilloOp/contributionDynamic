"""GitHub GraphQL contribution calendar collector."""

import json
from datetime import date
from urllib.request import Request, urlopen

from contribution_dynamic.calendar import Day

QUERY = """
query Calendar($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount weekday contributionLevel } }
      }
    }
  }
}
"""

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


def parse_calendar(payload: dict) -> tuple[Day, ...]:
    if payload.get("errors"):
        raise ValueError("GitHub GraphQL returned errors")
    user = payload["data"]["user"]
    if user is None:
        raise ValueError("GitHub user not found")
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    return tuple(
        Day(
            date.fromisoformat(d["date"]),
            d["contributionCount"],
            d["weekday"],
            w,
            LEVELS.get(d.get("contributionLevel")),
        )
        for w, week in enumerate(weeks)
        for d in week["contributionDays"]
    )


def collect(login: str, token: str) -> tuple[Day, ...]:
    if not token.strip():
        raise ValueError("Set GITHUB_TOKEN before fetching contributions")
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    request = Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "contributionDynamic",
        },
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return parse_calendar(json.load(response))
