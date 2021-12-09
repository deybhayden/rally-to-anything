import json
import os
from datetime import datetime

import boto3
import tqdm
from botocore.client import Config

from .text import RallyTextTranslator
from src.rally.artifacts import RallyArtifact
from src.rally.attachments import RallyAttachment


class RallyArtifactTranslator(object):
    def __init__(self, migrator, skip_attachment_upload=False):
        self.migrator = migrator
        self.skip_attachment_upload = skip_attachment_upload
        self._config = self.migrator._config
        self.mappings = self._config["jira"]["mappings"]
        self.text_translator = RallyTextTranslator(self._config)
        self.today = datetime.now()

    def create_issue(self, artifact):
        issuetype = self.mappings["artifacts"][artifact["type"]]
        priority = self.mappings["priority"].get(artifact["priority"])
        status = self._get_status(issuetype, artifact)
        resolution = self.mappings["resolution"].get(status)
        description, zendesk_tickets = self._get_description_and_tickets(artifact)

        issue = {
            "externalId": artifact["formattedId"],
            "priority": priority,
            "created": artifact["creationDate"],
            "issueType": issuetype,
            "status": status,
            "description": description,
            "components": self._get_components(artifact),
            "reporter": self._get_user(artifact["createdBy"]),
            "comments": self._get_comments(artifact, zendesk_tickets),
            "attachments": self._get_attachments(artifact),
            "labels": self._get_labels(artifact),
            "summary": artifact["name"],
            "environment": artifact["environment"],
            "customFieldValues": [],
        }

        if resolution:
            issue["resolution"] = resolution

        if artifact["owner"]:
            issue["assignee"] = self._get_user(artifact["owner"])

        if artifact["blocked"]:
            issue["labels"].append("Blocked")

        if artifact["release"]:
            self._set_version(issue, artifact["release"])

        self._set_custom_fields(issue, artifact, zendesk_tickets)

        return issue

    def _get_description_and_tickets(self, artifact):
        description = f"{artifact['description']}\n{artifact['notes']}"

        if "defectDetails" in artifact:
            details = artifact["defectDetails"]
            if details["expectedResults"]:
                description += f"\n*Expected Results*\n{details['expectedResults']}"
            if details["actualResults"]:
                description += f"\n*Actual Results*\n{details['actualResults']}"
            if details["rootCause"]:
                description += f"\n*Root Cause*\n{details['rootCause']}"
            if details["siteURL"]:
                description += f"\n*Site URL*\n{details['siteURL']}"
            if details["stepsToReproduce"]:
                description += f"\n*Steps To Reproduce*\n{details['stepsToReproduce']}"

        return self.text_translator.rally_html_to_jira(description)

    def _get_attachments(self, artifact):
        attachments = []
        for attachment in tqdm.tqdm(artifact["attachments"], "Uploading Attachments"):
            attachment_filepath = self._get_attachment_filepath(attachment)
            if os.path.exists(attachment_filepath):
                url = self._get_s3_presignedurl(attachment_filepath)
                attachments.append(
                    {
                        "name": f"{attachment['name']} - {attachment['objectId']}",
                        "attacher": self._get_user(attachment["user"]),
                        "created": attachment["creationDate"],
                        "description": attachment["description"],
                        "uri": url,
                    }
                )
            else:
                print(f"WARN: Filepath missing for attachment {attachment['objectId']}")

        return attachments

    def _get_attachment_filepath(self, attachment):
        return os.path.join(
            RallyAttachment.output_root(self._config),
            "slm",
            "webservice",
            "v2.0",
            "attachment",
            str(attachment["objectId"]),
            attachment["name"],
        )

    def _get_s3_presignedurl(self, attachment_filepath):
        s3_key = self._upload_attachment_to_s3(attachment_filepath)
        url = self.migrator.s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self._config["aws"]["bucket_name"],
                "Key": s3_key,
            },
            HttpMethod="Get",
            ExpiresIn=self._config["aws"]["s3_presign_expires"],
        )
        return url

    def _upload_attachment_to_s3(self, attachment_filepath):
        dirs, filename = os.path.split(attachment_filepath)
        s3_key = os.path.join("attachments", os.path.basename(dirs), filename)
        if not self.skip_attachment_upload:
            self.migrator.s3_client.upload_file(
                attachment_filepath,
                Bucket=self._config["aws"]["bucket_name"],
                Key=s3_key,
            )
        return s3_key

    def _get_comments(self, artifact, zendesk_tickets):
        comments = []
        for discussion in artifact["discussion"]:
            body, new_tickets = self.text_translator.rally_html_to_jira(
                discussion["text"]
            )
            if body:
                zendesk_tickets.extend(new_tickets)
                comments.append(
                    {
                        "body": body,
                        "author": self._get_user(discussion["user"]),
                        "created": discussion["creationDate"],
                    }
                )
        return comments

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
        for field in self.mappings["labels"]["fields"]:
            value = artifact.get(field)
            if value:
                if isinstance(value, list):
                    names = [v.get("name") for v in value if isinstance(v, dict)]
                    if names:
                        labels.extend(names)
                    else:
                        labels.extend(value)
                elif isinstance(value, dict):
                    labels.append(value.get("name"))
                else:
                    labels.append(value)
        return labels

    def _get_sprint(self, iteration):
        start_date = datetime.strptime(
            iteration["endDate"], "%Y-%m-%dT%H:%M:%S.%f%z"
        ).replace(tzinfo=None)
        end_date = datetime.strptime(
            iteration["endDate"], "%Y-%m-%dT%H:%M:%S.%f%z"
        ).replace(tzinfo=None)

        iteration_state = None
        if start_date < self.today < end_date:
            iteration_state = "ACTIVE"
        elif end_date < self.today:
            iteration_state = "CLOSED"
        elif self.today < start_date:
            iteration_state = "FUTURE"

        return {
            "fieldName": "Sprint",
            "fieldType": "com.pyxis.greenhopper.jira:gh-sprint",
            "value": [
                {
                    "rapidViewId": self.mappings["sprints"]["rapidViewId"],
                    "state": iteration_state,
                    "startDate": iteration["startDate"],
                    "endDate": iteration["endDate"],
                    "completeDate": iteration["endDate"],
                    "name": iteration["name"],
                }
            ],
        }

    def _get_status(self, issuetype, artifact):
        if issuetype == "Epic" and "epic" in self.mappings["status"]:
            return self.mappings["status"]["epic"][artifact["state"]]
        elif issuetype == "Bug" and "bug" in self.mappings["status"]:
            return self.mappings["status"]["bug"][artifact["state"]]
        else:
            if artifact["scheduleState"]:
                return self.mappings["status"]["issue"][artifact["scheduleState"]]
            if artifact["state"]:
                return self.mappings["status"]["issue"][artifact["state"]]

    def _get_user(self, rally_user):
        if rally_user:
            if rally_user["firstName"]:
                name = f"{rally_user['firstName']} {rally_user['lastName']}"
            else:
                name = f"{rally_user.get('name')}"

            if rally_user["emailAddress"] not in self.migrator.jira_users:
                self.migrator.jira_users[rally_user["emailAddress"]] = {
                    "name": name,
                    "email": rally_user["emailAddress"],
                    "fullname": name,
                }

            return name

    def _set_custom_fields(self, issue, artifact, zendesk_tickets):
        issue["customFieldValues"] = []

        if artifact["planEstimate"]:
            issue["customFieldValues"].append(
                {
                    "fieldName": "Story Points",
                    "fieldType": "com.atlassian.jira.plugin.system.customfieldtypes:float",
                    "value": artifact["planEstimate"],
                }
            )

        if artifact["iteration"]:
            issue["customFieldValues"].append(self._get_sprint(artifact["iteration"]))

        if zendesk_tickets:
            issue["customFieldValues"].append(
                {
                    "value": ",".join(zendesk_tickets),
                    **self.mappings["customfields"]["zendesk_import"],
                }
            )

        if issue["issueType"] == "Epic":
            issue["customFieldValues"].extend(
                [
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
            )

        for key, value in self.mappings["customfields"].items():
            if artifact.get(key):
                issue["customFieldValues"].append({"value": artifact[key], **value})

    def _set_version(self, issue, release):
        release_date = datetime.strptime(
            release["releaseDate"], "%Y-%m-%dT%H:%M:%S.%f%z"
        ).replace(tzinfo=None)
        version = {
            "name": release["name"],
            "released": release_date < self.today,
            "startDate": release["releaseStartDate"],
            "releaseDate": release["releaseDate"],
        }
        issue["fixVersions"] = [version["name"]]
        existing_versions = [v["name"] for v in self.migrator.project["versions"]]
        if version["name"] not in existing_versions:
            self.migrator.project["versions"].append(version)


class JiraMigrator(object):
    def __init__(self, config, verbose, object_ids=None):
        self._config = config
        self.verbose = verbose
        boto3.setup_default_session(profile_name=config["aws"]["sso_profile"])
        self.s3_client = boto3.client(
            "s3",
            region_name=config["aws"]["region"],
            config=Config(signature_version="s3v4"),
            endpoint_url=config["aws"]["s3_endpoint_url"],
        )
        self.rally_artifacts = self.load_rally_artifacts(object_ids)
        self.jira_users = {}
        self.translator = None
        self.project = self._config["jira"]["project"].copy()
        self.ancestor = None

    def load_rally_artifacts(self, object_ids=None):
        rally_artifacts = []
        artifact_root = RallyArtifact.output_root(self._config)
        for (dirpath, _, files) in os.walk(artifact_root):
            for filepath in files:
                if object_ids:
                    object_id, _ = filepath.split(".")
                    if object_id not in object_ids:
                        continue
                with open(os.path.join(dirpath, filepath), "r") as f:
                    rally_artifacts.append(json.load(f))
        return rally_artifacts

    def build_import_json(self, skip_attachment_upload=False):
        self.translator = RallyArtifactTranslator(self, skip_attachment_upload)
        self.project["issues"] = []
        self.project["versions"] = []
        import_json = {
            "users": [],
            "links": [],
            "projects": [self.project],
        }

        for artifact in tqdm.tqdm(self.rally_artifacts, "Artifacts"):
            issue = self.translator.create_issue(artifact)

            if artifact["parent"]:
                if artifact["parent"]["type"] == "PortfolioItem/Epic":
                    issue["labels"].append(artifact["parent"]["name"])

            self.project["issues"].append(issue)
            self.ancestor = issue
            self._add_children(import_json, artifact, issue)

        import_json["users"] = [
            {"email": email, **user} for (email, user) in self.jira_users.items()
        ]
        self._write_json_file(import_json)

    def _find_or_create_parent_issue(self, artifact):
        matches = [
            i
            for i in self.project["issues"]
            if artifact["parent"]["formattedId"] == i["externalId"]
        ]
        if matches:
            return matches[0]
        else:
            parent_issue = self.translator.create_issue(artifact["parent"])
            self.project["issues"].append(parent_issue)
            return parent_issue

    def _add_children(self, import_json, artifact, issue):
        for child_attrs in ("children", "stories", "tasks"):
            for child in artifact.get(child_attrs, []):
                child_issue = self.translator.create_issue(child)
                if issue["issueType"] == "Epic":
                    child_issue["customFieldValues"].append(
                        {
                            "fieldName": "Epic Link",
                            "fieldType": "com.pyxis.greenhopper.jira:gh-epic-link",
                            "value": issue["summary"],
                        }
                    )
                else:
                    self._add_issue_links(import_json, issue, child_issue)
                self.project["issues"].append(child_issue)
                self._add_children(import_json, child, child_issue)

    def _add_issue_links(self, import_json, issue, child_issue):
        issue_link = self._get_issue_link(issue, child_issue)
        if issue_link:
            import_json["links"].append(issue_link)

        if self.ancestor["externalId"] != issue["externalId"]:
            issue_link = self._get_issue_link(self.ancestor, child_issue)
            if issue_link:
                import_json["links"].append(issue_link)

    def _get_issue_link(self, issue, child_issue):
        link_type = self._config["jira"]["mappings"]["issuelinking"].get(
            issue["issueType"], "sub-task-link"
        )

        if link_type == "sub-task-link":
            return {
                "name": link_type,
                "sourceId": child_issue["externalId"],
                "destinationId": issue["externalId"],
            }
        elif link_type == "Dependent":
            return {
                "name": link_type,
                "sourceId": issue["externalId"],
                "destinationId": child_issue["externalId"],
            }

    def _write_json_file(self, import_json):
        output_file = self._config["jira"]["json"]["filepath"]
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(import_json, f)
