import os
import typing

import httpx
import hyperlink


class SavedImage(typing.TypedDict):
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

    image_resp = httpx.get(image_url, follow_redirects=True)

    # Note: we assume the URl will be something like
    #
    #     http://www.bibdsl.co.uk/bds-images/l/123456/1234567890.jpg
    #
    # and use the final part as a basis for the filename.
    out_path = os.path.join("covers", os.path.basename(image_resp.url.path))

    if os.path.basename(image_resp.url.path) == "blank.gif":
        return {"url": image_url, "path": None}

    with open(out_path, "wb") as out_file:
        out_file.write(image_resp.content)

    return {"url": image_url, "path": out_path}
