import time

import pyral

from .artifacts import RallyArtifact


class Rally(object):
    def __init__(self, config, verbose):
        self._config = config
        self.verbose = verbose
        before = time.time()
        self.sdk = pyral.Rally(
            server=config["rally"]["sdk"]["server"],
            apikey=config["rally"]["sdk"]["api_key"],
            workspace=config["rally"]["sdk"]["workspace"],
            project=config["rally"]["sdk"].get("project"),
        )
        after = time.time()
        if self.verbose:
            print(f"Rally SDK initialized in {after - before:.2f} seconds")

        self.artifacts = [RallyArtifact(artifact) for artifact in self._get_artifacts()]

    def _get_artifacts(self):
        before = time.time()
        artifacts = self.sdk.get(
            "Artifact",
            fetch=True,
            projectScopeDown=True,
            **self._config["rally"]["artifacts"],
        )
        after = time.time()
        if self.verbose:
            print(artifacts)
            print(f"Artifacts loaded in {after - before:.2f} seconds")

        return artifacts
