from urllib import request
from bs4 import BeautifulSoup
from pprint import PrettyPrinter
import os
import string

pp = PrettyPrinter(indent=2)


class GW2Walls:
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
                self.walls.append({'name':wall_name, 'dim': wall_size_item.text, 'url':wall_size_item['href'], 'type':'media'})

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
        print('\nGetting {} walls...'.format(wall_name))
        for keyword in ['wallpaper', 'resolutions']:
            for wall_item in release_soup.find_all('ul', keyword):
                for wall_size_item in wall_item.find_all('a'):
                    if not wall_size_item['href'].startswith('https:'):
                        wall_size_item['href'] = 'https:{}'.format(wall_size_item['href'])
                    print('...Adding {} {} ({})'.format(wall_name, wall_size_item.text, wall_size_item['href']))
                    self.walls.append({'name':wall_name, 'dim': wall_size_item.text, 'url':wall_size_item['href'], 'type':'release'})

    def collect_download_urls(self, dim, name=None):
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
        for item in self.walls:
            if name:
                if item['name'] == name and item['dim'] == dim:
                    wall_list.append(item)
            else:
                if item['dim'] == dim:
                    wall_list.append(item)
        return wall_list

    def download_walls(self, save_path, dim, name=None):
        save_path = os.path.expanduser(save_path)
        save_path = os.path.expandvars(save_path)
        if not os.path.exists(save_path):
            try:
                os.mkdir(save_path)
            except OSError as e:
                print(e)
        items = self.collect_download_urls(dim, name=name)
        print('\nDownloading wallpapers to {}'.format(save_path))
        for idx, item in enumerate(items):
            save_file = os.path.join(save_path, item['url'].split('/')[-1])
            try:
                print('({:>3}/{:>3}) {} <-- {}'.format(idx + 1, len(items), save_file, item['url']))
                with open(save_file, mode='wb') as f:
                    f.write(request.urlopen(item['url']).read())
            except (PermissionError, OSError) as e:
                print(e)

    @property
    def dimensions(self):
        return set(dic['dim'] for dic in self.walls)

    @property
    def names(self):
        return set(dic['name'] for dic in self.walls)

    @staticmethod
    def __filename(in_file):
        valid_chars = '-_.() {}{}'.format(string.ascii_letters, string.digits)
        return ''.join(c for c in in_file if c in valid_chars)

if __name__ == '__main__':
    app = GW2Walls()
    # Print some properties.
    app.download_walls('%userprofile%\\Desktop\\GW2 Walls', '1680x1050')