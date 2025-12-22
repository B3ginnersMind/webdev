import logging, requests
from html.parser import HTMLParser
from urllib.parse import urljoin

class LinkParser(HTMLParser):
    def __init__(self, base_url, prefix):
        super().__init__()
        self.base_url = base_url
        self.prefix = prefix
        self.links = []

    def handle_starttag(self, tag, attrs):
        """
        Handle start tags <a ..> in HTML and collect links that match the prefix.
        attrs: list of (attribute, value) tuples
        urljoin is used to form absolute URLs from relative ones.
        """
        if tag == "a":
            for k, v in attrs:  # look for href attributes
                if k == "href":
                    full_url = urljoin(self.base_url, v)
                    if full_url.startswith(self.prefix):
                        self.links.append(full_url)

def get_extension_link(url: str, prefix: str) -> str | None:
    """
    Find download link for an extension matching the given prefix.
    Note: this approach does not work for Mediawikie releases (403)!
    :param url: webpage to parse
    :param prefix: prefix to match links against
    :return: download link or None
    """
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        html = resp.text
    except requests.RequestException as e:
        logging.warning("Failed to fetch %s: %s", url, e)
        return None

    parser = LinkParser(url, prefix)
    parser.feed(html)
    if len(parser.links) > 1:
        logging.warning("Multiple links found for prefix %s", prefix)
    if parser.links:
        logging.info("Found archive: %s", parser.links[0])
        return parser.links[0]
    return None
