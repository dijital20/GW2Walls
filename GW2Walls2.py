import argparse
import logging
import os
import re
import sys

from contextlib import closing
from threading import Thread
from Queue import Queue, Empty

try:  # Python 3
    from urllib.request import urlopen
except ImportError:  # Python 2
    from urllib2 import urlopen

try:  # Python 3
    from urllib.parse import urlsplit
except ImportError:  # Python 2
    from urlparse import urlsplit


MEDIA_URL = 'https://www.guildwars2.com/en/media/wallpapers/'
RELEASES_URL = 'https://www.guildwars2.com/en/the-game/releases/'
MAIN_SITE_URL = 'https://www.guildwars2.com'
LINK_PATTERN = r'<a .*?href=["\'](.+?)["\'].*?>(.*?)</a>'
LIST_PATTERN = r'<li.*?>(.*?)</li>'
HEADER_4_PATTERN = r'<h4.*?>(.*?)</h4>'
HEADER_5_PATTERN = r'<h5.*?>(.*?)</h5>'
DATETIME_PATTERN = r'<time.*?datetime="([\d\-]*)".*?>'
RELEASE_SECTION_PATTERN = r'<section.*?class=".*?release-canvas.*?>(.*?)</section>'

_log = logging.getLogger('GW2Walls2')
_queue = Queue()

def fix_save_path(save_path):
    _log.debug('Called with: %s', save_path)
    save_path = os.path.expanduser(save_path)
    save_path = os.path.expandvars(save_path)
    save_path = os.path.abspath(save_path)
    _log.debug('Returning: %s', save_path)
    return save_path

def cleanup_html(html):
    # PATTERNS
    newline_pattern = r'[\r\n]'
    tab_pattern = r'\t'
    redundant_whitespace_pattern = r'\s{2,}'
    # Cleanup
    _log.debug('Input length: %d chars', len(html))
    html = re.sub(newline_pattern, ' ', html)
    html = re.sub(tab_pattern, ' ', html)
    html = re.sub(redundant_whitespace_pattern, '', html)
    _log.debug('Output length: %d chars', len(html))
    return html

def cleanup_title(title_html):
    _log = logging.getLogger('GW2Walls2')
    # PATTERNS
    tag_pattern = r'<[/]?\w+>'
    unfriendly_chars = r'[^\w\s\-]'
    # Cleanup
    _log.debug('Called with: %s', title_html)
    title_html = re.sub(tag_pattern, '', title_html)
    title_html = re.sub(unfriendly_chars, '', title_html)
    _log.debug('Returning: %s', title_html)
    return title_html

def cleanup_url(url):
    if url.startswith('//'):
        url = 'https:{}'.format(url)
    elif url.startswith('/'):
        url = '{}{}'.format(MAIN_SITE_URL, url)
    return url

# --- Gather URLs -------------------------------------------------------------
def get_media_urls(resolution, save_path, media_url=MEDIA_URL):
    _log.debug('Called with: %s', locals())
    found = 0
    with closing(urlopen(media_url)) as p:
        data = cleanup_html(p.read())
    links = re.findall(LINK_PATTERN, data, flags=re.IGNORECASE)
    _log.debug('Processing %d links', len(links))
    for file_url, link_text in links:
        file_url = cleanup_url(file_url)
        _log.debug('%s <--> %s', repr(link_text), repr(resolution))
        if link_text == resolution:
            file_path = os.path.join(
                save_path, 
                'Media',
                os.path.basename(urlsplit(file_url)[2])
            )
            _log.debug('Adding URL: %s, %s', file_url, file_path)
            _queue.put((file_url, file_path))
            found += 1
    _log.info('Found %d wallpapers in Media', found)

def get_releases_urls(resolution, save_path, release_url=RELEASES_URL):
    _log.debug('Called with: %s', locals())
    with closing(urlopen(release_url)) as p:
        data = cleanup_html(p.read())
    section_data = re.findall(RELEASE_SECTION_PATTERN, data, flags=re.IGNORECASE)
    for section in section_data:
        section_title = re.findall(HEADER_4_PATTERN, section, flags=re.IGNORECASE)
        section_title = cleanup_title(section_title[0] if section_title else '')
        list_items = re.findall(LIST_PATTERN, section)
        for list_item in list_items:
            release_name = re.findall(HEADER_5_PATTERN, list_item, flags=re.IGNORECASE)
            release_name = cleanup_title(release_name[0] if release_name else '')
            release_date = re.findall(DATETIME_PATTERN, list_item, flags=re.IGNORECASE)
            release_date = release_date[0] if release_date else ''
            links = re.findall(LINK_PATTERN, list_item)
            _log.debug('Processing %d links', len(links))
            for url, _ in links:
                url = cleanup_url(url)
                t = Thread(target=get_release_urls, args=(
                    section_title, 
                    release_name, 
                    release_date, 
                    url, 
                    resolution,
                    save_path
                ))
                t.start()

