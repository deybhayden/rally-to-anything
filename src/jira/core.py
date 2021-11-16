import json
import os
import time

from jira import JIRA

from ..rally.artifacts import RallyArtifact

# from ..rally.attachments import RallyAttachment


class Jira(object):
    def __init__(self, config, verbose):
        self._config = config
        self.verbose = verbose
        before = time.time()
        self.sdk = JIRA(
            config["jira"]["sdk"]["server"],
            basic_auth=(
                config["jira"]["sdk"]["email"],
                config["jira"]["sdk"]["api_token"],
            ),
        )
        after = time.time()
        if self.verbose:
            print(f"JIRA SDK initialized in {after - before:.2f} seconds")

        self.rally_artifacts = self.load_rally_artifacts()

    def load_rally_artifacts(self):
        rally_artifacts = []
        for (dirpath, _, files) in os.walk(RallyArtifact.output_root):
            for filepath in files:
                with open(os.path.join(dirpath, filepath), "r") as f:
                    rally_artifacts.append(json.load(f))
        return rally_artifacts

    def migrate_rally_artifacts(self):
        pass

    def build_jira_issues(self):
        pass
