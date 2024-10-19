import os

import bs4

from library_lookup.parsers import (
    get_cover_image_url,
    get_url_of_next_page,
    parse_availability_info,
    parse_record_details,
)


def get_fixture(fixture_name: str) -> bs4.BeautifulSoup:
    with open(os.path.join("tests/fixtures", fixture_name)) as in_file:
        return bs4.BeautifulSoup(in_file.read(), "html.parser")


class TestParseAvailabilityInfo:
    def test_it_gets_missing_info(self) -> None:
        soup = get_fixture("availability.html")

        assert parse_availability_info(soup) == [
            {
                "location": "St Albans Library",
                "collection": "Fiction",
                "status": "Onloan - Due: 02 Jun 2024",
                "call_number": "Science fiction paperback",
            },
            {
                "location": "Stevenage Central Library",
                "collection": "Fiction",
                "status": "Available",
                "call_number": "Science fiction paperback",
            },
            {
                "location": "Woodhall Library",
                "collection": "Adult Fiction: Science Fiction / Fantasy Fiction",
                "status": "Available",
                "call_number": "",
            },
        ]


class TestParseRecordDetails:
    def test_it_handles_none(self) -> None:
        soup = get_fixture("isbn_9780804692298.html")

        actual = parse_record_details(
            soup, url="/cgi-bin/spydus.exe/FULL/WPAC/ALLENQ/347793/70566229,142"
        )
        expected = {
            "Main title": "Ursula K. Le Guin : voyager to inner lands and to outer space / edited by Joe De Bolt ; with an introduction by Barry N. Malzbert.",
            "Imprint": "Port Washington ; London : Kennikat Press, 1979.",
            "Collation": "[5],221p. ; 22cm.",
            "ISBN": "9780804692298",
            "BRN": "2512994",
            "Bookmark link": "https://herts.spydus.co.uk/cgi-bin/spydus.exe/ENQ/WPAC/BIBENQ?SETLVL=&BRN=2512994",
            "Summary": [],
        }

        assert actual == expected

    def test_it_handles_multiple_entries_for_isbn(self) -> None:
        soup = get_fixture("isbn_9781847442260.html")

        details = parse_record_details(
            soup, url="/cgi-bin/spydus.exe/FULL/WPAC/ALLENQ/126638/71101226,44"
        )
        assert details["ISBN"] == ["9781847442260 (hbk)", "9781405517386 (ePub ebook)"]


class TestGetUrlOfNextPage:
    def test_it_finds_the_next_url(self) -> None:
        soup = bs4.BeautifulSoup(
            """
            <div class="col col-md text-md-center mt-2 mt-md-0"><nav class="prvnxt result-pages-prvnxt" aria-label="Search results previous and next pages"><ul class="list-inline mb-0"><li class="list-inline-item prv"><span><span class="fas fa-chevron-left mr-2"><span></span></span>Previous<span class="sr-only"> page of search results</span></span></li><li class="list-inline-item nxt"><a href="/cgi-bin/spydus.exe/SET/WPAC/ALLENQ/313828/71369607?NREC=20">Next<span class="sr-only"> page of search results</span><span class="fas fa-chevron-right ml-2"><span></span></span></a></li></ul></nav></div>
            """,
            "html.parser",
        )

        assert (
            get_url_of_next_page(soup)
            == "/cgi-bin/spydus.exe/SET/WPAC/ALLENQ/313828/71369607?NREC=20"
        )

    def test_it_returns_none_on_the_final_page(self) -> None:
        soup = bs4.BeautifulSoup(
            """
            <div class="col col-md text-md-center mt-2 mt-md-0"><nav class="prvnxt result-pages-prvnxt" aria-label="Search results previous and next pages"><ul class="list-inline mb-0"><li class="list-inline-item prv"><a href="/cgi-bin/spydus.exe/SET/WPAC/ALLENQ/313828/491841463?NREC=160&amp;NAVDIR=-1"><span class="fas fa-chevron-left mr-2"><span></span></span>Previous<span class="sr-only"> page of search results</span></a></li><li class="list-inline-item nxt"><span>Next<span class="sr-only"> page of search results</span><span class="fas fa-chevron-right ml-2"><span></span></span></span></li></ul></nav></div>
            """,
            "html.parser",
        )

        assert get_url_of_next_page(soup) is None


def test_get_cover_image_url() -> None:
    soup = bs4.BeautifulSoup(
        """
        <img
            alt="Thumbnail for Adulthood rites"
            class="imgsc img-fluid d-block mx-auto" data-deficon=""
    longdesc="https://www.bibdsl.co.uk/xmla/image-service.asp?ISBN=9781472281074&amp;SIZE=s&amp;DBM=1ipoizw9i9eqiwirork2o1o4j12nreflvemxskafsqa&amp;ERR=blank.gif&amp;SSL=true**"
            src="/docs/WPAC/images/loading.png"
            title="Adulthood rites"/>
        """,
        "html.parser",
    )
    img_elem = soup.find("img")
    assert isinstance(img_elem, bs4.Tag)

    assert (
        get_cover_image_url(img_elem)
        == "https://www.bibdsl.co.uk/xmla/image-service.asp?ISBN=9781472281074&SIZE=l&DBM=1ipoizw9i9eqiwirork2o1o4j12nreflvemxskafsqa&ERR=blank.gif&SSL=true%2A%2A"
    )
