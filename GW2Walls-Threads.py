import argparse
import logging
import os
import sys
import time
from datetime import datetime
from string import ascii_letters, digits
from threading import Thread

import requests
from bs4 import BeautifulSoup

MEDIA_URL = 'https://www.guildwars2.com/en/media/wallpapers/'
RELEASES_URL = 'https://www.guildwars2.com/en/the-game/releases/'
MAIN_URL = 'https://www.guildwars2.com'
LOG = logging.getLogger(__name__)


def get_soup(url):
    return BeautifulSoup(requests.get(url).content, 'html.parser')


def get_media_walls(dimensions, save_path):
    LOG.debug('Collecting Media walls for %s', dimensions)
    soup = get_soup(MEDIA_URL)
    tasks = []
    for wall_item in soup.find_all('li', 'wallpaper'):
        wall_name = wall_item.img['src'].split('/')[-1].replace('-crop.jpg', '.jpg')

        for wall_size_item in wall_item.find_all('a'):
            if not wall_size_item['href'].startswith('https:'):
                wall_size_item['href'] = 'https:{}'.format(wall_size_item['href'])

            if wall_size_item.text.strip() != dimensions:
                continue

            tasks.append(Thread(
                target=download_wallpaper, args=(wall_size_item['href'], wall_name, 'media', save_path)
            ))
            tasks[-1].start()

    LOG.debug('Done getting media walls')
    return tasks


def get_releases(dimensions, save_path):
    LOG.debug('Collecting Releases')
    soup = get_soup(RELEASES_URL)

    tasks = []
    for canvas in soup.find_all('section', 'release-canvas'):
        for release in canvas.find_all('li'):
            release_url = (
                release.a['href']
                if release.a['href'].startswith(MAIN_URL)
                else '{}{}'.format(MAIN_URL, release.a['href'])
            )
            tasks += get_release_walls(dimensions, release_url, save_path)

    LOG.debug('Done getting releases')
    return tasks


def get_release_walls(dimensions, release_url, save_path):
    soup = get_soup(release_url)
    release_name = get_filename_friendly(soup.title.text.replace(' | GuildWars2.com', ''))
    release_date = get_release_date_from_url(release_url)
    wall_number = 0

    LOG.debug('Collecting %s (%s) walls for %s', release_name, release_date, dimensions)
    tasks = []
    for keyword in ('wallpaper', 'resolutions'):
        for wall_item in soup.find_all('ul', keyword):
            wall_number += 1

            for wall_size_item in wall_item.find_all('a'):
                if not wall_size_item['href'].startswith('https:'):
                    wall_size_item['href'] = 'https:{}'.format(wall_size_item['href'])

                if wall_size_item.text.strip() != dimensions:
                    continue

                wall_name = f'{release_date}_{release_name}_{wall_number}.jpg'
                tasks.append(Thread(
                    target=download_wallpaper,
                    args=(wall_size_item['href'], wall_name, 'release', save_path),
                ))
                tasks[-1].start()

    LOG.debug('Done getting %s walls', release_name)
    return tasks


def get_filename_friendly(in_file):
    valid_chars = '-_.() {}{}'.format(ascii_letters, digits)
    return ''.join(c for c in in_file if c in valid_chars)


def get_release_date_from_url(release_url):
    date = release_url.split('/')[-2]
    for date_format in ['%B-%Y', '%B-%d-%Y']:
        try:
            return datetime.strptime(date, date_format).date()
        except ValueError:
            continue
    return ''


def get_wall_urls(dimensions, save_path):
    LOG.info('Getting wallpapers with dimensions %r to path %r', dimensions, save_path)
    tasks = get_releases(dimensions, save_path) + get_media_walls(dimensions, save_path)
    last_count = 0
    LOG.debug('Waiting on threads to complete now...')
    while tasks:
        if len(tasks) != last_count:
            LOG.debug('%d living threads', len(tasks))
            last_count = len(tasks)
        tasks = [t for t in tasks if t.is_alive()]


def download_wallpaper(url, name, kind, save_path):
    LOG.debug('Downloading %s', url)
    dst_path = os.path.abspath(
        os.path.expandvars(
            os.path.expanduser(
                os.path.join(save_path, kind, name)
            )
        )
    )
    response = requests.get(url)
    LOG.info('Writing %s (%d bytes)', dst_path, len(response.content))
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, mode='wb') as f:
        for chunk in response.iter_content(2 ** 16):
            f.write(chunk)
    LOG.debug('Done writing %s to %s', url, dst_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find and download Guild Wars 2 wallpapers.')

    parser.add_argument('-v', action='store_true', help='Enable verbose output.', )

    parser.add_argument('resolution', type=str, help='Resolution to download wallpapers for.')
    parser.add_argument(
        'save_path', type=str,
        help='Path to save downloaded wallpapers to. This path can include environment variables and the tilde (~).'
    )

    # Parse arguments
    args = parser.parse_args()

    # Setup logger
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG if args.v else logging.INFO,
        format='%(relativeCreated)8d [%(threadName)s %(funcName)s:%(lineno)d] %(message)s' if args.v else '%(message)s'
    )

    timer = time.perf_counter()
    get_wall_urls(args.resolution, args.save_path)
    elapsed = time.perf_counter() - timer
    LOG.info('Downloaded wallpapers in %.2f seconds', elapsed)
