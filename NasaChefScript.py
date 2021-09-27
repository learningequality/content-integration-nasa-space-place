import requests
from bs4 import BeautifulSoup
import os
from ricecooker.chefs import SushiChef
from ricecooker.classes import nodes, files, licenses
from PIL import Image
from ricecooker.utils import downloader
from ricecooker.utils import zip

KOLIBRI_API_KEY = 'bca1e71945d1456dc450211ebf1df799d63d5b7b'
# Run constants
################################################################################
CHANNEL_ID = "b349f1287cc94ab59b921171a134f8d3"  # Test channel ID
CHANNEL_NAME = "Nasa Testing Channel"  # Name of Kolibri channel
CHANNEL_SOURCE_ID = "nasa-testing-channel"  # Unique ID for content source
CHANNEL_DOMAIN = "https://spaceplace.nasa.gov/"  # Who is providing the content
CHANNEL_LANGUAGE = "en"  # Language of channel
CHANNEL_DESCRIPTION = "Nasa Channel"  # Description of the channel (optional)
CHANNEL_THUMBNAIL = "https://spaceplace.nasa.gov/resources/homepage/nasa.png"  # Local path or url to image file (optional)
CONTENT_ARCHIVE_VERSION = 1
LICENSE = licenses.AllRightsLicense('Nasa')

# Additional constants
################################################################################
CREDENTIALS = os.path.join("credentials", "credentials.json")
GAMES_FOLDER = os.path.join("chefdata", "games")
PDF_FOLDER = os.path.join("chefdata", "pdfbooks")
IMAGE_FOLDER = os.path.join("chefdata", 'images')
STATIC_URL = "https://spaceplace.nasa.gov"
ARCHIVE_FOLDER = os.path.join('chefdata', 'archive')
DATA_DIR = os.path.abspath('chefdata')
ZIP_DIR = os.path.join(DATA_DIR, 'zips')

SESSION = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'
}
SESSION.headers = headers


