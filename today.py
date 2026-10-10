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


def get_repos(username, affiliations, token):
    query = """
    query($login: String!, $affiliations: [RepositoryAffiliation], $cursor: String) {
      user(login: $login) {
        repositories(first: 100, after: $cursor, ownerAffiliations: $affiliations) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes { nameWithOwner stargazerCount }
        }
      }
    }
    """
    repos = []
    cursor = None
    while True:
        variables = {"login": username, "affiliations": affiliations, "cursor": cursor}
        page = run_query(query, variables, token)["data"]["user"]["repositories"]
        repos += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            return page["totalCount"], repos
        cursor = page["pageInfo"]["endCursor"]


def get_account_stats(username, token):
    query = """
    query($login: String!) {
      user(login: $login) {
        id
        createdAt
        followers { totalCount }
      }
    }
    """
    data = run_query(query, {"login": username}, token)["data"]["user"]
    owned_count, owned = get_repos(username, ["OWNER"], token)
    contributed_count, contributed = get_repos(username, ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"], token)
    total_commits = loc_add = loc_del = 0
    for repo in contributed:
        owner, name = repo["nameWithOwner"].split("/")
        commits, additions, deletions = get_repo_history(owner, name, data["id"], token)
        total_commits += commits
        loc_add += additions
        loc_del += deletions
    created_at = datetime.datetime.strptime(data["createdAt"], "%Y-%m-%dT%H:%M:%SZ")
    account_age = relativedelta.relativedelta(datetime.datetime.utcnow(), created_at)
    return {
        "commits": total_commits,
        "repos": owned_count,
        "contributed": contributed_count,
        "stars": sum(repo["stargazerCount"] for repo in owned),
        "followers": data["followers"]["totalCount"],
        "loc_add": loc_add,
        "loc_del": loc_del,
        "account_age": f"{account_age.years} years, {account_age.months} months, {account_age.days} days",
    }


def fmt(number):
    return f"{number:,}".replace(",", ".")


def read_ascii():
    if not os.path.exists(ASCII_FILE):
        return []
    with open(ASCII_FILE, "r", encoding="utf-8") as f:
        return [line.rstrip("\n").rstrip("\r") for line in f]


def build_info(stats):
    profile = PROFILE[:2] + [("Uptime", stats["account_age"])] + PROFILE[2:]
    github = [
        ("pair",
         ("Repos", [(fmt(stats["repos"]), "value"), (" {", None), ("Contributed", "key"), (": ", None),
                    (fmt(stats["contributed"]), "value"), ("}", None)]),
         ("Stars", fmt(stats["stars"]))),
        ("pair", ("Commits", fmt(stats["commits"])), ("Followers", fmt(stats["followers"]))),
        ("item", "Lines of Code on GitHub", [
            (fmt(stats["loc_add"] - stats["loc_del"]), "value"), (" ( ", None),
            (fmt(stats["loc_add"]), "add"), ("++", "add"), (", ", None),
            (fmt(stats["loc_del"]), "del"), ("--", "del"), (" )", None),
        ]),
    ]
    info = [("header", HOSTNAME)]
    info += [("item", key, value) for key, value in profile]
    for title, rows in (("Contact", [("item", k, v) for k, v in CONTACT]), ("GitHub Stats", github)):
        info.append(("blank",))
        info.append(("title", f"- {title}"))
        info += rows
    return info


def as_segments(value):
    return value if isinstance(value, list) else [(value, "value")]


def seg_len(value):
    return sum(len(text) for text, _ in as_segments(value))


def render_segments(value):
    return "".join(
        f'<tspan class="{cls}">{escape(text)}</tspan>' if cls else escape(text)
        for text, cls in as_segments(value)
    )


def render_cell(key, value, width, prefix):
    # prefix + key + ":" + " " + dots + " " + value == width
    dots = "." * max(1, width - len(prefix) - len(key) - seg_len(value) - 3)
    return (
        f'<tspan class="dots">{prefix}</tspan>' if prefix else ""
    ) + f'<tspan class="key">{escape(key)}</tspan>:<tspan class="dots"> {dots} </tspan>' + render_segments(value)


def cell_min(key, value, prefix):
    return len(prefix) + len(key) + seg_len(value) + 4


def build_svg(theme, art_lines, info):
    c = THEMES[theme]
    art_cols = max((len(line) for line in art_lines), default=0)
    items = [row for row in info if row[0] == "item"]
    pairs = [row for row in info if row[0] == "pair"]
    left_w = max([cell_min(*row[1], ". ") + 2 for row in pairs], default=0)
    right_w = max([cell_min(*row[2], "") + 1 for row in pairs], default=0)
    line_chars = max(
        [LINE_CHARS, left_w + 3 + right_w]
        + [cell_min(row[1], row[2], ". ") + 2 for row in items]
    )
    right_w = line_chars - left_w - 3
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
        if kind in ("header", "title"):
            # title keeps the plain text color so it stands out from the orange keys
            rule = "-" + "\u2014" * max(3, line_chars - len(row[1]) - 3) + "-"
            out.append(f'<tspan x="{info_x}" y="{y}">{escape(row[1])}</tspan> {rule}')
        elif kind == "item":
            out.append(f'<tspan x="{info_x}" y="{y}"></tspan>' + render_cell(row[1], row[2], line_chars, ". "))
        elif kind == "pair":
            out.append(
                f'<tspan x="{info_x}" y="{y}"></tspan>'
                + render_cell(*row[1], left_w, ". ")
                + " | "
                + render_cell(*row[2], right_w, "")
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
    
