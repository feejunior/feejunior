import os
import datetime
import requests
from dateutil import relativedelta

GRAPHQL_URL = "https://api.github.com/graphql"


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
        repositories(first: 100, ownerAffiliation: OWNER, isFork: false) {
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


def render_svg(template_path, output_path, stats):
    with open(template_path, "r", encoding="utf-8") as f:
        svg = f.read()
    svg = svg.replace("{{COMMITS}}", str(stats["commits"]))
    svg = svg.replace("{{REPOS}}", str(stats["repos"]))
    svg = svg.replace("{{STARS}}", str(stats["stars"]))
    svg = svg.replace("{{FOLLOWERS}}", str(stats["followers"]))
    svg = svg.replace("{{ACCOUNT_AGE}}", stats["account_age"])
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)


def main():
    token = os.environ["GITHUB_TOKEN"]
    username = os.environ["GH_USERNAME"]
    stats = get_account_stats(username, token)
    render_svg("templates/dark_mode.svg", "dark_mode.svg", stats)
    render_svg("templates/light_mode.svg", "light_mode.svg", stats)
    print(stats)


if __name__ == "__main__":
    main()
