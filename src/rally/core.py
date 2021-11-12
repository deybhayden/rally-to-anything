import time

import pyral

from .artifacts import RallyArtifact

# from .portfolio_items import RallyPortfolioItem


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

        # self.portfolio_items = [
        #     RallyPortfolioItem(item) for item in self._get_portfolio_items()
        # ]

    def _get_artifacts(self):
        before = time.time()
        kwargs = {
            "query": self._config["rally"]["artifacts"].get("query"),
            "limit": self._config["rally"]["artifacts"].get("limit"),
            "threads": self._config["rally"]["artifacts"].get("threads"),
        }
        artifacts = self.sdk.get(
            "Artifact", fetch=True, projectScopeDown=True, **kwargs
        )
        after = time.time()
        if self.verbose:
            print(f"Artifacts loaded in {after - before:.2f} seconds")

        return artifacts

    def _get_portfolio_items(self):
        return self.sdk.get("PortfolioItem", fetch=True, projectScopeDown=True)
