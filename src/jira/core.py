import json
import os
import time

from jira import JIRA

from ..rally.artifacts import RallyArtifact

from ..rally.attachments import RallyAttachment


class RallyAttachmentTranslator(object):
    def __init__(self, artifact):
        self.artifact = artifact
        self.url_prefix = f"/slm/attachment/{artifact['objectId']}"

    @property
    def attachment_dirpath(self):
        os.path.join(
            RallyAttachment.output_root,
            "slm",
            "webservice",
            "v2.0",
            "attachment",
            self.artifact["objectId"],
        )

    @property
    def has_attachments(self):
        return os.path.exists(self.attachment_dirpath)

    def add_attachments(self, issue):
        if self.has_attachments:
            issue["attachments"] = []
            for (dirpath, _, files) in os.walk(self.attachment_dirpath):
                issue["attachments"].extend([os.path.join(dirpath, f) for f in files])

    # def replace_attachments(self, text):
    #     if text.find(self.url_prefix):


class RallyArtifactTranslator(object):
    def __init__(self, config):
        self._config = config

    def create_issue(self, artifact):
        attachment_translator = RallyAttachmentTranslator(artifact)
        issue = {
            "project": self._config["jira"]["project"],
            "issuetype": {
                "name": self._config["jira"]["mappings"]["artifacts"][artifact["type"]]
            },
            "summary": f"{artifact['formattedId']} - {artifact['name']}",
            "description": f"{artifact['description']}\n{artifact['notes']}",
            "components": self._get_components(artifact),
            "comments": self._get_comments(artifact),
            "priority": self._config["jira"]["mappings"]["priority"].get(
                artifact["priority"]
            ),
            "labels": self._get_labels(artifact),
            "reporter": {"name": artifact["createdBy"]["userName"]},
            "assignee": {"name": artifact["owner"]["userName"]},
        }

        attachment_translator.add_attachments(issue)

        return issue

    def _add_attachments(self, issue):
        attachment_translator = RallyAttachmentTranslator(issue)
        attachments = attachment_translator.find_attachments()
        issue["attachments"] = attachments

    def _get_comments(self, artifact):
        return [
            {"body": d["text"], "author": d["user"]} for d in artifact["discussion"]
        ]

    def _get_components(self, artifact):
        components = []
        if artifact["component"]:
            if isinstance(artifact["component"], list):
                components = [{"name": c} for c in artifact["component"]]
            else:
                components.append({"name": artifact["component"]})

        return components

    def _get_labels(self, artifact):
        labels = []
        for field in self._config["jira"]["mappings"]["labels"]["fields"]:
            value = artifact.get(field)
            if value:
                if isinstance(value, list):
                    labels.extend(value)
                else:
                    labels.append(value)
        return labels


class JiraMigrator(object):
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

    def migrate_rally_artifact(self, artifact):
        jira_mapping = self.build_jira_mapping(artifact)
        epic_id = None
        issue_keys = []
        if jira_mapping["parent"]:
            parent_issue = self._sdk_create_issue(jira_mapping["parent"])
            if parent_issue.fields.issuetype == "Epic":
                epic_id = parent_issue.id

        for child in jira_mapping["children"]:
            child_issue = self._sdk_create_issue(child)
            issue_keys.append(child_issue.key)

        if issue_keys:
            jira_mapping["issue"]["issuelinks"] = issue_keys

        issue = self._sdk_create_issue(jira_mapping["issue"], linked_issues=issue_keys)
        issue_keys.append(issue.key)

        if epic_id:
            self.sdk.add_issues_to_epic(epic_id, issue_keys)

        print("stop")

    def build_jira_mapping(self, artifact):
        translator = RallyArtifactTranslator(self._config)
        mapping = {
            "parent": None,
            "issue": translator.create_issue(artifact),
            "children": [],
        }

        if artifact["parent"]:
            mapping["parent"] = translator.create_issue(artifact["parent"])

        for child in artifact.get("children", []):
            mapping["children"].append(translator.create_issue(child))

        for child in artifact.get("stories", []):
            mapping["children"].append(translator.create_issue(child))

        return mapping

    def _sdk_create_issue(self, field_list):
        new_issue = self.sdk.create_issue(fields=field_list)
        if self.verbose:
            print(f"jira.create_issue() => {new_issue}")
        return new_issue
