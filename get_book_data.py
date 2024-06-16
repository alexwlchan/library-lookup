#!/usr/bin/env python3

from collections.abc import Iterable
import datetime
import functools
import json
import os
import sys
import typing
from urllib.error import HTTPError, URLError

import bs4
import certifi
import httpx
import hyperlink
import keyring
import mechanize
from tenacity import retry, stop_after_attempt, wait_exponential
import tqdm

from library_lookup.parsers import (
    AvailabilityInfo,
    RecordDetails,
    get_url_of_next_page,
    parse_availability_info,
    parse_record_details,
)


def save_image_locally(img_element: bs4.Tag) -> str | None:
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
        assert isinstance(isbn, str)

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
        return None

    with open(out_path, "wb") as out_file:
        out_file.write(image_resp.content)

    return out_path


def is_retryable(exc: Exception) -> bool:
    if isinstance(exc, URLError):
        return True

    if isinstance(exc, HTTPError) and exc.code >= 500:
        return True

    return False


class DefaultList(typing.TypedDict):
    count: int
    url: str


class FieldsetInfo(typing.TypedDict):
    title: str
    record_details: RecordDetails
    image: str | None
    author: str | None
    publication_year: str | None
    availability: list[AvailabilityInfo]


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

        # This is necessary to avoid errors like:
        #
        #     urllib.error.URLError:
        #     <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate
        #     verify failed: unable to get local issuer certificate
        #     (_ssl.c:1000)>
        #
        self.browser.set_ca_data(cafile=certifi.where())

        self.browser.open(self.base_url).read()

        self.browser.select_form(
            predicate=lambda form: form.attrs.get("id") == "frmLogin"
        )
        self.browser.set_value(username, name="BRWLID")
        self.browser.set_value(password, name="BRWLPWD")
        self.browser.submit().read()

    @retry(
        stop=stop_after_attempt(5),
        retry=is_retryable,  # type: ignore
        wait=wait_exponential(multiplier=1, min=1, max=15),
    )
    def _get_soup(self, url: str) -> bs4.BeautifulSoup:
        """
        Open a URL and parse the HTML with BeautifulSoup.
        """
        if url.startswith("/"):
            resp = self.browser.open(self.base_url + url)
        else:
            resp = self.browser.open(url)

        return bs4.BeautifulSoup(resp, "html.parser")

    @functools.cache
    def get_default_list(self) -> DefaultList:
        """
        Return some basic info about my default list, including the
        URL and number of titles.
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

        titles_elem = soup.find("td", attrs={"data-caption": "Titles"})
        assert titles_elem is not None
        count = int(titles_elem.text)

        url = self.browser.find_link(text="Default").absolute_url

        return {"count": count, "url": url}

    def get_pages_in_list(self, url: str) -> Iterable[bs4.BeautifulSoup]:
        """
        Given a paginated list, fetch each page of the list in turn
        and generate the HTML as parsed by BeautifulSoup.

            :param url: The first page of he list.

        """
        while url is not None:
            soup = self._get_soup(url)

            yield soup

            url_of_next_page = get_url_of_next_page(soup)

            if url_of_next_page is None:
                break

            url = url_of_next_page

    def get_books_in_list(self, url: str) -> Iterable[FieldsetInfo]:
        """
        Generate a list of books in a list, which is all the books
        I've marked with a bookmark icon.
        """
        for soup in self.get_pages_in_list(url):
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
            result_content_list = soup.find("div", attrs={"id": "result-content-list"})
            assert isinstance(result_content_list, bs4.Tag)

            for fieldset in result_content_list.find_all("fieldset"):
                try:
                    yield self.parse_fieldset_info(fieldset)
                except Exception:
                    print(f"Unable to get info from {fieldset!r}", file=sys.stderr)
                    raise

    def parse_fieldset_info(self, fieldset: bs4.Tag) -> FieldsetInfo:
        """
        Given a <fieldset> element from the list of books in a saved list,
        return all the metadata I want to extract.
        """
        title_elem = fieldset.find("h2", attrs={"class": "card-title"})
        assert isinstance(title_elem, bs4.Tag)
        title = title_elem.getText()

        anchor_elem = title_elem.find("a")
        assert isinstance(anchor_elem, bs4.Tag)
        url = anchor_elem.attrs["href"]

        record_details = self.get_record_details(url)

        img_elem = fieldset.find("img")
        assert isinstance(img_elem, bs4.Tag)
        image = save_image_locally(img_elem)

        # The author and publication year are in a block like so:
        #
        #     <div class="card-text recdetails">
        #       <span class="d-block">Cleeves, Ann</span>
        #       <span class="d-block">2023</span>
        #     </div>
        #
        recdetail_div = fieldset.find("div", attrs={"class": "recdetails"})
        assert isinstance(recdetail_div, bs4.Tag)
        recdetail_spans = recdetail_div.find_all("span")

        if (
            title == "Ursula K. Le Guin : voyager to inner lands and to outer space"
            and len(recdetail_spans) == 1
        ):
            author = "Ursula K. Le Guin"
            title = "Voyager to Inner Lands and to Outer Space"
            publication_year = "1979"
        elif (
            title
            == "From hurt to hope : stories of mental health, mental illness and being autistic"
            and len(recdetail_spans) == 1
        ):
            author = "Various authors"
            publication_year = "2021"
        elif len(recdetail_spans) != 2:
            print(
                f'Unexpected data on {title}; could not find two instances of <div class="recdetails">'
            )
            author = None
            publication_year = None
        else:
            author = recdetail_spans[0].getText()
            publication_year = recdetail_spans[1].getText()

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
        assert isinstance(availability_elem, bs4.Tag)

        availability_link_elem = availability_elem.find("a")
        assert isinstance(availability_link_elem, bs4.Tag)
        availability_url = availability_link_elem.attrs["href"]

        soup = self._get_soup(availability_url)

        availability = parse_availability_info(soup)

        return {
            "title": title,
            "record_details": record_details,
            "image": image,
            "author": author,
            "publication_year": publication_year,
            "availability": availability,
        }

    def get_record_details(self, url: str) -> RecordDetails:
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

        return parse_record_details(soup, url=url)


if __name__ == "__main__":
    try:
        username: str | None = os.environ["LIBRARY_CARD_NUMBER"]
        password: str | None = os.environ["LIBRARY_CARD_PASSWORD"]
    except KeyError:
        username = keyring.get_password("library", "username")
        password = keyring.get_password("library", "password")

    assert username is not None, "Could not get username!"
    assert password is not None, "Could not get password!"

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
