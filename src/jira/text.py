import re
from urllib.parse import urlparse

import html2jira

HYPERLINK_RE = re.compile(
    r"(?P<url>https?://[^\s]+)",
)


class RallyTextTranslator(object):
    def __init__(self, config):
        self._config = config
        self.zendesk_domain = urlparse(self._config["zendesk"]["sdk"]["server"]).netloc

    def rally_html_to_jira(self, html):
        # bodywidth set to 0 so no wrapping
        h = html2jira.HTML2Jira(bodywidth=0)
        # Reduce the amount of inline links/images in text & comments
        h.ignore_links = True
        h.ignore_images = True
        plaintext = h.handle(html).strip()
        zendesk_tickets = self.find_zendesk_tickets(plaintext)
        return (plaintext, zendesk_tickets)

    def find_zendesk_tickets(self, text):
        zendesk_tickets = []

        for link in HYPERLINK_RE.finditer(text):
            ticket_no = self._get_ticket_no(link)
            if ticket_no:
                zendesk_tickets.append(ticket_no)

        return zendesk_tickets

    def _get_ticket_no(self, match):
        urlparts = urlparse(match.group())
        if urlparts.netloc == self.zendesk_domain:
            (_, ticket_no) = urlparts.path.rsplit("/", 1)
            return ticket_no
