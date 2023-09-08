# library-lookup

This is a tool for finding books that are available in nearby branches of my public lending library.

It shows me a list of books I can borrow immediately:

![A list of books. The first two books have large titles, a summary, and a list of branches where copies are available for immediate borrowing. There are two more books which are shown in smaller text and with greyed-out covers -- these aren't available nearby.](screenshot.png)

I don't expect anybody else will want to use this tool directly, but some of the ideas might be reusable.

How it works:

*   `get_book_data.py` scrapes the library website and saves the data about books I'm interested in to a JSON file.
*   `render_data_as_html.py` renders the JSON file as an HTML file which I can view in my browser. Having this be a separate step means I can tweak the presentation without having to redownload all the book data.

Some useful Python libraries:

*   I'm using [mechanize] to pretend to be a browser, and log into the library website.
    This is loosely based on some [code for scraping Spydus][spydus] by Mike Jagdis.
*   I'm using [BeautifulSoup] to parse the library website HTML.
*   I'm using [Jinja] to render the data as HTML.

[mechanize]: https://github.com/python-mechanize/mechanize
[spydus]: https://github.com/mjagdis/spydus
[BeautifulSoup]: https://www.crummy.com/software/BeautifulSoup/
[Jinja]: https://jinja.palletsprojects.com/en/3.1.x/
