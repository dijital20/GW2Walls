import argparse
import csv

try:  # Python 3
    from urllib.request import urlopen
except ImportError:  # Python 2
    from urllib2 import urlopen

from os import path, mkdir
from string import ascii_letters, digits
from datetime import datetime

from bs4 import BeautifulSoup


class GW2Walls:
    """
    This object searches the Guild Wars 2 website for wallpapers and adds them
    to a massive list of dictionary. You can then call the download_walls method
    to have it download all of the wallpapers for a specified resolution to a
    specified location.

    Script should automagically pick up new wallpapers (provided ArenaNet
    doesn't change the page design on any of the pages).

    Requires BeautifulSoup4.
    """

    # Set the URLs for the Media and Releases pages.
    media_url = 'https://www.guildwars2.com/en/media/wallpapers/'
    releases_url = 'https://www.guildwars2.com/en/the-game/releases/'
    main_site_url = 'https://www.guildwars2.com'

    def __init__(self, verbose=False):
        """
        Initializes the object for use.

        :return: None
        """
        self.walls = list()
        self.verbose = verbose
        self.get_media_walls()
        self.get_release_walls()
        if len(self.walls) == 0:
            raise ValueError('No walls found.')

    def get_media_walls(self):
        """
        Gets the wallpapers from the media page.

        :return: None - appends to self.walls.
        """
        print('\nGetting media walls\n{0}'.format(self.media_url))
        wallpaper_html = urlopen(self.media_url).read()
        wallpaper_soup = BeautifulSoup(wallpaper_html, 'html.parser')
        for wall_item in wallpaper_soup.find_all('li', 'wallpaper'):
            wall_name = wall_item.img['src'].split('/')[-1].replace(
                '-crop.jpg', '')
            for wall_size_item in wall_item.find_all('a'):
                if not wall_size_item['href'].startswith('https:'):
                    wall_size_item['href'] = 'https:{}'.format(
                        wall_size_item['href'])
                if self.verbose:
                    print('...Adding {} {} ({})'.format(
                        wall_name, wall_size_item.text,
                        wall_size_item['href']))
                self.walls.append({
                    'name': wall_name,
                    'dim': wall_size_item.text,
                    'url': wall_size_item['href'],
                    'type': 'media',
                    'date': '',
                    'num': ''
                })

    def get_release_walls(self):
        """
        Gets each release, gets the wallpaper(s) from that release, and adds
        them all.

        :return: None - appends to self.walls.
        """
        print('\nGetting release walls\n{0}'.format(self.releases_url))
        releases_html = urlopen(self.releases_url).read()
        releases_soup = BeautifulSoup(releases_html, 'html.parser')
        for canvas in releases_soup.find_all('section', 'release-canvas'):
            for release in canvas.find_all('li'):
                release_url = release.a['href'] \
                    if release.a['href'].startswith(self.main_site_url) \
                    else '{0}{1}'.format(self.main_site_url, release.a['href'])
                self.get_specified_release_wall(release_url)

    def get_specified_release_wall(self, release_url):
        """
        Gets the wallpaper links in a specific release.

        :param release_url: string - the URL to the release page.
        :return: None - appends to self.walls.
        """
        print('  Getting release: {0}'.format(release_url))
        release_html = urlopen(release_url).read()
        release_soup = BeautifulSoup(release_html, 'html.parser')
        wall_name = self.__filename(
            release_soup.title.text.replace(' | GuildWars2.com', ''))
        wall_number = 0
        wall_date = self.__get_release_date(release_url)
        if self.verbose:
            print('\nGetting {} ({}) walls...'.format(wall_name, wall_date))
        for keyword in ['wallpaper', 'resolutions']:
            for wall_item in release_soup.find_all('ul', keyword):
                wall_number += 1
                for wall_size_item in wall_item.find_all('a'):
                    if not wall_size_item['href'].startswith('https:'):
                        wall_size_item['href'] = 'https:{}'.format(
                            wall_size_item['href'])
                    if self.verbose:
                        print('...Adding {} {} ({})'.format(
                            wall_name, wall_size_item.text,
                            wall_size_item['href']))
                    self.walls.append({
                        'name': wall_name,
                        'dim': wall_size_item.text,
                        'url': wall_size_item['href'],
                        'type': 'release',
                        'date': wall_date,
                        'num': wall_number
                    })

    def collect_download_urls(self, dim, name=None, wall_type=None):
        """
        Goes through the combined list of dict

        :param dim: string - Contains the dimension we should return.
        :param name: string - Contains the release we should return.
        :return: None
        """
        wall_list = list()
        if dim not in self.dimensions:
            raise ValueError(
                'Incorrect dimension specified ({}).\n\nPlease specify one of '
                'the following:\n{}'.format(
                    dim, self.dimensions))
        if name and name not in self.names:
            raise ValueError(
                'Incorrect release name specified ({}).\n\nPlease specify one '
                'of the following:\n{}'.format(name, self.names))
        if wall_type and wall_type not in self.types:
            raise ValueError('Incorrect type specified ({}).\n\n'
                             'Please specify one of the following:\n{}'.format(
                                 wall_type, self.types))
        for item in self.walls:
            if name and wall_type:
                if item['name'] == name and item['type'] == wall_type \
                        and item['dim'] == dim:
                    wall_list.append(item)
            elif name and not wall_type:
                if item['name'] == name and item['dim'] == dim:
                    wall_list.append(item)
            elif wall_type and not name:
                if item['type'] == wall_type and item['dim'] == dim:
                    wall_list.append(item)
            else:
                if item['dim'] == dim:
                    wall_list.append(item)
        return wall_list

    def download_walls(self, save_path, dim,
                       name=None,
                       use_info=False,
                       use_folders=False,
                       wall_type=None):
        """
        Downloads wallpapers to save_path that match the resolution given in
        dim. If name is specified, just gets the wallpaper for that release,
        that resolution.

        :param save_path: string - The path to save the wallpapers to. Path can
            contain environment variables and ~.
        :param dim: string - The resolution given as "AxB", where A and B are
            numbers.
        :param name: string - (optional) The name of the release to get
            wallpapers for. Example: "The Dragon's Reach Part 2"
        :return: None (Downloads wallpapers)
        """
        save_path = path.expanduser(save_path)
        save_path = path.expandvars(save_path)
        items = self.collect_download_urls(dim, name=name, wall_type=wall_type)
        print('\nDownloading wallpapers to {}'.format(save_path))
        for idx, item in enumerate(items):
            if use_info:
                if use_folders:
                    save_file = path.join(
                        save_path, item['type'],
                        '{date} {name} {num} {dim}.jpg'.format(**item).strip())
                else:
                    save_file = path.join(
                        save_path,
                        '{date} {name} {num} {dim}.jpg'.format(**item).strip())
            else:
                save_file = path.join(save_path, item['url'].split('/')[-1])
            if not path.exists(path.dirname(save_file)):
                try:
                    print('Creating {}'.format(path.dirname(save_file)))
                    mkdir(path.dirname(save_file))
                except OSError as e:
                    print(e)
            try:
                if self.verbose:
                    print('({:>3}/{:>3}) {} <-- {}'.format(
                        idx + 1, len(items), save_file, item['url']))
                else:
                    print('({:>3}/{:>3}) {}'.format(idx + 1, len(items),
                                                    path.basename(save_file)))
                with open(save_file, mode='wb') as f:
                    f.write(urlopen(item['url']).read())
            except OSError as e:
                print(e)

    def walls_to_csv(self, save_file):
        """
        Export the list of walls to a csv file. May be useful for debugging.

        :param save_file: str - Path to the csv file that the list will be
            exported to.
        :return: None - Writes and then exits, returns nothing.
        """
        fields = ['dim', 'name', 'type', 'date', 'url']
        print('\nWriting output to {}'.format(save_file))
        with open(save_file, mode='w') as f:
            csv_out = csv.DictWriter(f, fieldnames=fields)
            csv_out.writeheader()
            csv_out.writerows(self.walls)
        print('Writing complete.')

    @property
    def dimensions(self):
        """
        Returns the list of dimensions in self.walls.

        :return: set - The set of all dimension strings in the collection.
        """
        return set(dic['dim'] for dic in self.walls)

    @property
    def names(self):
        """
        Returns the list of names in self.walls.

        :return: set - The set of all release names in the collection.
        """
        return set(dic['name'] for dic in self.walls)

    @property
    def types(self):
        """
        Returns the list of types in self.walls.

        :return: set - The set of all types in the collection.
        """
        return set(dic['type'] for dic in self.walls)

    @staticmethod
    def __filename(in_file):
        """
        Returns a filename-friendly version of the release name.

        :param in_file: string - Name of the release.
        :return: string - Filename-friendly version of the name of the release.
        """
        valid_chars = '-_.() {}{}'.format(ascii_letters, digits)
        return ''.join(c for c in in_file if c in valid_chars)

    @staticmethod
    def __get_release_date(release_url):
        """
        Takes the release_url and returns the date inside of the last path
        segment (if it exists).
        Example input: https://www.guildwars2.com/en/the-game/releases/august-12-2014/
        Example output: 2014-08-12

        :param release_url: str - URL of the release page.
        :return: str - Date string of the date from the URL or an empty string
            if no date in URL.
        """
        date = release_url.split('/')[-2]
        for date_format in ['%B-%Y', '%B-%d-%Y']:
            try:
                return datetime.strptime(date, date_format).date()
            except ValueError:
                continue
        return ''


