# rally-is-bad

## Objective

Create a utiliy for migrating core information for projects, iterations, epics,
features, and user stories including attachments and discussions from Rally (CA Agile)
to [Clubhouse](https://clubhouse.io) or [Jira](https://www.atlassian.com/software/jira).

## Working Notes

:warning: :warning: **WORK IN PROGRESS - USE AT YOUR OWN RISK** :warning: :warning:

The notes below will evolve into full sections over time, but if
you're reading this text you should ignore this project unless you're
just looking for examples of how to do something similar.

### Functionality

- CLI driven
- Configurable exclusion of:
  - Multiple Artifacts by Rally Query
- Configurable mapping and aggregation for Rally fields with sane defaults.
- Dump and serialize data from Rally on disk with support for incremental updates
  when data changes (all data new first run). Support for:
  - Releases & Iterations
  - Epics, Features, User Stories, Defects
  - Discussions and attachments for above.
  - Dynamic fields converted to labels: Milestones
- Migrate serialized Rally data produced by this utility
  |Rally|Clubhouse|Jira|
  |--|--|--|
  |Release|--|Version|
  |Iteration|Iteration|Sprint|
  |Milestones|Milestones|Label|
  |Epic|Epic|--|
  |Feature|Epic|Epic|
  |User Story|Story|Sub-Task|
  |Defect|Story (type: :bug:)|Bug|
- Uses the [Zendesk Support Jira App](https://www.zendesk.com/apps/support/24475/jira/) to create links to zendesk tickets extracted from Rally text fields.

  Fields to be converted based upon configuration. Reasonable defaults
  will be defined in the repository as examples/for ease of use.

  Attachments will be linked to corresponding artifacts directly were
  possible and will be shared as lins in comments otherwise.

  Attachments references in fields or discussions will be updated to
  refer to the Clubhouse/Jira file.

  Discussions will be converted as comments.

  Attachments will be linked to corresponding artifacts. Discussions
  mentioning artifacts will be converted as comments with

### Recommendation: Try it in Isolation

:dragon: Your mileage may vary with this tool.

Clubhouse allows you to create multiple workspaces under an organization. Jira can make many different projects for experimenting.

If you want to inspect the results of running this utility against your own
environment, I suggest starting with a sample in an isolated workspace in case
you don't like the results.

If it doesn't work for you out of the box, feel free to submit a pull request
or just modify it for your own purposes in a fork. :smile:

### Running this Utility

Assumptions:

- You're using a Mac
- You're using `pyenv` & `pipenv`
- You have AWS SSO & an S3 bucket for migrating attachments

#### pipenv

From within your checkout:

```bash
pyenv install 3.9.6
pipenv install --python 3.9.6 . --editable .
```

#### Complete configuration

```bash
cp config.example.toml config.toml
# edit config.toml
# set api_key variables to live API key values and save
```

Example AWS SSO profile:

```ini
[profile jira-migration]
region = us-east-2
output = json
sso_start_url = https://d-30010391193.awsapps.com/start
sso_region = us-east-1
sso_account_id = 123456789123
sso_role_name = PowerUser
```

#### Running

```bash
aws sso login --profile jira-migration
pipenv shell
rally-to-anything dump-rally --config <config-location> --attachments
rally-to-anything generate-jira-import-json --config <config-location>
# upload the JSON file on the External System Import screen in Global Jira Settings
# after the initial import, you can link your Zendesk tickets to Jira issues
manage-jira link-imported-zendesk-tickets
# all done?
manage-jira empty-project
```

### Tidbits

[Clubhouse limits file uploads to 50mb](https://help.clubhouse.io/hc/en-us/articles/205268729-Upload-Files-to-a-Story#:~:text=The%20web%20app%20has%20a,at%20most%20380%20pixels%20high.).
[Rally shares the same limit](https://knowledge.broadcom.com/external/article/57524/rally-link-a-file-that-exceeds-max-allo.html#:~:text=A%20user%20has%20a%20file,maximum%20allowed%2050%20MB%20limit.)

#### Resources

- [Rally Webservice](https://rally1.rallydev.com/slm/doc/webservice/)
- [Rally Python SDK](https://github.com/RallyTools/RallyRestToolkitForPython)
- [Clubhouse API](https://clubhouse.io/api/rest/v3)
