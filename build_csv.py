"""Builds the GameBoost item-offer upload CSVs from data/listings.json.

Image links point at the banners in this repo, so they work as soon as the
repo is public on GitHub. Run by the "Build upload CSV" workflow.
"""
import csv
import json
import os

REPO = os.environ.get("GITHUB_REPOSITORY", "YOUR-GITHUB-NAME/bst-autopilot")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
IMG = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/banners/{{}}.png"

HEADER = ["external_id", "slug", "title", "description", "price", "stock", "min_quantity",
          "delivery_method", "delivery_time_duration", "delivery_time_unit", "delivery_instructions",
          "image_url", "is_featured", "data_capital_hall_count", "data_clan_league",
          "data_clan_level", "data_clan_points_count"]


def row(item):
    return {
        "external_id": item["external_id"], "slug": item["slug"], "title": item["title"],
        "description": item["description"], "price": f'{item["price"]:.2f}', "stock": item["stock"],
        "min_quantity": 1, "delivery_method": "", "delivery_time_duration": item["delivery_hours"],
        "delivery_time_unit": "hours", "delivery_instructions": item["delivery_instructions"],
        "image_url": IMG.format(item["banner"]), "is_featured": "false",
        "data_capital_hall_count": 1, "data_clan_league": "Unranked", "data_clan_level": 1,
        "data_clan_points_count": 1,
    }


def write(path, items):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(row(i) for i in items)
    print(f"{path}: {len(items)} listings")


def main():
    items = json.load(open("data/listings.json", encoding="utf-8"))
    os.makedirs("output", exist_ok=True)
    write("output/upload-approved.csv", [i for i in items if i["status"] == "approved"])
    write("output/upload-all.csv", items)


if __name__ == "__main__":
    main()
