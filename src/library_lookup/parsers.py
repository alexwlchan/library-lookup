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
