from datetime import datetime
from email.utils import parsedate_to_datetime
import json
import os
from urllib.parse import urlparse
import sys

from jinja2 import Environment, FileSystemLoader
from markdown import markdown
from PIL import Image
import requests
from slugify import slugify
import xmltodict


file_loader = FileSystemLoader('templates')
env = Environment(loader=file_loader)

def download_audio_files(url, settings):
    url_path = urlparse(url).path
    file_name = os.path.basename(url_path)
    file_path = os.path.join(settings['output_dir'], 'audio', file_name)
    if not os.path.exists(file_path):
        r = requests.get(url, allow_redirects=True)
        open(file_path, 'wb').write(r.content)
    file_url = settings['site_url'] + '/audio/' + file_name
    return file_url


def download_cover_art(url, settings):
    url_path = urlparse(url).path
    file_name = os.path.basename(url_path)
    file_path = os.path.join(settings['output_dir'], file_name)
    if not os.path.exists(file_path):
        r = requests.get(url, allow_redirects=True)
        open(file_path, 'wb').write(r.content)
    file_url = settings['site_url'] + '/' + file_name
    return file_url



def get_podcast(rss_url, settings):
    r = requests.get(rss_url)
    xml_dict = xmltodict.parse(r.text)
    podcast = {}
    podcast['rss_url'] = rss_url
    podcast['cover_art_url'] = xml_dict['rss']['channel']['itunes:image']['@href']
    podcast['title'] = xml_dict['rss']['channel']['title']
    podcast['description'] = xml_dict['rss']['channel']['description']
    podcast['episodes'] = get_episodes(xml_dict, settings)

    if settings['archive']:
        podcast['cover_art_url'] = download_cover_art(podcast['cover_art_url'], settings)
    
    #print(json.dumps(podcast, indent=4))
    return podcast

def get_episodes(xml_dict, settings):
    episodes = []
    for item in xml_dict['rss']['channel']['item']:
        if 'enclosure' in item:
            episode = {}
            pubDate = parsedate_to_datetime(item['pubDate'])
            episode['date'] = pubDate.strftime("%Y-%m-%d")
            episode['description'] = item['description']
            episode['description'] = markdown(episode['description'], extensions=["mdx_linkify"])
            episode['title'] = item['title']
            episode['enclosure_url'] = item['enclosure']['@url']
            episode['slug'] = slugify(item['title'])

            if settings['archive']:
                episode['enclosure_url'] = download_audio_files(episode['enclosure_url'], settings)
                print(episode['enclosure_url'])

            episodes.append(episode)
    return episodes


def render_home(podcast, settings):
    file_path = os.path.join(settings['output_dir'], '_index.html')

    template = env.get_template('home.html')
    output = template.render(podcast=podcast, settings=settings)
    with open(file_path, 'w') as f:
        f.write(output)



def render_episode(episode, settings):
    file_name = episode['slug'] + ".html"
    file_path = os.path.join(settings['output_dir'], 'episodes', file_name)
    template = env.get_template('episode.html')
    output = template.render(episode=episode, settings=settings)
    with open(file_path, 'w') as f:
        f.write(output)

settings_file = sys.argv[1]
with open(settings_file) as f:
    settings = json.load(f)

podcast = get_podcast(settings['rss_url'], settings)
render_home(podcast, settings)
for episode in podcast['episodes']:
    render_episode(episode, settings)