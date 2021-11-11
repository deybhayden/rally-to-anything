import time

import pyral
import tqdm

from .artifacts import RallyArtifact
# from .portfolio_items import RallyPortfolioItem


class Rally(object):
    def __init__(self, config, verbose):
        self._config = config
        before = time.time()
        self.sdk = pyral.Rally(
            server=config["rally"]["sdk"]["server"],
            apikey=config["rally"]["sdk"]["api_key"],
            workspace=config["rally"]["sdk"]["workspace"],
            project=config["rally"]["sdk"].get("project"),
        )
        after = time.time()
        if verbose:
            print(f"Rally SDK initialized in {after - before:.2f} seconds")

        before = time.time()
        self.artifacts = [
            RallyArtifact(artifact) for artifact in tqdm.tqdm(self._get_artifacts(), desc="Artifacts")
        ]
        after = time.time()
        if verbose:
            print(f"Artifacts loaded in {after - before:.2f} seconds")

        # self.portfolio_items = [
        #     RallyPortfolioItem(item) for item in tqdm.tqdm(self._get_portfolio_items(), desc="Portfolio Items")
        # ]

    def _get_artifacts(self):
        limit = self._config["rally"]["artifacts"].get("limit")
        return self.sdk.get("Artifact", fetch=True, projectScopeDown=True, limit=limit)

    def _get_portfolio_items(self):
        return self.sdk.get("PortfolioItem", fetch=True, projectScopeDown=True)
