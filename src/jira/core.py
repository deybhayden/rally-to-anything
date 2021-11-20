import json
import os
import time

import tqdm
from jira import JIRA

from ..rally.artifacts import RallyArtifact
from ..rally.attachments import RallyAttachment


class RallyAttachmentTranslator(object):
    def __init__(self, artifact):
        self.artifact = artifact
        self.url_prefix = f"/slm/attachment/{artifact['objectId']}"

    @property
    def attachment_dirpath(self):
        return os.path.join(
            RallyAttachment.output_root,
            "slm",
            "webservice",
            "v2.0",
            "attachment",
            str(self.artifact["objectId"]),
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
    def __init__(self, migrator):
        self.migrator = migrator
        self.jira_config = self.migrator._config["jira"]

    def create_issue(self, artifact):
        issuetype = self.jira_config["mappings"]["artifacts"][artifact["type"]]
        priority = self.jira_config["mappings"]["priority"].get(artifact["priority"])
        status = self._get_status(artifact)

        issue = {
            "externalId": artifact["formattedId"],
            "priority": priority,
            "created": artifact["creationDate"],
            "issueType": issuetype,
            "status": status,
            "description": f"{artifact['description']}\n{artifact['notes']}",
            "reporter": self._get_user(artifact["createdBy"]),
            "comments": self._get_comments(artifact),
            "labels": self._get_labels(artifact),
            "summary": artifact["name"],
        }

        if artifact["owner"]:
            issue["assignee"] = self._get_user(artifact["owner"])

        if artifact["blocked"]:
            issue["labels"].append("Blocked")

        if issuetype == "Epic":
            issue["customFieldValues"] = [
                {
                    "fieldName": "Epic Name",
                    "fieldType": "com.pyxis.greenhopper.jira:gh-epic-label",
                    "value": issue["summary"],
                },
                {
                    "fieldName": "Epic Status",
                    "fieldType": "com.pyxis.greenhopper.jira:gh-epic-status",
                    "value": issue["status"],
                },
            ]
        else:
            issue.update(
                {
                    "components": self._get_components(artifact),
                }
            )

        return issue

    def _get_comments(self, artifact):
        return [
            {
                "body": d["text"],
                "author": self._get_user(d["user"]),
                "created": d["creationDate"],
            }
            for d in artifact["discussion"]
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
        for field in self.jira_config["mappings"]["labels"]["fields"]:
            value = artifact.get(field)
            if value:
                if isinstance(value, list):
                    labels.extend(value)
                elif isinstance(value, dict):
                    labels.append(value.get("name"))
                else:
                    labels.append(value)
        return labels

    def _get_status(self, artifact):
        if artifact["scheduleState"]:
            return self.jira_config["mappings"]["status"][artifact["scheduleState"]]
        elif artifact["state"]:
            return self.jira_config["mappings"]["status"][artifact["state"]]

    def _get_user(self, rally_user):
        if rally_user:
            if rally_user["firstName"]:
                name = f"{rally_user['firstName']} {rally_user['lastName']}"
                active = True
            else:
                name = f"{rally_user.get('name')}"
                active = False

            if rally_user["emailAddress"] not in self.migrator.jira_users:
                self.migrator.jira_users[rally_user["emailAddress"]] = {
                    "name": name,
                    "active": active,
                    "email": rally_user["emailAddress"],
                    "fullname": name,
                }

            return name


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
        self.jira_users = {}

    def load_rally_artifacts(self):
        rally_artifacts = []
        for (dirpath, _, files) in os.walk(RallyArtifact.output_root):
            for filepath in files:
                with open(os.path.join(dirpath, filepath), "r") as f:
                    rally_artifacts.append(json.load(f))
        return rally_artifacts

    def build_import_json(self, output_file):
        translator = RallyArtifactTranslator(self)
        project = self._config["jira"]["project"]
        project["issues"] = []
        import_json = {
            "users": [],
            "links": [],
            "projects": [project],
        }

        for artifact in tqdm.tqdm(self.rally_artifacts[:10], "Artifacts"):
            issue = translator.create_issue(artifact)

            if artifact["parent"]:
                parent_issue = translator.create_issue(artifact["parent"])
                if parent_issue["issueType"] == "Epic":
                    issue["customFieldValues"] = [
                        {
                            "fieldName": "Epic Link",
                            "fieldType": "com.pyxis.greenhopper.jira:gh-epic-link",
                            "value": parent_issue["summary"],
                        }
                    ]

                project["issues"].append(parent_issue)

            project["issues"].append(issue)

            for child_attrs in ("children", "stories"):
                for child in artifact[child_attrs]:
                    child_issue = translator.create_issue(child)
                    import_json["links"].append(
                        {
                            "name": "sub-task-link",
                            "sourceId": child_issue["externalId"],
                            "destinationId": issue["externalId"],
                        }
                    )
                    project["issues"].append(child_issue)

        import_json["users"] = [
            user.update({"email": email}) for (email, user) in self.jira_users
        ]
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(import_json, f)
