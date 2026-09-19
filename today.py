import os
import datetime
from xml.sax.saxutils import escape

import requests
from dateutil import relativedelta

GRAPHQL_URL = "https://api.github.com/graphql"
FONT = "Consolas, 'DejaVu Sans Mono', monospace"
CHAR_W = 9.6
LINE_HEIGHT = 20
LINE_CHARS = 54
ASCII_FILE = "ascii.txt"
HOSTNAME = "felipe@junior"

THEMES = {
    "dark": {"bg": "#161b22", "text": "#c9d1d9", "key": "#ffa657", "value": "#a5d6ff", "dots": "#616e7f", "add": "#3fb950", "del": "#f85149"},
    "light": {"bg": "#f6f8fa", "text": "#24292f", "key": "#953800", "value": "#0a3069", "dots": "#c2cfde", "add": "#1a7f37", "del": "#cf222e"},
}

PROFILE = [
    ("Role", "Software Engineer"),
    ("Stack", "Python, Django, JavaScript, TypeScript, MySQL"),
    ("OS", "Linux, Windows"),
    ("Host", "FreeAgent"),
    ("Learning", "Java - RocketSeat"),
]

CONTACT = [
    ("Portfolio", "https://feejunior.com.br"),
    ("LinkedIn", "linkedin.com/in/feejunior"),
]


def run_query(query, variables, token):
    headers = {"Authorization": f"token {token}"}
    response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Query failed: {response.status_code} {response.text}")
    result = response.json()
    if "errors" in result:
        raise Exception(f"GraphQL errors: {result['errors']}")
    return result


def get_repo_history(owner, name, author_id, token):
    query = """
    query($owner: String!, $name: String!, $author: ID!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 100, after: $cursor, author: {id: $author}) {
                pageInfo { hasNextPage endCursor }
                nodes { additions deletions }
              }
            }
          }
        }
      }
    }
    """
    commits = additions = deletions = 0
    cursor = None
    while True:
        variables = {"owner": owner, "name": name, "author": author_id, "cursor": cursor}
        branch = run_query(query, variables, token)["data"]["repository"]["defaultBranchRef"]
        if branch is None:
            break
        history = branch["target"]["history"]
        for node in history["nodes"]:
            additions += node["additions"]
            deletions += node["deletions"]
        commits += len(history["nodes"])
        if not history["pageInfo"]["hasNextPage"]:
            break
        cursor = history["pageInfo"]["endCursor"]
    return commits, additions, deletions


