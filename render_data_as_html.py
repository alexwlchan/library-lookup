#!/usr/bin/env python3

import collections
import datetime
import json
import os
import re
import shutil

import jinja2
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image

from tint_colors import choose_tint_color_for_file, from_hex


def display_author_name(label):
    """
    Convert an author name from Spydus into something to display
    on the page.

    See the tests for examples.
    """
    # Remove years of life from the end of the label, e.g.
    #
    #     Kawaguchi, Toshikazu, 1971-
    #     Le Guin, Ursula K., 1929-2018
    #
    label = re.sub(r", [0-9]{4}\-(?:[0-9]{4})?$", "", label)

    try:
        last_name, first_name = label.split(",")
    except ValueError:
        return label

    # Remove any trailing descriptions from the first name, e.g.
    #
    #     Claire (Journalist)
    #     Justin (Comic book writer)
    #
    first_name = re.sub(r" \([A-Za-z ]+\)$", "", first_name)

    return f"{first_name.strip()} {last_name.strip()}"


def rgba(hs, opacity):
    r, g, b = from_hex(hs)
    return f"rgba({r}, {g}, {b}, {opacity})"


if __name__ == "__main__":
    book_data = json.load(open("books.json"))

    # Get a tally of all the branches in the Hertfordshire network
    branches = set()
    for book in book_data["books"]:
        for av in book["availability"]:
            if av["status"] == "Available":
                branches.add(av["location"])

    # Get a tally of all the (title, author_name) pairs
    unique_titles = collections.Counter()

    for book in book_data["books"]:
        unique_titles[(book["title"], book["author"])] += 1

    # Set up the Jinja environment
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(),
        undefined=jinja2.StrictUndefined,
    )

    env.filters["author_name"] = display_author_name
    env.filters["rgba"] = rgba

    template = env.get_template("books_to_read.html")

    os.makedirs("_html", exist_ok=True)

    for b in book_data["books"]:
        if b["image"]:
            b["tint_color"] = choose_tint_color_for_file(b["image"])

            im = Image.open(b["image"])

            b["image_width"] = im.width
            b["image_height"] = im.height

        if "pbk" in b["record_details"].get("ISBN", ""):
            b["format"] = "paperback"
        elif "hbk" in b["record_details"].get("ISBN", ""):
            b["format"] = "hardback"
        else:
            b["format"] = None

    with open("_html/index.html", "w") as outfile:
        outfile.write(
            template.render(
                books=book_data["books"],
                branches=branches,
                unique_titles=unique_titles,
                generated_at=datetime.datetime.fromisoformat(book_data["generated_at"]),
            )
        )

    os.makedirs("_html/covers", exist_ok=True)

    for f in os.listdir("covers"):
        shutil.copyfile(os.path.join("covers", f), os.path.join("_html/covers", f))

    shutil.copyfile("assets/library_lookup.js", "_html/library_lookup.js")
    shutil.copyfile("assets/style.css", "_html/style.css")
    shutil.copyfile("assets/apple-touch-icon.png", "_html/apple-touch-icon.png")
