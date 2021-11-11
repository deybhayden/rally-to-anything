import functools
import json
import os

from .attachments import RallyAttachment


class RallyPortfolioItemJSONSerializer(json.JSONEncoder):
    def default(self, obj):
        json_encoder = functools.partial(json.JSONEncoder.default, self)
        if isinstance(obj, RallyPortfolioItem):
            json_encoder = self._encode_rally_portfolio_item_as_json

        return json_encoder(obj)

    def _encode_rally_portfolio_item_as_json(self, rally_portfolio_item):

        portfolio_item = {
            "project": rally_portfolio_item.Project.Name,
            "type": rally_portfolio_item._type,
            "state": rally_portfolio_item.FlowState.Name,
            "formattedId": rally_portfolio_item.FormattedID,
            "description": rally_portfolio_item.Description,
            "discussion": [
                {
                    "user": comment.User,
                    "text": comment.Text,
                }
                for comment in rally_portfolio_item.Discussion
            ],
        }

        return portfolio_item


class RallyPortfolioItem(object):

    output_root = os.path.join(".", "rally-to-anything", "rally")

    def __init__(
        self,
        portfolio_item,
    ):
        self._portfolio_item = portfolio_item

    def __getattr__(self, attribute):
        return getattr(self._portfolio_item, attribute)

    def json(self):
        return json.dumps(self, cls=RallyPortfolioItemJSONSerializer)

    def write_to_disk(self):
        return json.dumps(self, cls=RallyPortfolioItemJSONSerializer)

    @property
    def number_of_attachments(self):
        return len(self.Attachments)

    def attachments(self):
        for attachment in self.Attachments:
            attachment = RallyAttachment(attachment)
            yield attachment
