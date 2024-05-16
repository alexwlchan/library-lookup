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
        result = self.find_optional(name, attrs=attrs)
        assert result is not None
        return result

    def find_optional(
        self, name: str, *, attrs: dict[str, str] | None = None
    ) -> "StrictTag" | None:
        tag = self._underlying.find(name, attrs=attrs or {})

        if tag is None:
            return None
        else:
            assert isinstance(tag, bs4.Tag)
            return StrictTag(tag=tag)

    def find_all(self, name: str) -> list["StrictTag"]:
        results = self._underlying.find_all(name)
        assert all(isinstance(r, bs4.Tag) for r in results)
        return [StrictTag(tag=t) for t in results]


class StrictTag(StrictSoup):
    def __init__(self, tag: bs4.Tag):
        self._underlying = tag

    @property
    def attrs(self) -> dict[str, str]:
        return self._underlying.attrs

    @property
    def text(self) -> str:
        return self._underlying.text

    def getText(self) -> str:
        return self._underlying.getText()
