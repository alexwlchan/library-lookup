import bs4


class StrictSoup:
    """
    This is a wrapper around BeautifulSoup that provides some
    copies of ``find()`` and ``find_all()`` with assertions that
    they return the correct types.
    """

    def __init__(self, soup: bs4.BeautifulSoup):
        self._underlying: bs4.BeautifulSoup | bs4.Tag = soup

    def find(self, name: str, *, attrs: dict[str, str] | None = None) -> "StrictTag":
        tag = self._underlying.find(name, attrs=attrs or {})
        assert isinstance(tag, bs4.Tag)
        return StrictTag(tag=tag)


class StrictTag:
    def __init__(self, tag: bs4.Tag):
        self._underlying = tag

    def find(self, name: str, *, attrs: dict[str, str] | None = None) -> "StrictTag":
        tag = self._underlying.find(name, attrs=attrs or {})
        assert isinstance(tag, bs4.Tag)
        return StrictTag(tag=tag)

    def find_all(self, name: str, attrs: dict[str, str] | None = None) -> list["StrictTag"]:
        found_tags = self._underlying.find_all(name, attrs=attrs or {})
        assert all(isinstance(tag, bs4.Tag) for tag in found_tags)
        return [StrictTag(tag=tag) for tag in found_tags]

    @property
    def attrs(self) -> dict[str, str]:
        return self._underlying.attrs

    @property
    def text(self) -> str:
        return self._underlying.text

    def getText(self) -> str:
        return self._underlying.getText()
