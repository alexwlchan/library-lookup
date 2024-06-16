import re
import typing

import bs4


class AvailabilityInfo(typing.TypedDict):
    location: str
    collection: str
    status: str
    call_number: str


def parse_availability_info(soup: bs4.BeautifulSoup) -> list[AvailabilityInfo]:
    """
    Given a chunk of HTML from the "availability API", which includes a
    table of availability info, parse out the relevant fields.
    """
    availability = []

    # There's a table with four columns:
    # Location/Collection/Call number/Status
    #
    # I'm mainly interested in location and status
    tbody = soup.find("tbody")
    assert isinstance(tbody, bs4.Tag)

    for row in tbody.find_all("tr"):
        fields = [
            ("location", "Location"),
            ("collection", "Collection"),
            ("status", "Status/Desc"),
            ("call_number", "Call number"),
        ]

        elements: dict[str, bs4.Tag | None] = {
            key: row.find("td", attrs={"data-caption": caption})
            for key, caption in fields
        }

        info: AvailabilityInfo = typing.cast(
            AvailabilityInfo,
            {key: elem.text if elem else "" for key, elem in elements.items()},
        )

        if "(Hertfordshire County Council)" not in info["location"]:
            continue

        info["location"] = info["location"].replace(
            " (Hertfordshire County Council)", ""
        )

        availability.append(info)

    return availability


RecordDetails: typing.TypeAlias = dict[str, str | list[str]]


def parse_record_details(soup: bs4.BeautifulSoup, *, url: str) -> RecordDetails:
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
    assert isinstance(rec_details_body, bs4.Tag)

    record_details: RecordDetails = {}

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
                record_details[key] = value[0]
            else:
                print(f"Record detail had multiple entries for {key}: {url}")
                record_details[key] = value

    # There's also a summary on the page, which unlike the search
    # results, isn't truncated.  e.g.
    #
    #     <div id="divtabSUMMARY" class="tab-container-body-inner">
    #       <span class="d-block">Anna Hart is a seasoned …</span>
    #     </div>
    #
    summary_div = soup.find("div", attrs={"id": "divtabSUMMARY"})

    if isinstance(summary_div, bs4.Tag):
        record_details["Summary"] = [
            span.getText() for span in summary_div.find_all("span")
        ]
    else:
        record_details["Summary"] = []

    return record_details


def get_url_of_next_page(soup: bs4.BeautifulSoup) -> str | None:
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
    assert isinstance(pagination_nav, bs4.Tag)

    nxt_li_elem = pagination_nav.find("li", attrs={"class": "nxt"})
    assert nxt_li_elem is not None

    anchor_elem = nxt_li_elem.find("a")
    if anchor_elem is None:
        return None

    assert isinstance(anchor_elem, bs4.Tag)
    return anchor_elem.attrs["href"]
