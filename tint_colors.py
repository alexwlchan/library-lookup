import json
import subprocess


def from_hex(hs):
    """
    Returns an RGB tuple from a hex string, e.g. #ff0102 -> (255, 1, 2)
    """
    return int(hs[1:3], 16), int(hs[3:5], 16), int(hs[5:7], 16)


def choose_tint_color_for_file(path):
    """
    Returns the tint colour for a file.
    """
    try:
        with open("colors.json") as infile:
            cached_colors = json.load(infile)
    except FileNotFoundError:
        cached_colors = {}

    try:
        return cached_colors[path]
    except KeyError:
        pass

    cmd = [
        "dominant_colours",
        "--no-palette",
        "--max-colours=12",
        path,
        "--best-against-bg=#ffffff",
    ]

    hex_str = subprocess.check_output(cmd).decode("utf8").strip()

    cached_colors[path] = hex_str

    with open("colors.json", "w") as outfile:
        outfile.write(json.dumps(cached_colors, indent=2, sort_keys=True))

    return hex_str
