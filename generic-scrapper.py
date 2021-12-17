import re
import yaml
from time import sleep
from selenium import webdriver
from bs4 import BeautifulSoup
from requests_html import HTMLSession


def download_url(url, save_path):
    response = session.get(url, stream=True)
    response.raise_for_status()

    if save_path.lower().endswith('pdf'):
        with open(save_path, 'wb') as save_fp:
            save_fp.write(response.content)
    else:
        with open(save_path, 'w', encoding='utf-8') as save_fp:
            save_fp.write(response.text)


def extract_links(text, download, type, value):
    sleep(2)
    soup = BeautifulSoup(text, 'lxml')
    links = []
    if type == 'id':
        links = [link['href'] if link['href'].startswith('http') else base_url + link['href']
                 for link in soup.find_all('a', id=value)]
    elif type == 'class':
        links = [link['href'] if link['href'].startswith('http') else base_url + link['href']
                 for link in soup.find_all('a', class_=value)]
    elif type == 'regex':
        for link in soup.find_all('a'):
            if link.has_attr('href') and re.search(value, link['href']):
                if link['href'].startswith('http'):
                    links.append(link['href'])
                else:
                    links.append(base_url + link['href'])
    if download:
        for link in set(links):
            save_path = link.split('/')[-1].replace('%20', ' ').replace('%28', '(').\
                replace('%29', ')').replace('%E2%80%93', '–').replace('%24', '$')
            download_url(link, save_path)

    return links


def extract_content_from_tag(text, tag, attr, value):
    sleep(2)
    soup = BeautifulSoup(text, 'lxml')
    return str(soup.find(tag, attrs={attr: value}))


if __name__ == '__main__':
    try:
        with open("config.yaml", 'r') as stream:
            config = yaml.safe_load(stream)['step_config']
    except Exception as e:
        print(e)
        exit(-1)

    driver_map = {'id': 'find_element_by_id', 'class': 'find_element_by_class_name',
                  'xpath': 'find_element_by_xpath', 'name': 'find_element_by_name'}

    base_url = '/'.join(config['url'].split('/')[:3])
    session = HTMLSession()

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.get(config['url'])

    if config['act1']['type'] == 'search':
        search_box = \
            getattr(driver, driver_map[config['act1']['searchType']])(config['act1']['searchValue'])
        search_box.send_keys(config['act1']['search_text'])
        driver.implicitly_wait(10)
        submit_button = \
            getattr(driver, driver_map[config['act1']['submitType']])(config['act1']['submitValue'])
        submit_button.click()
        driver.implicitly_wait(10)

        if 'act2' in config and config['act2']['type'] == 'getlinks':
            sleep(2)
            links = extract_links(driver.page_source, False, config['act2']['searchType'],
                                  config['act2']['searchValue'])

            if 'act3' in config and config['act3']['type'] == 'download':
                for link in links:
                    driver.get(link)
                    driver.implicitly_wait(10)
                    sublinks = extract_links(driver.page_source, True, config['act3']['searchType'],
                                             config['act3']['searchValue'])

    elif config['act1']['type'] == 'download':
        sublinks = extract_links(driver.page_source, True, config['act1']['searchType'],
                                 config['act1']['searchValue'])

    elif config['act1']['type'] == 'getlinks':
        if "filterContent" in config['act1'] and config['act1']['filterContent']:
            content = \
                extract_content_from_tag(driver.page_source, config['act1']['filterTag'],
                                         config['act1']['filterAttr'], config['act1']['filterValue'])
        else:
            content = driver.page_source

        links = extract_links(content, False, config['act1']['searchType'],
                              config['act1']['searchValue'])

        if 'act2' in config and config['act2']['type'] == 'download':
            for link in links:
                driver.get(link)
                driver.implicitly_wait(10)
                sublinks = extract_links(driver.page_source, True, config['act2']['searchType'],
                                         config['act2']['searchValue'])

    driver.close()
    driver.quit()
    exit(0)