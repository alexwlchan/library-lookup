import bs4

from library_lookup.parsers import parse_availability_info


def test_it_gets_missing_info() -> None:
    with open("tests/fixtures/availability.html") as in_file:
        soup = bs4.BeautifulSoup(in_file.read(), "html.parser")

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
