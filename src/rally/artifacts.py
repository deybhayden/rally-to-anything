import functools
import json
import os

import tqdm
from pyral.entity import UnreferenceableOIDError

from .attachments import RallyAttachment


def _format_user(user):
    """Return a User Dictionary if the User is still a valid entity in Rally."""
    try:
        return {
            "emailAddress": user.EmailAddress,
            "firstName": user.FirstName,
            "lastName": user.LastName,
        }
    except UnreferenceableOIDError:
        return {"name": user.Name}
    except UnreferenceableOIDError:
        return


class RallyArtifactJSONSerializer(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        self.download_attachments = kwargs.pop("download_attachments", False)
        self.force_cache = kwargs.pop("force_cache", False)
        super(RallyArtifactJSONSerializer, self).__init__(*args, **kwargs)

    def default(self, obj):
        json_encoder = functools.partial(json.JSONEncoder.default, self)
        if isinstance(obj, RallyArtifact):
            json_encoder = self._encode_rally_artifact_as_json

        return json_encoder(obj)

    def _encode_rally_artifact_as_json(
        self, rally_artifact, recurse_parent=True, recurse_children=True
    ):
        artifact = {
            "objectId": rally_artifact.ObjectID,
            "project": rally_artifact.Project.Name,
            "name": rally_artifact.Name,
            "release": self._get_release(rally_artifact),
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
            "dragAndDropRank": rally_artifact._get_or_none("DragAndDropRank"),
            "environment": rally_artifact._get_or_none("Environment"),
            "attachments": self._get_attachments(rally_artifact),
            "discussion": [
                {
                    "user": _format_user(comment.User),
                    "text": comment.Text,
                    "creationDate": comment.CreationDate,
                }
                for comment in rally_artifact.Discussion
            ],
        }

        if recurse_parent:
            artifact["parent"] = self._get_parent(rally_artifact)

        if recurse_children:
            for (key, attr) in (
                ("children", "Children"),
                ("stories", "UserStories"),
                ("tasks", "Tasks"),
            ):
                if hasattr(rally_artifact, attr):
                    artifact[key] = self._get_children(rally_artifact, attr=attr)

        artifact.update(**self._get_custom_fields(rally_artifact))

        return artifact

    def _get_attachments(self, rally_artifact):
        json_attachments = []
        for attachment in tqdm.tqdm(
            rally_artifact.attachments(),
            desc="Attachments",
            total=rally_artifact.number_of_attachments,
            disable=rally_artifact.number_of_attachments == 0,
        ):
            if self.download_attachments:
                attachment.cache_to_disk(self.force_cache)

            json_attachments.append(
                {
                    "name": attachment.Name,
                    "user": _format_user(attachment.User),
                    "creationDate": attachment.CreationDate,
                    "objectId": attachment.ObjectID,
                    "description": attachment.Description,
                }
            )
        return json_attachments

    def _get_blocker(self, rally_artifact):
        blocker = rally_artifact._get_or_none("Blocker")
        if blocker:
            return {
                "objectId": blocker.ObjectID,
                "name": blocker.Name,
                "blockedBy": _format_user(blocker.BlockedBy),
                "creationDate": blocker.CreationDate,
            }

    def _get_children(self, rally_artifact, attr="Children"):
        encoded_children = []
        children = rally_artifact._get_or_none(attr)
        if children:
            for child in children:
                child_artifact = RallyArtifact(
                    rally_artifact._config, child, rally_artifact._artifact_directory
                )
                encoded_children.append(
                    self._encode_rally_artifact_as_json(
                        child_artifact, recurse_parent=False
                    )
                )
        return encoded_children

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

    def _get_parent(self, rally_artifact):
        parent = rally_artifact._get_or_none("Parent")
        if parent:
            parent_artifact = RallyArtifact(
                rally_artifact._config, parent, rally_artifact._artifact_directory
            )
            return self._encode_rally_artifact_as_json(
                parent_artifact, recurse_children=False
            )

    def _get_release(self, rally_artifact):
        artifact = rally_artifact._get_or_none("Release")
        if artifact:
            return {
                "objectId": artifact.ObjectID,
                "name": artifact.Name,
                "creationDate": artifact.CreationDate,
                "releaseStartDate": artifact.ReleaseStartDate,
                "releaseDate": artifact.ReleaseDate,
                "state": artifact.State,
                "planEstimate": artifact.PlanEstimate,
                "plannedVelocity": artifact.PlannedVelocity,
                "theme": artifact.Theme,
            }

    def _get_state(self, rally_artifact):
        state = rally_artifact._get_or_none("State")
        if state:
            return state.Name if hasattr(state, "Name") else state

    def _get_custom_fields(self, rally_artifact):
        fields = {}

        client_names = rally_artifact._get_or_none("c_ClientName")
        if client_names:
            fields["clientNames"] = [c.value for c in client_names]

        if rally_artifact._type == "Defect":
            fields["defectDetails"] = {
                "actualResults": rally_artifact.ActualResults,
                "expectedResults": rally_artifact.ExpectedResults,
                "rootCause": rally_artifact.RootCause,
                "siteURL": rally_artifact.SiteURL,
                "stepsToReproduce": rally_artifact.StepstoReproduce,
            }

        return fields


class RallyArtifact(object):
    def __init__(self, config, artifact, artifact_directory):
        self._config = config
        self._artifact = artifact
        self._artifact_directory = artifact_directory

    def __getattr__(self, attribute):
        return getattr(self._artifact, attribute)

    def _get_or_none(self, attr):
        return getattr(self._artifact, attr, None)

    @staticmethod
    def output_root(config):
        return os.path.join(config["rally"]["output_root"], "artifacts")

    @property
    def disk_path(self):
        return os.path.join(
            self.output_root(self._config),
            self._artifact_directory,
            f"{self.ObjectID}.json",
        )

    @property
    def is_on_disk(self):
        return os.path.exists(self.disk_path)

    def json(self):
        return json.dumps(self, cls=RallyArtifactJSONSerializer)

    def cache_to_disk(self, download_attachments=False, force=False):
        if not self.is_on_disk or force:
            os.makedirs(os.path.dirname(self.disk_path), exist_ok=True)
            with open(self.disk_path, "w") as f:
                return json.dump(
                    self,
                    f,
                    cls=RallyArtifactJSONSerializer,
                    download_attachments=download_attachments,
                    force_cache=force,
                )

    @property
    def number_of_attachments(self):
        return len(self.Attachments)

    def attachments(self):
        for attachment in self.Attachments:
            attachment = RallyAttachment(self._config, attachment)
            yield attachment
