#!/usr/bin/env python3

import datetime
import json
import os
import shutil

import jinja2
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image
import titlecase

from library_lookup.render_data_as_html import display_author_name
from tint_colors import choose_tint_color_for_file, from_hex


def rgba(hs: str, opacity: float) -> str:
    r, g, b = from_hex(hs)
    return f"rgba({r}, {g}, {b}, {opacity})"


if __name__ == "__main__":
    book_data = json.load(open("books.json"))

    for book in book_data["books"]:
        for av in list(book["availability"]):
            if av["location"].endswith(" (Hertfordshire Libraries)"):
                av["location"] = av["location"].replace(
                    " (Hertfordshire Libraries)", ""
                )
            else:
                book["availability"].remove(av)

    # Get a tally of all the branches in the Hertfordshire network
    branches = set()
    for book in book_data["books"]:
        for av in book["availability"]:
            if av["status"] == "Available":
                branches.add(av["location"])

    # Set up the Jinja environment
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(),
        undefined=jinja2.StrictUndefined,
    )

    env.filters["author_name"] = display_author_name
    env.filters["rgba"] = rgba
    env.filters["titlecase"] = titlecase.titlecase

    template = env.get_template("books_to_read.html")

    os.makedirs("_html", exist_ok=True)

    for b in book_data["books"]:
        if b["image"]:
            if b["image"]["path"] is not None:
                b["tint_color"] = choose_tint_color_for_file(path=b["image"]["path"])

                im = Image.open(b["image"]["path"])

                b["image_width"] = im.width
                b["image_height"] = im.height

        if "pbk" in b["record_details"].get("ISBN", ""):
            b["format"] = "paperback"
        elif "hbk" in b["record_details"].get("ISBN", ""):
            b["format"] = "hardback"
        else:
            b["format"] = None

    # with open('book_data.json', 'x') as of:
    #     of.write(json.dumps(book_data, indent=2, sort_keys=True))

    with open("_html/index.html", "w") as outfile:
        outfile.write(
            template.render(
                books=book_data["books"],
                branches=branches,
                generated_at=datetime.datetime.fromisoformat(book_data["generated_at"]),
            )
        )

    os.makedirs("_html/covers", exist_ok=True)

    for f in os.listdir("covers"):
        shutil.copyfile(os.path.join("covers", f), os.path.join("_html/covers", f))

    shutil.copyfile("assets/library_lookup.js", "_html/library_lookup.js")
    shutil.copyfile("assets/style.css", "_html/style.css")
    shutil.copyfile("assets/apple-touch-icon.png", "_html/apple-touch-icon.png")
    shutil.copyfile("books.json", "_html/books.json")
