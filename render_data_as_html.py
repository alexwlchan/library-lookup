#!/usr/bin/env python3

import datetime
import json
import os
import secrets
import shutil

import jinja2
from jinja2 import Environment, FileSystemLoader, select_autoescape


if __name__ == "__main__":
    books = json.load(open("books.json"))

    # Get a tally of all the branches in the Hertfordshire network
    branches = set()
    for book in books:
        for av in book["availability_info"]:
            if av["status"] == "Available":
                branches.add(av["location"])

    # Set up the Jinja environment
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(),
        undefined=jinja2.StrictUndefined,
    )

    template = env.get_template("books_to_read.html")

    os.makedirs("_html", exist_ok=True)

    for b in books:
        b["id"] = str(secrets.token_hex())

    with open("_html/index.html", "w") as outfile:
        outfile.write(
            template.render(books=books, branches=branches, now=datetime.datetime.now())
        )

    os.makedirs('_html/covers', exist_ok=True)

    for f in os.listdir('covers'):
        shutil.copyfile(os.path.join('covers', f), os.path.join('_html/covers', f))

    shutil.copyfile('templates/library_lookup.js', '_html/library_lookup.js')
    shutil.copyfile('templates/style.css', '_html/style.css')
