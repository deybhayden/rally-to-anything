import re
from urllib.parse import urlparse

HYPERLINK_RE = re.compile(
    r"(?P<url>https?://[^\s]+)",
)


class RallyLinkTranslator(object):
    def __init__(self, config):
        self._config = config
        self.zendesk_domain = urlparse(self._config["zendesk"]["sdk"]["server"]).netloc

    def find_zendesk_tickets(self, issue):
        zendesk_tickets = []

        for link in HYPERLINK_RE.finditer(issue["description"]):
            ticket_no = self._get_ticket_no(link)
            if ticket_no:
                zendesk_tickets.append(ticket_no)

        for comment in issue["comments"]:
            for link in HYPERLINK_RE.finditer(comment["body"]):
                ticket_no = self._get_ticket_no(link)
                if ticket_no:
                    zendesk_tickets.append(ticket_no)

        return zendesk_tickets

    def _get_ticket_no(self, match):
        urlparts = urlparse(match.group())
        if urlparts.netloc == self.zendesk_domain:
            (_, ticket_no) = urlparts.path.rsplit("/", 1)
            return ticket_no
