import functools
import json
import os

from pyral.entity import UnreferenceableOIDError

from .attachments import RallyAttachment


def _format_user(user):
    """Return a User Dictionary if the User is still a valid entity in Rally."""
    try:
        return {"userName": user.UserName, "displayName": user.DisplayName}
    except UnreferenceableOIDError:
        return {"name": user.Name}
    except UnreferenceableOIDError:
        return


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
            "scheduleState": rally_artifact._get_or_none("ScheduleState"),
            "iteration": self._get_iteration(rally_artifact),
            "blocked": rally_artifact.Blocked,
            "blockedReason": rally_artifact.BlockedReason,
            "blocker": self._get_blocker(rally_artifact),
            "priority": rally_artifact._get_or_none("Priority"),
            "component": rally_artifact._get_or_none("Component"),
            "formattedId": rally_artifact.FormattedID,
            "description": rally_artifact.Description,
            "notes": rally_artifact.Notes,
            "milestones": self._get_milestones(rally_artifact),
            "acceptanceCriteria": rally_artifact._get_or_none("AcceptanceCriteria"),
            "createdBy": _format_user(rally_artifact.CreatedBy),
            "creationDate": rally_artifact.CreationDate,
            "owner": self._get_owner(rally_artifact),
            "planEstimate": rally_artifact._get_or_none("PlanEstimate"),
            "portfolioItem": self._get_porfolio_item(rally_artifact),
            "dragAndDropRank": rally_artifact._get_or_none("DragAndDropRank"),
            "discussion": [
                {
                    "user": _format_user(comment.User),
                    "text": comment.Text,
                }
                for comment in rally_artifact.Discussion
            ],
        }

        return artifact

    def _get_blocker(self, rally_artifact):
        blocker = rally_artifact._get_or_none("Blocker")
        if blocker:
            return {
                "objectId": blocker.ObjectID,
                "name": blocker.Name,
                "blockedBy": _format_user(blocker.BlockedBy),
                "creationDate": blocker.CreationDate,
            }

    def _get_iteration(self, rally_artifact):
        iteration = rally_artifact._get_or_none("Iteration")
        if iteration:
            return {
                "objectId": iteration.ObjectID,
                "name": iteration.Name,
                "creationDate": iteration.CreationDate,
                "startDate": iteration.StartDate,
                "endDate": iteration.EndDate,
                "state": iteration.State,
                "planEstimate": iteration.PlanEstimate,
                "plannedVelocity": iteration.PlannedVelocity,
                "theme": iteration.Theme,
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
            return _format_user(rally_artifact.Owner)

    def _get_porfolio_item(self, rally_artifact):
        portfolio_item = rally_artifact._get_or_none("PortfolioItem")
        if portfolio_item:
            return {
                "objectId": portfolio_item.ObjectID,
                "formattedId": portfolio_item.FormattedID,
                "type": portfolio_item.PortfolioItemTypeName,
            }

    def _get_state(self, rally_artifact):
        state = rally_artifact._get_or_none("State")
        if state:
            return state.Name if hasattr(state, "Name") else state


class RallyArtifact(object):

    output_root = os.path.join(".", "rally-to-anything", "rally", "artifacts")

    def __init__(
        self,
        artifact,
    ):
        self._artifact = artifact

    def __getattr__(self, attribute):
        return getattr(self._artifact, attribute)

    def _get_or_none(self, attr):
        return getattr(self._artifact, attr, None)

    @property
    def disk_path(self):
        return os.path.join(self.output_root, f"{self.ObjectID}.json")

    @property
    def is_on_disk(self):
        return os.path.exists(self.disk_path)

    def json(self):
        return json.dumps(self, cls=RallyArtifactJSONSerializer)

    def cache_to_disk(self, force=False):
        if not self.is_on_disk or force:
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
