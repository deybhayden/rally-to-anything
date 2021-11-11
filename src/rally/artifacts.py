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
            "project": rally_artifact.Project.Name,
            "type": rally_artifact._type,
            "state": rally_artifact.FlowState.Name,
            "priority": rally_artifact.Priority,
            "components": rally_artifact.Components,
            "formattedId": rally_artifact.FormattedID,
            "description": rally_artifact.Description,
            "discussion": [
                {
                    "user": comment.User,
                    "text": comment.Text,
                }
                for comment in rally_artifact.Discussion
            ],
        }

        return artifact


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
        return os.path.join(self.output_root, self.relative_path, self.FormattedID)

    def json(self):
        return json.dumps(self, cls=RallyArtifactJSONSerializer)

    def write_to_disk(self):
        return json.dump(self, cls=RallyArtifactJSONSerializer, )

    @property
    def number_of_attachments(self):
        return len(self.Attachments)

    def attachments(self):
        for attachment in self.Attachments:
            attachment = RallyAttachment(attachment)
            yield attachment
