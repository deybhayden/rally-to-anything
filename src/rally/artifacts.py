import functools
import json
import os

from .attachments import RallyAttachment


def _get_or_none(rally_artifact, attr):
    return getattr(rally_artifact, attr, None)


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
            "state": self._get_state(rally_artifact),
            "scheduleState": _get_or_none(rally_artifact, "ScheduleState"),
            "iteration": self._get_iteration(rally_artifact),
            "blocked": rally_artifact.Blocked,
            "blockedReason": rally_artifact.BlockedReason,
            "blocker": rally_artifact.Blocker,
            "priority": _get_or_none(rally_artifact, "Priority"),
            "component": rally_artifact.Component,
            "formattedId": rally_artifact.FormattedID,
            "description": rally_artifact.Description,
            "notes": rally_artifact.Notes,
            "milestones": self._get_milestones(rally_artifact),
            "acceptanceCriteria": _get_or_none(rally_artifact, "AcceptanceCriteria"),
            "createdBy": self._format_user(rally_artifact.CreatedBy),
            "creationDate": rally_artifact.CreationDate,
            "owner": self._get_owner(rally_artifact),
            "planEstimate": _get_or_none(rally_artifact, "PlanEstimate"),
            "portfolioItem": self._get_porfolio_item(rally_artifact),
            "discussion": [
                {
                    "user": self._format_user(comment.User),
                    "text": comment.Text,
                }
                for comment in rally_artifact.Discussion
            ],
        }

        return artifact

    def _format_user(self, user):
        return {"userName": user.UserName, "displayName": user.DisplayName}

    def _get_iteration(self, rally_artifact):
        iteration = _get_or_none(rally_artifact, "Iteration")
        if iteration:
            return {
                "name": iteration.Name,
            }

    def _get_milestones(self, rally_artifact):
        return [
            {
                "formattedId": milestone.FormattedID,
                "objectId": milestone.ObjectID,
                "name": milestone.Name,
                "targetDate": milestone.TargetDate,
            }
            for milestone in rally_artifact.Milestones
        ]

    def _get_owner(self, rally_artifact):
        if rally_artifact.Owner:
            return self._format_user(rally_artifact.Owner)

    def _get_porfolio_item(self, rally_artifact):
        portfolio_item = _get_or_none(rally_artifact, "PortfolioItem")
        if portfolio_item:
            return {
                "objectId": portfolio_item.ObjectID,
                "formattedId": portfolio_item.FormattedID,
                "type": portfolio_item.PortfolioItemTypeName,
            }

    def _get_state(self, rally_artifact):
        flow_state = _get_or_none(rally_artifact, "FlowState")
        if flow_state:
            return flow_state.Name


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
    def disk_path(self):
        return os.path.join(self.output_root, f"{self.ObjectID}.json")

    @property
    def is_on_disk(self):
        return os.path.exists(self.disk_path)

    def json(self):
        return json.dumps(self, cls=RallyArtifactJSONSerializer)

    def cache_to_disk(self, force=False):
        if not self.is_on_disk and not force:
            os.makedirs(os.path.dirname(self.disk_path), exist_ok=True)
            with open(self.disk_path, "w") as f:
                return json.dump(self, f, cls=RallyArtifactJSONSerializer)

    @property
    def number_of_attachments(self):
        return len(self.Attachments)

    def attachments(self):
        for attachment in self.Attachments:
            attachment = RallyAttachment(attachment)
            yield attachment
