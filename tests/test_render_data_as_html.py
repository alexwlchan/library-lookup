import pytest

from library_lookup.render_data_as_html import display_author_name


@pytest.mark.parametrize(
    ["label", "display_label"],
    [
        ("Alexander, Tasha, 1969-", "Tasha Alexander"),
        ("Allende, Isabel", "Isabel Allende"),
        ("Douglas, Claire (Journalist)", "Claire Douglas"),
        ("Various authors", "Various authors"),
        ("Kay, Laura, 1989", "Laura Kay"),
    ],
)
def test_display_author_name(label: str, display_label: str) -> None:
    assert display_author_name(label) == display_label
