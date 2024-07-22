import re


def display_author_name(label: str) -> str:
    """
    Convert an author name from Spydus into something to display
    on the page.

    See the tests for examples.
    """
    # Remove years of life from the end of the label, e.g.
    #
    #     Kawaguchi, Toshikazu, 1971-
    #     Le Guin, Ursula K., 1929-2018
    #
    label = re.sub(r", [0-9]{4}\-(?:[0-9]{4})?$", "", label)

    try:
        last_name, first_name = label.split(",")
    except ValueError:
        return label

    # Remove any trailing descriptions from the first name, e.g.
    #
    #     Claire (Journalist)
    #     Justin (Comic book writer)
    #
    first_name = re.sub(r" \([A-Za-z ]+\)$", "", first_name)

    return f"{first_name.strip()} {last_name.strip()}"