class NasaChefScript(SushiChef):
    channel_info = {
        'CHANNEL_ID': CHANNEL_ID,
        'CHANNEL_SOURCE_DOMAIN': CHANNEL_DOMAIN,
        'CHANNEL_SOURCE_ID': CHANNEL_SOURCE_ID,
        'CHANNEL_TITLE': CHANNEL_NAME,
        'CHANNEL_LANGUAGE': CHANNEL_LANGUAGE,
        'CHANNEL_DESCRIPTION': CHANNEL_DESCRIPTION,
        'CHANNEL_THUMBNAIL': CHANNEL_THUMBNAIL
    }
    ASSETS_DIR = os.path.abspath('assets')
    DATA_DIR = os.path.abspath('chefdata')
    DOWNLOADS_DIR = os.path.join(DATA_DIR, 'downloads')
    ARCHIVE_DIR = os.path.join(DOWNLOADS_DIR, 'archive_{}'.format(CONTENT_ARCHIVE_VERSION))

    def download_pdf(self, pdf_url, file_name):
        r = SESSION.get(pdf_url, stream=True)
        if not os.path.exists(GAMES_FOLDER):
            os.makedirs(GAMES_FOLDER)
        games_path = f'{GAMES_FOLDER}/{file_name}'
        with open(pdf_url, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
            return games_path

    def download_convert_image_to_jpg(self, file_url):
        folder_dir_path = os.path.join(IMAGE_FOLDER)
        if not os.path.exists(folder_dir_path):
            os.makedirs(folder_dir_path)
        file_name = file_url.split('/')[-1]
        new_name = file_name.split('.')[0]
        orig_path = os.path.join(folder_dir_path, f'{new_name}.jpg')

        if not os.path.exists(orig_path):
            response = SESSION.get(file_url, stream=True)
            with open(orig_path, 'wb') as pdf_file:
                pdf_file.write(response.content)

        file = Image.open(orig_path)
        rgb_image = file.convert('RGB')
        rgb_image.save(f'{new_name}.jpg')
        return orig_path

    def scrapping_resource_each_topic(self, url):
        response = SESSION.get(url)
        page = BeautifulSoup(response.text, 'html5lib')
        div_content = page.find('div', {"class": "content"})
        return div_content

    def scraping_nasa(self):
        response = SESSION.get(STATIC_URL)
        page = BeautifulSoup(response.text, 'html5lib')
        lst_nav_items = page.find_all('a', {'class': 'navItem'})
        dict_topic = {}
        for link in lst_nav_items:
            dict_topic[link.text] = {}
            res = SESSION.get(f'{STATIC_URL}/{link["href"]}', stream=True)
            page_tab = BeautifulSoup(res.text, 'html5lib')
            page_content = page_tab.find_all('li')
            # nasa_topic = nodes.TopicNode(source_id=f'{STATIC_URL}_{link.text}', title=link.text)
            for li in page_content:
                page_url = None
                dict_files = {}
                if li.find('span', {'class': 'play'}):
                    continue
                if li.find('img'):
                    image_url = li.find('img')['src']
                    dict_files['image_url'] = f'{STATIC_URL}{image_url}'
                if li.find('a'):
                    page_url = li.find('a')['href']
                    dict_files['page_url'] = page_url
                if li.find('p'):
                    name = li.find('p').text
                    dict_files['name'] = name
                if dict_files and dict_files.get('name') and dict_files.get('image_url'):
                    if dict_files.get('image_url').endswith('.gif'):
                        orig_path = self.download_convert_image_to_jpg(dict_files.get('image_url'))
                        dict_files['image_url'] = orig_path
                    if link.text in dict_topic:
                        if not dict_topic.get(link.text).get(page_url):
                            dict_topic.get(link.text)[page_url] = dict_files

        return dict_topic

    def construct_channel(self, *args, **kwargs):
        """
        Creates ChannelNode and build topic tree
        Args:
          - args: arguments passed in on the command line
          - kwargs: extra options passed in as key="value" pairs on the command line
            For example, add the command line option   lang="fr"  and the value
            "fr" will be passed along to `construct_channel` as kwargs['lang'].
        Returns: ChannelNode
        """

        channel_info = self.channel_info
        channel = nodes.ChannelNode(
            source_domain=channel_info['CHANNEL_SOURCE_DOMAIN'],
            source_id=channel_info['CHANNEL_SOURCE_ID'],
            title=channel_info['CHANNEL_TITLE'],
            thumbnail=channel_info.get('CHANNEL_THUMBNAIL'),
            description=channel_info.get('CHANNEL_DESCRIPTION'),
            language="en",
        )

        dict_content = self.scraping_nasa()
        channel = self.upload_content(dict_content, channel)

        return channel

    def remove_tags(self, bs_page):
        if bs_page:
            tags = bs_page.find_all('header')
            for tag in tags:
                tag.decompose()
            # for link in bs_page.find_all("a"):
            #     print(link.findParent)
            #     link.decompose()
            # for header in bs_page.find_all('h3', {'class': 'Quicksand'}):
            #     header.decompose()

    def create_zip_foreach_page(self, url_path, name):
        client = downloader.ArchiveDownloader(ARCHIVE_FOLDER)

        zip_dir_page = client.create_zip_dir_for_page(url_path)
        index_path = client.get_relative_index_path(url_path)

        with open(os.path.join(zip_dir_page, index_path), 'rb+') as f:
            page = f.read()
            bs_page = BeautifulSoup(page, 'html.parser')
            self.remove_tags(bs_page)
            bs_page.prettify('utf-8')

        with open(os.path.join(zip_dir_page, index_path), 'wb+') as f:
            f.write(bs_page.prettify('utf-8'))

        entrypoint = client.get_relative_index_path(url_path)
        zip_dir = zip.create_predictable_zip(zip_dir_page, entrypoint=entrypoint)
        zip_filename = os.path.join(ZIP_DIR, "{}.zip".format(name))

        os.makedirs(os.path.dirname(zip_filename), exist_ok=True)
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
        os.rename(zip_dir, zip_filename)
        return zip_filename

    def upload_content(self, dict_content, channel):
        for key in dict_content:
            nasa_topic = nodes.TopicNode(source_id=key, title=key)
            dict_topics = dict_content.get(key)
            for key_topic in dict_topics:
                dict_topic = dict_topics[key_topic]
                zip_dir = self.create_zip_foreach_page(f'{STATIC_URL}{dict_topic.get("page_url")}', dict_topic.get('name'))
                html_file = files.HTMLZipFile(path=zip_dir)

                html_node = nodes.HTML5AppNode(
                    title=dict_topic.get('name'),
                    license=LICENSE,
                    source_id=f'html_{dict_topic.get("page_url")}',
                    description="Test Html5 Node",
                    files=[html_file]
                )

                topic = nodes.TopicNode(
                    title=dict_topic.get('name'),
                    source_id=dict_topic.get("page_url").replace('/', '_'),
                    thumbnail=dict_topic.get('image_url'),
                    author="Nasa",
                    description=dict_topic.get('name')
                )
                topic.add_child(html_node)
                nasa_topic.add_child(topic)
                break
            channel.add_child(nasa_topic)
            break
        return channel


# CLI
################################################################################
if __name__ == '__main__':
    # This code runs when sushichef.py is called from the command line
    chef = NasaChefScript()
    chef.main()

    # def remove_tags(bs_page):
    #     if bs_page:
    #         tags = bs_page.find_all('header')
    #         for tag in tags:
    #             tag.decompose()
    #         # for link in bs_page.find_all("a"):
    #         #     print(link.findParent)
    #         #     link.decompose()
    #         # for header in bs_page.find_all('h3', {'class': 'Quicksand'}):
    #         #     header.decompose()
    #
    #
    # url_path = 'http://spaceplace.nasa.gov'
    # url_path_earth = 'https://spaceplace.nasa.gov/moon-phases/en/'
    #
    # from ricecooker.config import LOGGER  # Use LOGGER to print messages
    # import json
    #
    # client = downloader.ArchiveDownloader(ARCHIVE_FOLDER)
    #
    # zip_dir_page = client.create_zip_dir_for_page(url_path_earth)
    # index_path = client.get_relative_index_path(url_path_earth)
    #
    # with open(os.path.join(zip_dir_page, index_path), 'rb+') as f:
    #     page = f.read()
    #     bs_page = BeautifulSoup(page, 'html.parser')
    #     remove_tags(bs_page)
    #
    # with open(os.path.join(zip_dir_page, index_path), 'wb+') as f:
    #     f.write(bs_page.prettify('utf-8'))
    #
    # entrypoint = client.get_relative_index_path(url_path_earth)
    # zip_dir = zip.create_predictable_zip(zip_dir_page, entrypoint=entrypoint)
    # zip_filename = os.path.join(ZIP_DIR, "{}.zip".format('test'))
    # #
    # os.makedirs(os.path.dirname(zip_filename), exist_ok=True)
    # if os.path.exists(zip_filename):
    #     os.remove(zip_filename)
    # os.rename(zip_dir, zip_filename)
    # print(zip_filename)
