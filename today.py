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
    "dark": {"bg": "#161b22", "text": "#c9d1d9", "key": "#ffa657", "value": "#a5d6ff", "dots": "#616e7f"},
    "light": {"bg": "#f6f8fa", "text": "#24292f", "key": "#953800", "value": "#0a3069", "dots": "#8c959f"},
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


def get_account_stats(username, token):
    query = """
    query($login: String!) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          totalCount
          nodes { stargazerCount }
        }
        contributionsCollection {
          contributionCalendar { totalContributions }
        }
      }
    }
    """
    data = run_query(query, {"login": username}, token)["data"]["user"]
    total_stars = sum(repo["stargazerCount"] for repo in data["repositories"]["nodes"])
    created_at = datetime.datetime.strptime(data["createdAt"], "%Y-%m-%dT%H:%M:%SZ")
    account_age = relativedelta.relativedelta(datetime.datetime.utcnow(), created_at)
    return {
        "commits": data["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "repos": data["repositories"]["totalCount"],
        "stars": total_stars,
        "followers": data["followers"]["totalCount"],
        "account_age": f"{account_age.years} anos, {account_age.months} meses",
    }


def read_ascii():
    if not os.path.exists(ASCII_FILE):
        return []
    with open(ASCII_FILE, "r", encoding="utf-8") as f:
        return [line.rstrip("\n").rstrip("\r") for line in f]


def build_info(stats):
    github = [
        ("Uptime", stats["account_age"]),
        ("Repos", str(stats["repos"])),
        ("Commits (ano)", str(stats["commits"])),
        ("Stars", str(stats["stars"])),
        ("Seguidores", str(stats["followers"])),
    ]
    info = [("header", HOSTNAME)]
    for title, items in (("felipe@junior", PROFILE), ("GitHub", github), ("CONTACT", CONTACT)):
        info.append(("blank",))
        info.append(("title", title))
        for key, value in items:
            info.append(("item", key, value))
    return info


def build_svg(theme, art_lines, info):
    c = THEMES[theme]
    art_cols = max((len(line) for line in art_lines), default=0)
    info_x = int(15 + art_cols * CHAR_W + 30)
    width = int(info_x + LINE_CHARS * CHAR_W + 15)
    rows = max(len(art_lines), len(info))
    height = rows * LINE_HEIGHT + 30

    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="{FONT}" width="{width}px" height="{height}px" font-size="16px">',
        "<style>",
        f".key {{fill: {c['key']};}}",
        f".value {{fill: {c['value']};}}",
        f".dots {{fill: {c['dots']};}}",
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
            fill = "-" * max(3, LINE_CHARS - len(row[1]) - 1)
            out.append(f'<tspan x="{info_x}" y="{y}">{escape(row[1])}</tspan> <tspan class="dots">{fill}</tspan>')
        elif kind == "title":
            fill = "-" * max(3, LINE_CHARS - len(row[1]) - 3)
            out.append(f'<tspan x="{info_x}" y="{y}" class="key">- {escape(row[1])}</tspan> <tspan class="dots">{fill}</tspan>')
        elif kind == "item":
            key, value = row[1], row[2]
            dots = "." * max(2, LINE_CHARS - len(key) - len(value) - 5)
            out.append(
                f'<tspan x="{info_x}" y="{y}" class="dots">. </tspan>'
                f'<tspan class="key">{escape(key)}</tspan>:'
                f'<tspan class="dots"> {dots} </tspan>'
                f'<tspan class="value">{escape(value)}</tspan>'
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
    