if __name__ == '__main__':
    # Setup the argument parser
    parser = argparse.ArgumentParser(
        description='Find and download Guild Wars 2 wallpapers.')
    parser.add_argument(
        '-r',
        type=str,
        help='Release to download wallpapers for. Example: \'Escape from Lions '
        'Arch\'',
        default='',
        metavar='release')
    parser.add_argument(
        '-t',
        type=str,
        help=
        'Type of wallpapers to download wallpapers for. Example: \'release\'',
        default='',
        metavar='type')
    parser.add_argument(
        '-u',
        help=
        'Use wallpaper information in the name rather than the original name.',
        action='store_true')
    parser.add_argument(
        '-f',
        help=
        'User wallpaper type as a folder. Only works in conjunction with -u.',
        action='store_true')
    parser.add_argument('-v',
                        help='Enable verbose output.',
                        action='store_true')
    parser.add_argument('-c',
                        type=str,
                        help='Output the link list to a csv file.',
                        default='',
                        metavar='csv_path')
    parser.add_argument('resolution',
                        type=str,
                        help='Resolution to download wallpapers for.')
    parser.add_argument(
        'save_path',
        type=str,
        help='Path to save downloaded wallpapers to. This path can include '
        'environment variables and the tilde (~).')
    # Parse arguments
    values = parser.parse_args()

    # Do stuff!
    app = GW2Walls(values.v)
    app.download_walls(values.save_path, values.resolution,
                       name=values.r,
                       wall_type=values.t,
                       use_info=values.u,
                       use_folders=values.f)
    if values.c:
        app.walls_to_csv(values.c)
