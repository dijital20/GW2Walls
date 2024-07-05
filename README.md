# GW2 Wallpaper Downloader

Another script to work with HTML parsing with BeautifulSoup 4.

This script will crawl the Media > Wallpapers and Release pages to find links to wallpapers, catalog them, and then 
download wallpapers for a selected resolution (and optionally a selected release). Right now, I have the basic class 
together and some of the methods, but I will be refining and adding an argparse front end for running the file as a 
script.

## Setup

Using `uv`:

1. Clone this repository, and change directory to the cloned repo.
2. `uv venv`
3. `uv pip sync requirements.txt`

## Usage

Run `python GW2Walls.py --help` for details.