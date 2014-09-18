from urllib import request
from pprint import PrettyPrinter
from os import path, mkdir
from string import ascii_letters, digits
from datetime import datetime

from bs4 import BeautifulSoup

pp = PrettyPrinter(indent=2)


class GW2Walls:
    """
    This object searches the Guild Wars 2 website for wallpapers and adds them to a massive list of dictionary. You
    can then call the download_walls method to have it download all of the wallpapers for a specified resolution to a
    specified location.

    Script should automagically pick up new wallpapers (provided ArenaNet doesn't change the page design on any of
    the pages).

    Requires BeautifulSoup4.
    """

    # Set the URLs for the Media and Releases pages.
    media_url = 'https://www.guildwars2.com/en/media/wallpapers/'
    releases_url = 'https://www.guildwars2.com/en/the-game/releases/'
    main_site_url = 'https://www.guildwars2.com'

    def __init__(self):
        """
        Initializes the object for use.

        :return: None
        """
        self.walls = list()
        self.get_media_walls()
        self.get_release_walls()

    def get_media_walls(self):
        """
        Gets the wallpapers from the media page.

        :return: None - appends to self.walls.
        """
        print('\nGetting media walls...')
        wallpaper_html = request.urlopen(self.media_url).read()
        wallpaper_soup = BeautifulSoup(wallpaper_html)
        for wall_item in wallpaper_soup.find_all('li', 'wallpaper'):
            wall_name = wall_item.img['src'].split('/')[-1].replace('-crop.jpg', '')
            for wall_size_item in wall_item.find_all('a'):
                if not wall_size_item['href'].startswith('https:'):
                    wall_size_item['href'] = 'https:{}'.format(wall_size_item['href'])
                print('...Adding {} {} ({})'.format(wall_name, wall_size_item.text, wall_size_item['href']))
                self.walls.append(
                    {'name': wall_name, 'dim': wall_size_item.text, 'url': wall_size_item['href'], 'type': 'media',
                     'date': ''})

    def get_release_walls(self):
        """
        Gets each release, gets the wallpaper(s) from that release, and adds them all.

        :return: None - appends to self.walls.
        """
        print('\nGetting release walls...')
        releases_html = request.urlopen(self.releases_url).read()
        releases_soup = BeautifulSoup(releases_html)
        for canvas in releases_soup.find_all('section', 'release-canvas'):
            for release in canvas.find_all('li'):
                self.get_specified_release_wall(self.main_site_url + release.a['href'])

    def get_specified_release_wall(self, release_url):
        """
        Gets the wallpaper links in a specific release.

        :param release_url: string - the URL to the release page.
        :return: None - appends to self.walls.
        """
        release_html = request.urlopen(release_url).read()
        release_soup = BeautifulSoup(release_html)
        wall_name = self.__filename(release_soup.title.text.replace(' | GuildWars2.com', ''))
        wall_date = self.__get_release_date(release_url)
        print('\nGetting {} ({}) walls...'.format(wall_name, wall_date))
        for keyword in ['wallpaper', 'resolutions']:
            for wall_item in release_soup.find_all('ul', keyword):
                for wall_size_item in wall_item.find_all('a'):
                    if not wall_size_item['href'].startswith('https:'):
                        wall_size_item['href'] = 'https:{}'.format(wall_size_item['href'])
                    print('...Adding {} {} ({})'.format(wall_name, wall_size_item.text, wall_size_item['href']))
                    self.walls.append({'name': wall_name, 'dim': wall_size_item.text, 'url': wall_size_item['href'],
                                       'type': 'release', 'date':wall_date})

    def collect_download_urls(self, dim, name=None, type=None):
        """
        Goes through the combined list of dict

        :param dim: string - Contains the dimension we should return.
        :param name: string - Contains the release we should return.
        :return: None
        """
        wall_list = list()
        if dim not in self.dimensions:
            raise ValueError('Incorrect dimension specified ({}).\nPlease specify one of the following:\n{}'.format(
                dim, pp.pprint(self.dimensions)))
        if name and name not in self.names:
            raise ValueError('Incorrect release name specified ({}).\nPlease specify one of the following:\n{'
                             '}'.format(name, pp.pprint(self.names)))
        if type and type not in self.types:
            raise ValueError('Incorrect type specified ({}).\nPlease specify one of the following:\n{}'.format(type,
                                                                                                               pp.pprint(self.types)))
        for item in self.walls:
            if name and type:
                if item['name'] == name and item['type'] == type and item['dim'] == dim:
                    wall_list.append(item)
            elif name and not type:
                if item['name'] == name and item['dim'] == dim:
                    wall_list.append(item)
            elif type and not name:
                if item['type'] == type and item['dim'] == dim:
                    wall_list.append(item)
            else:
                if item['dim'] == dim:
                    wall_list.append(item)
        return wall_list

    def download_walls(self, save_path, dim, name=None, use_info=False, type=None):
        """
        Downloads wallpapers to save_path that match the resolution given in dim. If name is specified, just gets the
        wallpaper for that release, that resolution.

        :param save_path: string - The path to save the wallpapers to. Path can contain environment variables and ~.
        :param dim: string - The resolution given as "AxB", where A and B are numbers.
        :param name: string - (optional) The name of the release to get wallpapers for. Example: "The Dragon's Reach
        Part 2"
        :return: None (Downloads wallpapers)
        """
        save_path = path.expanduser(save_path)
        save_path = path.expandvars(save_path)
        if not path.exists(save_path):
            try:
                mkdir(save_path)
            except OSError as e:
                print(e)
        items = self.collect_download_urls(dim, name=name, type=type)
        print('\nDownloading wallpapers to {}'.format(save_path))
        for idx, item in enumerate(items):
            if use_info:
                save_file = path.join(save_path, '{date} {name} {dim}.jpg'.format(**item))
            else:
                save_file = path.join(save_path, item['url'].split('/')[-1])
            try:
                print('({:>3}/{:>3}) {} <-- {}'.format(idx + 1, len(items), save_file, item['url']))
                with open(save_file, mode='wb') as f:
                    f.write(request.urlopen(item['url']).read())
            except (PermissionError, OSError) as e:
                print(e)

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
        date = release_url.split('/')[-2]
        for format in ['%B-%Y', '%B-%d-%Y']:
            try:
                return datetime.strptime(date, format).date()
            except ValueError:
                continue
        return ''

if __name__ == '__main__':
    app = GW2Walls()
    # app.download_walls('%userprofile%\\Desktop\\GW2 Walls', '1680x1050')
    app.download_walls('~/Desktop/GW2', '1920x1200', use_info=True)
    # TODO: Add argparse front-end here.