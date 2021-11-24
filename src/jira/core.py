import json
import os

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

    def create_issue(self, artifact):
        issuetype = self.mappings["artifacts"][artifact["type"]]
        priority = self.mappings["priority"].get(artifact["priority"])
        status = self._get_status(artifact)
        resolution = self.mappings["resolution"].get(status)
        description, zendesk_tickets = self.text_translator.rally_html_to_jira(
            f"{artifact['description']}\n{artifact['notes']}"
        )

        issue = {
            "externalId": artifact["formattedId"],
            "priority": priority,
            "created": artifact["creationDate"],
            "issueType": issuetype,
            "status": status,
            "description": description,
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

        if issuetype == "Epic":
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
        else:
            issue["components"] = self._get_components(artifact)
            if zendesk_tickets:
                issue["customFieldValues"].append(
                    {
                        "fieldName": "Zendesk Tickets",
                        "fieldType": "com.atlassian.jira.plugin.system.customfieldtypes:textfield",
                        "value": ",".join(zendesk_tickets),
                    }
                )

        return issue

    def _get_attachments(self, artifact):
        attachments = []
        for attachment in tqdm.tqdm(artifact["attachments"], "Uploading Attachments"):
            attachment_filepath = self._get_attachment_filepath(attachment)
            if os.path.exists(attachment_filepath):
                url = self._get_s3_presignedurl(attachment_filepath)
                attachments.append(
                    {
                        "name": attachment["name"],
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
            ExpiresIn=600,  # Expires in 10 minutes
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
            if discussion["text"]:
                body, new_tickets = self.text_translator.rally_html_to_jira(
                    discussion["text"]
                )
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
                    labels.extend(value)
                elif isinstance(value, dict):
                    labels.append(value.get("name"))
                else:
                    labels.append(value)
        return labels

    def _get_status(self, artifact):
        if artifact["scheduleState"]:
            return self.mappings["status"][artifact["scheduleState"]]
        elif artifact["state"]:
            return self.mappings["status"][artifact["state"]]

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


class JiraMigrator(object):
    def __init__(self, config, verbose):
        self._config = config
        self.verbose = verbose
        boto3.setup_default_session(profile_name=config["aws"]["sso_profile"])
        self.s3_client = boto3.client(
            "s3",
            region_name=config["aws"]["region"],
            config=Config(signature_version="s3v4"),
            endpoint_url=config["aws"]["s3_endpoint_url"],
        )
        self.rally_artifacts = self.load_rally_artifacts()
        self.jira_users = {}

    def load_rally_artifacts(self):
        rally_artifacts = []
        artifact_root = RallyArtifact.output_root(self._config)
        for (dirpath, _, files) in os.walk(artifact_root):
            for filepath in files:
                with open(os.path.join(dirpath, filepath), "r") as f:
                    rally_artifacts.append(json.load(f))
        return rally_artifacts

    def build_import_json(self, skip_attachment_upload=False):
        translator = RallyArtifactTranslator(self, skip_attachment_upload)
        project = self._config["jira"]["project"].copy()
        project["issues"] = []
        import_json = {
            "users": [],
            "links": [],
            "projects": [project],
        }

        for artifact in tqdm.tqdm(self.rally_artifacts, "Artifacts"):
            issue = translator.create_issue(artifact)

            if artifact["parent"]:
                parent_issue = self._find_or_create_parent_issue(
                    project, translator, artifact
                )
                if parent_issue["issueType"] == "Epic":
                    issue["customFieldValues"].append(
                        {
                            "fieldName": "Epic Link",
                            "fieldType": "com.pyxis.greenhopper.jira:gh-epic-link",
                            "value": parent_issue["summary"],
                        }
                    )

                project["issues"].append(parent_issue)

            project["issues"].append(issue)

            for child_attrs in ("children", "stories", "tasks"):
                for child in artifact.get(child_attrs, []):
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
            {"email": email, **user} for (email, user) in self.jira_users.items()
        ]
        self._write_json_file(import_json)

    def _find_or_create_parent_issue(self, project, translator, artifact):
        matches = [
            i
            for i in project["issues"]
            if artifact["parent"]["formattedId"] == i["externalId"]
        ]
        if matches:
            return matches[0]
        else:
            return translator.create_issue(artifact["parent"])

    def _write_json_file(self, import_json):
        output_file = self._config["jira"]["json"]["filepath"]
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(import_json, f)
