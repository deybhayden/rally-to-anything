import functools
import json
import os

from .attachments import RallyAttachment


class RallyArtifactJSONSerializer(json.JSONEncoder):
    def default(self, obj):
        json_encoder = functools.partial(json.JSONEncoder.default, self)
        if isinstance(obj, RallyArtifact):
            json_encoder = self._encode_rally_artifact_as_json

        return json_encoder(obj)

    def _encode_rally_artifact_as_json(self, rally_artifact):

        artifact = {
            "objectId": rally_artifact.ObjectID,
            "project": rally_artifact.Project.Name,
            "name": rally_artifact.Name,
            "type": rally_artifact._type,
            "state": rally_artifact.FlowState.Name,
            "scheduleState": rally_artifact.ScheduleState,
            "iteration": self._get_iteration(rally_artifact),
            "blocked": rally_artifact.Blocked,
            "blockedReason": rally_artifact.BlockedReason,
            "blocker": rally_artifact.Blocker,
            "priority": rally_artifact.Priority,
            "component": rally_artifact.Component,
            "formattedId": rally_artifact.FormattedID,
            "description": rally_artifact.Description,
            "notes": rally_artifact.Notes,
            "milestones": rally_artifact.Milestones,
            "acceptanceCriteria": rally_artifact.AcceptanceCriteria,
            "createdBy": rally_artifact.CreatedBy.UserName,
            "creationDate": rally_artifact.CreationDate,
            "owner": rally_artifact.Owner.UserName if rally_artifact.Owner else None,
            "planEstimate": rally_artifact.PlanEstimate,
            "portfolioItem": self._get_porfolio_item(rally_artifact),
            "discussion": [
                {
                    "user": comment.User,
                    "text": comment.Text,
                }
                for comment in rally_artifact.Discussion
            ],
        }

        return artifact

    def _get_porfolio_item(self, rally_artifact):
        if rally_artifact.PortfolioItem:
            return {
                "objectId": rally_artifact.PortfolioItem.ObjectID,
                "formattedId": rally_artifact.PortfolioItem.FormattedID,
                "type": rally_artifact.PortfolioItem.PortfolioItemTypeName,
            }

    def _get_iteration(self, rally_artifact):
        if rally_artifact.Iteration:
            return {
                "name": rally_artifact.Iteration.Name,
            }


class RallyArtifact(object):

    output_root = os.path.join(".", "rally-to-anything", "rally", "artifacts")

    def __init__(
        self,
        artifact,
    ):
        self._artifact = artifact

    def __getattr__(self, attribute):
        return getattr(self._artifact, attribute)

    @property
    def relative_path(self):
        return self._ref.replace(self.server, "")

    @property
    def disk_path(self):
        return os.path.join(self.output_root, self.relative_path, self.ObjectID)

    def json(self):
        return json.dumps(self, cls=RallyArtifactJSONSerializer)

    def write_to_disk(self):
        os.makedirs(os.path.dirname(self.disk_path), exist_ok=True)
        with open(self.disk_path, "wb") as f:
            return json.dump(self, f, cls=RallyArtifactJSONSerializer)

    @property
    def number_of_attachments(self):
        return len(self.Attachments)

    def attachments(self):
        for attachment in self.Attachments:
            attachment = RallyAttachment(attachment)
            yield attachment
