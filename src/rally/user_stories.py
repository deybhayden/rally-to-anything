import base64
import functools
import json
import os

import pyral
import tqdm


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

    output_root = os.path.join(".", "rally-to-clubhouse", "rally")

    def __init__(
        self,
        artifact,
    ):
        self._artifact = artifact

    def __getattr__(self, attribute):
        return getattr(self._artifact, attribute)

    def json(self):
        return json.dumps(self, cls=RallyArtifactJSONSerializer)

    @property
    def number_of_attachments(self):
        return len(self.Attachments)

    def attachments(self):
        for attachment in self.Attachments:
            attachment = RallyAttachment(attachment)
            yield attachment


class RallyAttachment(object):

    server = "https://rally1.rallydev.com/"
    output_root = os.path.abspath(
        os.path.join(".", "rally-to-clubhouse", "rally", "assets")
    )

    def __init__(self, attachment):
        self._attachment = attachment

        os.makedirs(self.output_root, exist_ok=True)
        self._cache_to_disk()

    def __getattr__(self, attribute):
        return getattr(self._attachment, attribute)

    @property
    def relative_path(self):
        return self._ref.replace(self.server, "")

    @property
    def disk_path(self):
        return os.path.join(self.output_root, self.relative_path, self.Name)

    @property
    def is_on_disk(self):
        return os.path.exists(self.disk_path)

    def _cache_to_disk(self, force=False):
        if not self.is_on_disk and not force:
            os.makedirs(os.path.dirname(self.disk_path), exist_ok=True)
            with open(self.disk_path, "wb") as f:
                f.write(base64.b64decode(self._attachment.Content.Content))

        self._attachment.Content.Content = ""
        self._attachment.Content._hydrated = False


class Rally(object):
    def __init__(self, config):
        self.sdk = pyral.Rally(
            server=config["rally"]["sdk"]["server"],
            apikey=config["rally"]["sdk"]["api_key"],
            workspace=config["rally"]["sdk"]["workspace"],
        )
        self.artifacts = [
            RallyArtifact(artifact) for artifact in tqdm.tqdm(self._get_artifacts())
        ]
        self.defects = []

    def _get_artifacts(self):
        return self.sdk.get("Artifact", fetch=True, projectScopeDown=True)

    def _get_defects(self):
        return self.sdk.get("Defect", fetch=True, projectScopeDown=True)

    def cache_to_disk(self):
        pass