"""Downloads wallpapers for the game Guild Wars 2."""

import argparse
import datetime as dt
import logging
import sys
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from string import ascii_letters, digits
from typing import Literal

from bs4 import BeautifulSoup
from requests.sessions import Session

LOG = logging.getLogger("GW2Walls")
LOG_FORMAT = "%(message)s"
LOG_FORMAT_VERBOSE = "[%(name)s.%(funcName)s:%(lineno)d] %(message)s"

URL_MAIN_SITE = "https://www.guildwars2.com"
URL_MEDIA = f"{URL_MAIN_SITE}/en/media/wallpapers/"
URL_RELEASES = f"{URL_MAIN_SITE}/en/the-game/releases/"
ALLOWED_CHARACTERS = f"{ascii_letters}{digits}_-.() "
TRIM_FROM_TITLE = " | GuildWars2.com"
DATE_FORMATS = ("%B-%Y", "%B-%d-%Y")
SESSION = Session()


# region Dataclasses
@dataclass
class Wallpaper:
    """Represents a found wallpaper."""

    name: str
    dimensions: str
    url: str
    type: Literal["media", "release"]
    date: str = ""
    num: str = ""

    def get_path(self: "Wallpaper", root: Path) -> Path:
        """Get a local path for this wallpaper.

        Args:
            root: Root path to save wallpapers to.
            use_info: Should we use info to make the filename?
            use_folders: Should we use type and release name for the folder?

        Returns:
            A path to save the file to.
        """
        return root / self.type / f"{self.date} {self.name} {self.num} {self.dimensions}.jpg"


# endregion


# region Private functions
def __clean_name(name: str) -> str:
    """Clean the name down to its filename friendly parts.

    Args:
        name: _description_

    Returns:
        _description_
    """
    return "".replace(TRIM_FROM_TITLE, "").join(c for c in name if c in ALLOWED_CHARACTERS)


def __extract_release_date(url: str) -> str:
    """Extract the release date from a URL.

    Args:
        url: URL to the release.

    Returns:
        String date or empty string.
    """
    date_segment = url.split("/")[-2]
    for date_format in DATE_FORMATS:
        with suppress(ValueError):
            return str(dt.datetime.strptime(date_segment, date_format).date())
    LOG.debug("Failed to parse date from %r", date_segment)
    return ""


def __prepend_str(stem: str, value: str) -> str:
    """Ensure that a given string starts with a given value by adding it.

    Args:
        stem: Prefix to ensure the string has.
        value: The string in question.

    Returns:
        Prefixed string.
    """
    return value if value.startswith(stem) else f"{stem}{value}"


def __get_url(url: str) -> BeautifulSoup:
    """Get the contents of a URL as a BeautifulSoup object.

    Args:
        url: URL to get.

    Raises:
        RuntimeError: If we get a non-2xx status code.

    Returns:
        Parsed HTML content as a BeautifulSoup object.
    """
    LOG.debug("Getting url %s", url)
    try:
        response = SESSION.get(url)
    except Exception:
        LOG.exception("Error getting %s", url)
        raise

    LOG.debug("Got response code %d, %d bytes", response.status_code, len(response.content))
    if response.status_code // 100 != 2:
        msg = f"{response.url} returned {response.status_code}:\n{response.reason}"
        raise RuntimeError(msg)

    try:
        return BeautifulSoup(response.text, features="html.parser")
    except Exception:
        LOG.exception("Error parsing to soup")
        raise


def __get_media_walls() -> Iterator[Wallpaper]:
    """Get all of the wallpapers on the Media page.

    Yields:
        Each wallpaper, one at a time.
    """
    LOG.info("Getting media walls")
    soup = __get_url(URL_MEDIA)
    for wallpaper in soup.find_all("li", "wallpaper"):
        name = wallpaper.img["src"].split("/")[-1].replace("-crop.jpg", "")

        for size in wallpaper.find_all("a"):
            url = __prepend_str("https:", size["href"])

            yield Wallpaper(
                name=name,
                dimensions=size.text,
                url=url,
                type="media",
            )


def __get_release_walls() -> Iterator[Wallpaper]:
    """Get all of the wallpapers from the Releases page.

    Yields:
        Each wallpaper, one at a time.
    """
    LOG.info("Getting release walls")
    soup = __get_url(URL_RELEASES)
    for canvas in soup.find_all("section", "release-canvas"):
        for release in canvas.find_all("li"):
            url = __prepend_str(URL_MAIN_SITE, release.a["href"])

            yield from __get_specified_release(url)


def __get_specified_release(url: str) -> Iterator[Wallpaper]:
    """Get all of the wallpapers for a specific release.

    Args:
        url: URL of the release page.

    Yields:
        Each wallpaper, one at a time.
    """
    LOG.info("Getting release %s", url)
    soup = __get_url(url)
    name = __clean_name(soup.title.text)
    number = 0
    date = __extract_release_date(url)

    for keyword in ("wallpaper", "resolutions"):
        for wallpaper in soup.find_all("ul", keyword):
            number += 1

            for size in wallpaper.find_all("a"):
                url = __prepend_str("https:", size["href"])

                yield Wallpaper(
                    name=name,
                    dimensions=size.text,
                    url=url,
                    type="release",
                    date=date,
                    num=str(number),
                )


# endregion


# region Public functions
def get_wallpapers() -> Iterator[Wallpaper]:
    """Gets each wallpaper from the site.

    Yields:
        Each wallpaper, one at a time.
    """
    yield from __get_media_walls()
    yield from __get_release_walls()


# endregion

if __name__ == "__main__":
    # Setup the argument parser
    parser = argparse.ArgumentParser(
        description="Find and download Guild Wars 2 wallpapers.",
    )
    # Keywords
    parser.add_argument(
        "--release",
        "-r",
        action="append",
        help="Release to download wallpapers for. Example: 'Escape from Lions Arch'",
    )
    parser.add_argument(
        "--type",
        "-t",
        help="Type of wallpapers to download wallpapers for. Example: 'release'",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output.",
    )
    # Positionals
    parser.add_argument(
        "resolution",
        help="Resolution to download wallpapers for.",
    )
    parser.add_argument(
        "save_path",
        type=Path,
        help="Path to save downloaded wallpapers to. This path can include environment variables and the tilde (~).",
    )
    args = parser.parse_args()

    # Setup logger
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG if args.verbose else logging.INFO,
        format=LOG_FORMAT_VERBOSE if args.verbose else LOG_FORMAT,
    )

    # Create the output directory
    args.save_path: Path = args.save_path.resolve()

    # Iterate through the wallpapers
    for wallpaper in get_wallpapers():
        if args.release and wallpaper.name not in args.release:
            LOG.debug("Skipping wallpaper (release does not match): %s", wallpaper)
            continue

        if args.type and wallpaper.type != args.type:
            LOG.debug("Skipping wallpaper (type does not match): %s", wallpaper)
            continue

        if wallpaper.dimensions != args.resolution:
            LOG.debug("Skipping wallpaper (resolution does not match): %s", wallpaper)
            continue

        path = wallpaper.get_path(args.save_path)
        LOG.info("  Downloading url: %s", wallpaper.url)

        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open(mode="wb") as f:
            f.write(SESSION.get(wallpaper.url).content)

        LOG.info("  Wrote: %s", path)
