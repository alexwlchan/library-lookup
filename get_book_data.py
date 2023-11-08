#!/usr/bin/env python3

import datetime
import functools
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


def save_image_locally(img_element):
    """
    Downloads a local copy of an image, and returns the path.
    """
    image_url = img_element.attrs["longdesc"]
    url = hyperlink.URL.from_text(image_url)

    # We're going to save it to the 'covers' directory, which is gitignore'd.
    # We don't know if the image is a PNG or a JPEG yet, so look for
    # a file with a matching ISBN in the directory -- that's what we want.
    os.makedirs("covers", exist_ok=True)

    try:
        isbn = url.get("ISBN")[0]
        existing_image = next(p for p in os.listdir("covers") if p.startswith(isbn))
        return os.path.join("covers", existing_image)
    except (IndexError, StopIteration):
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


class LibraryBrowser:
    def __init__(self, *, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url
        self.browser = mechanize.Browser()

        self._configure_browser(username=username, password=password)

    def _configure_browser(self, *, username: str, password: str) -> None:
        """
        Set up the browser, and log in to the library website.
        """
        self.browser.set_handle_robots(False)
        self.browser.set_handle_redirect(True)
        self.browser.set_handle_refresh(
            mechanize._http.HTTPRefreshProcessor(), max_time=1, honor_time=True
        )

        self.browser.open(self.base_url).read()

        self.browser.select_form(
            predicate=lambda form: form.attrs.get("id") == "frmLogin"
        )
        self.browser.set_value(username, name="BRWLID")
        self.browser.set_value(password, name="BRWLPWD")
        self.browser.submit().read()

    def _get_soup(self, url: str):
        """
        Open a URL and parse the HTML with BeautifulSoup.
        """
        if url.startswith("/"):
            resp = self.browser.open(self.base_url + url)
        else:
            resp = self.browser.open(url)

        return bs4.BeautifulSoup(resp, "html.parser")

    @functools.cache
    def get_default_list(self):
        """
        Returns the URL to my default list.
        """
        # Go to the homepage
        self.browser.open(self.base_url)

        # In the top right-hand corner is a dropdown menu; one of the
        # items is a link to "Dashboard".  Click it.
        self.browser.follow_link(text="Dashboard")

        # On the left-hand side is a list of links titled "My account".
        # One of the items is a link to my saved lists.  Click it.
        resp = self.browser.follow_link(text="View all saved lists")

        # Finally, a table which has my lists.  There's only one, which
        # is titled "Default".  Make a note of the URL and the title count.
        soup = bs4.BeautifulSoup(resp, "html.parser")
        count = int(soup.find("td", attrs={"data-caption": "Titles"}).text)

        url = self.browser.find_link(text="Default").absolute_url

        return {"count": count, "url": url}

    def get_books_in_list(self, url) -> None:
        """
        Generate a list of books in a list, which is all the books
        I've marked with a bookmark icon.
        """
        # This is the first page of results, but there are more pages.
        # Go through each page in turn, and look for data about the books.
        while True:
            soup = self._get_soup(url)

            # The books on the page are stored in the following structure:
            #
            #     <div id="result-content-list" …>
            #       <fieldset class="card card-list">
            #         … info about book 1 …
            #       </fieldset>
            #       <fieldset class="card card-list">
            #         … info about book 2 …
            #       </fieldset>
            #       …
            #
            result_content_List = soup.find("div", attrs={"id": "result-content-list"})

            for fieldset in result_content_List.find_all("fieldset"):
                yield self.parse_fieldset_info(fieldset)

            # Now look for a link to the next page, if there is one.
            #
            #     <nav class="prvnxt result-pages-prvnxt">
            #       <ul class="list-inline mb-0">
            #         <li class="list-inline-item prv">Previous</li>
            #         <li class="list-inline-item nxt">
            #           <a href="/cgi-bin/spydus.exe/…">Next</a>
            #         </li>
            #
            pagination_nav = soup.find("nav", attrs={"class": "result-pages-prvnxt"})
            next_link = pagination_nav.find("li", attrs={"class": "nxt"}).find("a")

            if next_link is None:
                break

            url = next_link.attrs["href"]

    def parse_fieldset_info(self, fieldset):
        """
        Given a <fieldset> element from the list of books in a saved list,
        return all the metadata I want to extract.
        """
        title_elem = fieldset.find("h2", attrs={"class": "card-title"})
        title = title_elem.getText()

        url = title_elem.find("a").attrs["href"]
        record_details = self.get_record_details(url)

        image = save_image_locally(fieldset.find("img"))

        # The author and publication year are in a block like so:
        #
        #     <div class="card-text recdetails">
        #       <span class="d-block">Cleeves, Ann</span>
        #       <span class="d-block">2023</span>
        #     </div>
        #
        recdetail_div = fieldset.find("div", attrs={"class": "recdetails"})
        recdetail_spans = recdetail_div.find_all("span")

        if title == "Ursula K. Le Guin : voyager to inner lands and to outer space" and len(recdetail_spans) == 1:
            author = "Ursula K. Le Guin"
            title = "Voyager to Inner Lands and to Outer Space"
            publication_year = "1979"
        elif len(recdetail_spans) != 2:
            print(
                f'Unexpected data on {title}; could not find two instances of <div class="recdetails">'
            )
            author = None
            publication_year = None
        else:
            author = recdetail_spans[0].getText()
            publication_year = recdetail_spans[1].getText()

        # The summary is in a block like:
        #
        #     <div class="card-text summary">
        #       When Jem Rosco - sailor, adventurer and local legend -
        #       …
        #     </div>
        #
        # Note that not all books have a summary, in which case this
        # element is missing.
        summary_elem = fieldset.find("div", attrs={"class": "summary"})
        if summary_elem is None:
            summary = None
        else:
            summary = summary_elem.getText().strip()

        # There's a link to the availability popover:
        #
        #     <div class="card-text availability">
        #       …
        #       <a href="/cgi-bin/spydus.exe/XHLD/WPAC/…" …>
        #         View availability
        #       </a>
        #
        # That's the URL we need to open to get availability info.
        availability_elem = fieldset.find("div", attrs={"class": "availability"})
        availability_url = availability_elem.find("a").attrs["href"]
        availability = self.get_availability_info(availability_url)

        return {
            "title": title,
            "record_details": record_details,
            "image": image,
            "author": author,
            "publication_year": publication_year,
            "summary": summary,
            "availability": availability,
        }

    def get_record_details(self, url: str) -> str:
        """
        Given the URL to a book's page in the current browser session,
        get all the record details, which are shown as a table on the page.

        Of particular interest here is the bookmark link, which should work
        across sessions.  For some reason, the Spydus URLs you get when
        logged in are tied to your current session, and don't always work later.

        Sometimes you get an error like:

            Session must be logged in to display this page

        even if you're already logged in!

        I don't use much of this right now, but while I'm in this table it
        makes sense to grab it all and work out what to do with it later.
        """
        soup = self._get_soup(url)

        # This is the rough structure of the HTML that renders the
        # "Record details" table (or at least the bits we care about):
        #
        #       <div id="tabRECDETAILS-body" …>
        #         <div class="row">
        #           <div class="col-sm-3 col-md-3 fd-caption">
        #             <span>Main title:</span>
        #           </div>
        #           <div class="col pl-sm-0">
        #             <span class="d-block"><a href="/cgi-bin/spydus.exe/ENQ/…"><span>A Cuban girl's guide to tea and tomorrow</span></a> / Laura Taylor Namey.</span>
        #           </div>
        #         </div>
        #         <div class="row">
        #           <div class="col-sm-3 col-md-3 fd-caption">
        #             <span>Imprint:</span>
        #           </div>
        #           <div class="col pl-sm-0">
        #             <span class="d-block">London : Simon & Schuster, 2022.</span>
        #           </div>
        #         </div>
        #         …
        #
        rec_details_body = soup.find("div", attrs={"id": "tabRECDETAILS-body"})

        record_details = {}

        for row in rec_details_body.find_all("div", attrs={"class": "row"}):
            caption_text = row.find("div", attrs={"class": "fd-caption"}).getText()

            # Strip the trailing colon
            key = re.sub(r":$", "", caption_text.strip())

            # There may be multiple rows, e.g. "Subject" and "Dewey Class"
            value = [
                span.getText().strip()
                for span in row.find_all("span", attrs={"class": "d-block"})
            ]

            # If there's a single value and we're not expecting multiple
            # values in this field, just get the single value.
            if key not in {
                "Added title",
                "Author",
                "Dewey class",
                "Language",
                "Local class",
                "More Information",
                "Notes",
                "Series title",
                "Subject",
            }:
                if len(value) == 1:
                    value = value[0]
                else:
                    print(f"Record detail had multiple entries for {key}: {url}")

            record_details[key] = value

        return record_details

    def get_availability_info(self, availability_url):
        soup = self._get_soup(availability_url)

        availability = []

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

            availability.append(info)

        return availability


if __name__ == "__main__":
    if os.environ.get("CI") == "true":
        username = os.environ["LIBRARY_CARD_NUMBER"]
        password = os.environ["LIBRARY_CARD_PASSWORD"]
    else:
        username = keyring.get_password("library", "username")
        password = keyring.get_password("library", "password")

    browser = LibraryBrowser(
        base_url="https://herts.spydus.co.uk", username=username, password=password
    )

    default_list = browser.get_default_list()

    books = list(
        tqdm.tqdm(
            browser.get_books_in_list(url=default_list["url"]),
            total=default_list["count"],
        )
    )

    data = {"generated_at": datetime.datetime.now().isoformat(), "books": books}

    with open("books.json", "w") as out_file:
        out_file.write(json.dumps(data, indent=2, sort_keys=True))
