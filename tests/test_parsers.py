import os

import bs4

from library_lookup.parsers import parse_availability_info, parse_record_details


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