def get_release_urls(section_title, release_name, release_date, url, resolution, save_path):
    _log.debug('Called with: %s', locals())
    found = 0
    try:
        with closing(urlopen(url)) as p:
            data = cleanup_html(p.read())
    except Exception as e:
        _log.error('ERROR opening %s: %s', url, e)
        return
    links = re.findall(LINK_PATTERN, data, flags=re.IGNORECASE)
    _log.debug('Processing %d links', len(links))
    for file_url, link_text in links:
        file_url = cleanup_url(file_url)
        try:
            _log.debug('%s %s: %s <--> %s', section_title, release_name, repr(link_text), repr(resolution))
            if link_text == resolution:
                file_path = os.path.join(
                    save_path, 
                    '{} {} {} {}'.format(
                        release_date,
                        section_title,
                        release_name,
                        os.path.basename(urlsplit(file_url)[2])
                    )
                )
                _log.debug('Adding URL: %s, %s', file_url, file_path)
                _queue.put((file_url, file_path))
                found += 1
        except ValueError:
            continue
    _log.info('Found %d wallpapers in %s %s', found, section_title, release_name)

# --- Download URLs -----------------------------------------------------------
def download_image():
    _log.debug('Download thread started.')
    while True:
        try:
            url, save_path = _queue.get(False)
            _log.debug('Got: %s --> %s', url, save_path)
            if not os.path.exists(os.path.dirname(save_path)):
                try:
                    os.makedirs(os.path.dirname(save_path))
                    _log.info('Created: %s', os.path.dirname(save_path))
                except Exception as e:
                    _log.warning('Failed to create: %s', os.path.dirname(save_path))
            try:
                if os.path.exists(save_path):
                    _log.warning('WARNING: Overwriting file as it already exists:\n%s', save_path)
                with closing(urlopen(url)) as u:
                    with open(save_path, mode='wb') as f:
                        f.write(u.read())
                _log.info('Saved: %s', save_path)
            except (ValueError, OSError) as e:
                _log.error('ERROR saving %s from %s:\n%s', save_path, url, e)
            _queue.task_done()
        except Empty:
            break
    _log.debug('Download thread done.')

# --- Main --------------------------------------------------------------------
if __name__ == '__main__':
    # Setup arg parser
    parser = argparse.ArgumentParser(
        version='1.0',
        description='Find and download GW2 Wallpapers.'
    )
    parser.add_argument(
        '--verbose',
        default=False,
        action='store_true',
        help='Enable verbose output.'
    )
    parser.add_argument(
        '--threads', '-t',
        default=1,
        type=int,
        help='Number of threads to use for downloading. Defaults to 1.'
    )
    parser.add_argument(
        'resolution', 
        type=str,
        metavar='RESOLUTION',
        help='Resolution of wallpapers to download.'
    )
    parser.add_argument(
        'save_path',
        type=str,
        metavar='SAVE_PATH',
        help='Path to save downloaded wallpapers to.'
    )
    values = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG
              if values.verbose
              else logging.INFO, 
        format='%(funcName)s:%(lineno)d %(message)s'
               if values.verbose
               else '%(message)s',
        stream=sys.stdout,
    )
    _log = logging.getLogger('GW2Walls2')
    values.save_path = fix_save_path(values.save_path)

    _log.debug('Processed Args:\n%s\n', '\n'.join(
        ['{:<16}: {}'.format(k, v) for k, v in values.__dict__.items()]
    ))

    _log.info('\nGetting URLs...')
    get_releases_urls(values.resolution, values.save_path)
    get_media_urls(values.resolution, values.save_path)
    
    _log.info('\nDownloading files...')
    for i in range(values.threads):
        t = Thread(target=download_image)
        t.start()
    
    _queue.join()
    _log.info('Done.')
