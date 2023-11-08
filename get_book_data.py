#!/usr/bin/env python3

import base64
import datetime
import io
import json
import os
import re

import bs4
import httpx
import hyperlink
import keyring
import mechanize
import tqdm
from unidecode import unidecode
from PIL import Image

from concurrently import concurrently


def isLoginForm(form):
    return form.attrs.get("id") == "frmLogin"


def get_all_books_in_default_list(browser, *, base_url, username, password):
    browser.open(base_url).read()

    browser.select_form(predicate=isLoginForm)
    browser.set_value(username, name="BRWLID")
    browser.set_value(password, name="BRWLPWD")
    browser.submit().read()

    browser.follow_link(text="Dashboard").read()
    browser.follow_link(text="View all saved lists").read()
    response = browser.follow_link(text="Default").read()

    while True:
        soup = bs4.BeautifulSoup(response, "html.parser")

        result_list = soup.find("div", attrs={"id": "result-content-list"})

        yield from result_list.find_all("fieldset")

        pagination_nav = soup.find("nav", attrs={"class": "result-pages-prvnxt"})

        try:
            next_page = next(
                anchor
                for anchor in pagination_nav.find_all("a")
                if "Next page of search results" in anchor.text
            )

            response = browser.open(base_url + next_page.attrs["href"])
        except StopIteration:
            break


def slugify(u):
    """Convert Unicode string into blog slug.

    From https://leancrew.com/all-this/2014/10/asciifying/
    """
    u = re.sub("[–—/:;,.]", "-", u)  # replace separating punctuation
    a = unidecode(u).lower()  # best ASCII substitutions, lowercased
    a = re.sub(r"[^a-z0-9 -]", "", a)  # delete any other characters
    a = a.replace(" ", "-")  # spaces to hyphens
    a = re.sub(r"-+", "-", a)  # condense repeated hyphens
    return a


def save_image_locally(fieldset_soup):
    """
    Downloads a local copy of an image, and returns the path.
    """
    image_url = fieldset_soup.find("img").attrs["longdesc"]
    url = hyperlink.URL.from_text(image_url)

    # We're going to save it to the 'covers' directory, which is gitignore'd.
    # We don't know if the image is a PNG or a JPEG yet, so look for
    # a file with a matching ISBN in the directory -- that's what we want.
    os.makedirs("covers", exist_ok=True)

    try:
        isbn = url.get("ISBN")[0]
        existing_image = next(p for p in os.listdir("covers") if p.startswith(isbn))
        return os.path.join("covers", existing_image)
    except (IndexError, StopIteration) as e:
        pass

    # By default the library website returns a small image, but we can futz
    # with the query parameters to get a large image.
    url = url.set("SIZE", "l")  # SIZE=s => small, SIZE=l => large
    image_resp = httpx.get(str(url), follow_redirects=True)

    # Note: we assume the URl will be something like
    #
    #     http://www.bibdsl.co.uk/bds-images/l/123456/1234567890.jpg
    #
    # and use the final part as a basis for the filename.
    out_path = os.path.join("covers", os.path.basename(image_resp.url.path))

    if os.path.basename(image_resp.url.path) == "blank.gif":
        return

    with open(out_path, "wb") as out_file:
        out_file.write(image_resp.content)

    return out_path


def get_book_info(fieldset, *, base_url, browser):
    body = fieldset.find("div", attrs={"class": "card-body"})
    anchor_tag = body.find("a")
    relative_link = anchor_tag.attrs["href"]
    title = anchor_tag.find("span").text

    image = save_image_locally(fieldset)

    details = fieldset.find("div", attrs={"class": "recdetails"})
    author = details.find("span", attrs={"class": "d-block"}).text

    year = next(
        s.text
        for s in details.find_all("span", attrs={"class": "d-block"})
        if s.text.isnumeric()
    )

    try:
        summary = fieldset.find("div", attrs={"class": "summary"}).text
    except AttributeError:
        summary = ""

    availability = (
        fieldset.find("div", attrs={"class": "availability"}).find("a").attrs["href"]
    )

    availability_resp = browser.open(base_url + availability).read()

    availability_info = list(get_availability_info(availability_resp))

    return {
        "image": image,
        "title": title,
        "author": author,
        "url": base_url + relative_link,
        "summary": summary,
        "year": year,
        "availability_info": availability_info,
    }


def get_availability_info(html):
    soup = bs4.BeautifulSoup(html, "html.parser")

    # There's a table with four columns:
    # Location/Collection/Call number/Status
    #
    # I'm mainly interested in location and status
    for row in soup.find("table").find("tbody").find_all("tr"):
        fields = [
            ("location", "Location"),
            ("collection", "Collection"),
            ("status", "Status/Desc"),
            ("call_number", "Call number"),
        ]

        info = {
            key: row.find("td", attrs={"data-caption": caption}).text
            if row.find("td", attrs={"data-caption": caption})
            else ""
            for (key, caption) in fields
        }

        if "(Hertfordshire County Council)" not in info["location"]:
            continue

        info["location"] = info["location"].replace(
            " (Hertfordshire County Council)", ""
        )

        yield info


if __name__ == "__main__":
    if os.environ.get("CI") == "true":
        username = os.environ["LIBRARY_CARD_NUMBER"]
        password = os.environ["LIBRARY_CARD_PASSWORD"]
    else:
        username = keyring.get_password("library", "username")
        password = keyring.get_password("library", "password")

    base_url = "https://herts.spydus.co.uk"

    browser = mechanize.Browser()
    browser.set_handle_robots(False)
    browser.set_handle_redirect(True)
    browser.set_handle_refresh(
        mechanize._http.HTTPRefreshProcessor(), max_time=1, honor_time=True
    )

    fieldsets = list(
        get_all_books_in_default_list(
            browser, base_url=base_url, username=username, password=password
        )
    )

    books = [
        book
        for (_, book) in tqdm.tqdm(
            concurrently(
                lambda fs: get_book_info(fs, browser=browser, base_url=base_url),
                fieldsets,
            ),
            total=len(fieldsets),
        )
    ]

    with open("books.json", "w") as out_file:
        out_file.write(
            json.dumps(
                {"generated_at": datetime.datetime.now().isoformat(), "books": books},
                indent=2,
                sort_keys=True,
            )
        )
