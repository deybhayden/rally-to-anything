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

        self.artifacts = []
        for section_name, section in config["rally"]["artifacts"].items():
            self.artifacts += [
                RallyArtifact(config, artifact, section_name)
                for artifact in self._get_artifacts(section_name, section)
            ]

    def _get_artifacts(self, section_name, section):
        before = time.time()
        kwargs = {"query": section["query"], "threads": section["threads"]}
        artifacts = self.sdk.get(
            section["entity"],
            fetch=True,
            projectScopeDown=True,
            **kwargs,
        )
        after = time.time()
        if self.verbose:
            print(artifacts)
            print(f"{section_name} loaded in {after - before:.2f} seconds")

        return artifacts