def get_account_stats(username, token):
    query = """
    query($login: String!) {
      user(login: $login) {
        id
        createdAt
        followers { totalCount }
        owned: repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          totalCount
          nodes { nameWithOwner stargazerCount }
        }
        contributed: repositories(ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) {
          totalCount
        }
        contributionsCollection {
          contributionCalendar { totalContributions }
        }
      }
    }
    """
    data = run_query(query, {"login": username}, token)["data"]["user"]
    repos = data["owned"]["nodes"]
    total_commits = loc_add = loc_del = 0
    for repo in repos:
        owner, name = repo["nameWithOwner"].split("/")
        commits, additions, deletions = get_repo_history(owner, name, data["id"], token)
        total_commits += commits
        loc_add += additions
        loc_del += deletions
    created_at = datetime.datetime.strptime(data["createdAt"], "%Y-%m-%dT%H:%M:%SZ")
    account_age = relativedelta.relativedelta(datetime.datetime.utcnow(), created_at)
    return {
        "commits": data["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "commits_total": total_commits,
        "repos": data["owned"]["totalCount"],
        "contributed": data["contributed"]["totalCount"],
        "stars": sum(repo["stargazerCount"] for repo in repos),
        "followers": data["followers"]["totalCount"],
        "loc_add": loc_add,
        "loc_del": loc_del,
        "account_age": f"{account_age.years} anos, {account_age.months} meses",
    }


def fmt(number):
    return f"{number:,}".replace(",", ".")


def read_ascii():
    if not os.path.exists(ASCII_FILE):
        return []
    with open(ASCII_FILE, "r", encoding="utf-8") as f:
        return [line.rstrip("\n").rstrip("\r") for line in f]


def build_info(stats):
    github = [
        ("Uptime", stats["account_age"]),
        ("Repos", f"{fmt(stats['repos'])} (contribuídos: {fmt(stats['contributed'])})"),
        ("Commits", fmt(stats["commits_total"])),
        ("Commits (ano)", fmt(stats["commits"])),
        ("Stars", fmt(stats["stars"])),
        ("Seguidores", fmt(stats["followers"])),
        (
            "Linhas de código",
            [
                (f"{fmt(stats['loc_add'] - stats['loc_del'])} (", "value"),
                (f"+{fmt(stats['loc_add'])}", "add"),
                (", ", "value"),
                (f"-{fmt(stats['loc_del'])}", "del"),
                (")", "value"),
            ],
        ),
    ]
    info = [("header", HOSTNAME)]
    for title, items in (("felipe@junior", PROFILE), ("GitHub", github), ("CONTACT", CONTACT)):
        info.append(("blank",))
        info.append(("title", title))
        for key, value in items:
            info.append(("item", key, value))
    return info


def as_segments(value):
    return value if isinstance(value, list) else [(value, "value")]


def build_svg(theme, art_lines, info):
    c = THEMES[theme]
    art_cols = max((len(line) for line in art_lines), default=0)
    line_chars = max(
        [LINE_CHARS]
        + [len(row[1]) + sum(len(t) for t, _ in as_segments(row[2])) + 7 for row in info if row[0] == "item"]
    )
    info_x = int(15 + art_cols * CHAR_W + 30)
    width = int(info_x + line_chars * CHAR_W + 15)
    rows = max(len(art_lines), len(info))
    height = rows * LINE_HEIGHT + 30

    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="{FONT}" width="{width}px" height="{height}px" font-size="16px">',
        "<style>",
        f".key {{fill: {c['key']};}}",
        f".value {{fill: {c['value']};}}",
        f".dots {{fill: {c['dots']};}}",
        f".add {{fill: {c['add']};}}",
        f".del {{fill: {c['del']};}}",
        "text, tspan {white-space: pre;}",
        "</style>",
        f'<rect width="{width}px" height="{height}px" fill="{c["bg"]}" rx="15"/>',
    ]

    out.append(f'<text fill="{c["text"]}" xml:space="preserve">')
    for i, line in enumerate(art_lines):
        y = 30 + i * LINE_HEIGHT
        out.append(f'<tspan x="15" y="{y}">{escape(line)}</tspan>')
    out.append("</text>")

    out.append(f'<text fill="{c["text"]}" xml:space="preserve">')
    for i, row in enumerate(info):
        y = 30 + i * LINE_HEIGHT
        kind = row[0]
        if kind == "header":
            fill = "-" * max(3, line_chars - len(row[1]) - 1)
            out.append(f'<tspan x="{info_x}" y="{y}">{escape(row[1])}</tspan> <tspan class="dots">{fill}</tspan>')
        elif kind == "title":
            fill = "-" * max(3, line_chars - len(row[1]) - 3)
            out.append(f'<tspan x="{info_x}" y="{y}" class="key">- {escape(row[1])}</tspan> <tspan class="dots">{fill}</tspan>')
        elif kind == "item":
            key, value = row[1], row[2]
            segments = as_segments(value)
            length = sum(len(text) for text, _ in segments)
            dots = "." * max(2, line_chars - len(key) - length - 5)
            spans = "".join(f'<tspan class="{cls}">{escape(text)}</tspan>' for text, cls in segments)
            out.append(
                f'<tspan x="{info_x}" y="{y}" class="dots">. </tspan>'
                f'<tspan class="key">{escape(key)}</tspan>:'
                f'<tspan class="dots"> {dots} </tspan>'
                + spans
            )
    out.append("</text>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def write_svgs(stats):
    art_lines = read_ascii()
    info = build_info(stats)
    for theme in THEMES:
        with open(f"{theme}_mode.svg", "w", encoding="utf-8") as f:
            f.write(build_svg(theme, art_lines, info))


def main():
    token = os.environ["GITHUB_TOKEN"]
    username = os.environ["GH_USERNAME"]
    stats = get_account_stats(username, token)
    write_svgs(stats)
    print(stats)


if __name__ == "__main__":
    main()
    
