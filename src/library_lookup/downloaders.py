import os
import ssl
from typing import TypedDict
import urllib.request

import certifi
import hyperlink


class SavedImage(TypedDict):
    url: str
    path: str | None


def download_cover_image(image_url: str) -> SavedImage:
    """
    Download a cover image to a local folder, and return the path.
    """
    # We're going to save it to the 'covers' directory, which is gitignore'd.
    # We don't know if the image is a PNG or a JPEG yet, so look for
    # a file with a matching ISBN in the directory -- that's what we want.
    os.makedirs("covers", exist_ok=True)

    try:
        isbn = hyperlink.parse(image_url).get("ISBN")[0]
        assert isinstance(isbn, str)

        existing_image = next(p for p in os.listdir("covers") if p.startswith(isbn))
        return {"url": image_url, "path": os.path.join("covers", existing_image)}
    except (IndexError, StopIteration):
        pass

    ssl_context = ssl.create_default_context(cafile=certifi.where())

    req = urllib.request.Request(image_url)
    req.add_header("User-Agent", "alexwlchan <alex@alexwlchan.net>")

    with urllib.request.urlopen(req, context=ssl_context) as resp:
        filename = hyperlink.parse(resp.geturl()).path[-1]
        image_data = resp.read()
        resp.close()

    if filename == "blank.gif":
        return {"url": image_url, "path": None}

    # Note: we assume the URl will be something like
    #
    #     http://www.bibdsl.co.uk/bds-images/l/123456/1234567890.jpg
    #
    # and use the final part as a basis for the filename.
    out_path = os.path.join("covers", filename)

    with open(out_path, "wb") as out_file:
        out_file.write(image_data)

    return {"url": image_url, "path": out_path}
