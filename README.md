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
  - Iterations
  - Epics, Features, User Stories, Defects
  - Discussions and attachments for above.
  - Dynamic fields converted to labels: Milestones, Releases
- Migrate serialized Rally data produced by this utility
  |Rally|Clubhouse|Jira|
  |--|--|--|
  |Iteration|Iteration|Label|
  |Milestones|Milestones|Label|
  |Epic|Epic|Epic|
  |Feature|Epic|Story|
  |User Story|Story|Sub-Task|
  |Defect|Story (type: :bug:)|Bug|

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
- You're using `pyenv`
- You're using `pipenv`

#### pipenv

From within your checkout:

```shell
pyenv install 3.9.6
pipenv install --python 3.9.6 . --editable .
```

#### Complete configuration

```shell
cp config.example.toml config.toml
# edit config.toml
# set api_key variables to live API key values and save
```

#### Running

```shell
pipenv shell
rally-to-anything dump-rally --config <config-location> --attachments
rally-to-anything generate-jira-import-json --config <config-location>
manage-jira empty-jira-project
```

### Tidbits

[Clubhouse limits file uploads to 50mb](https://help.clubhouse.io/hc/en-us/articles/205268729-Upload-Files-to-a-Story#:~:text=The%20web%20app%20has%20a,at%20most%20380%20pixels%20high.).
[Rally shares the same limit](https://knowledge.broadcom.com/external/article/57524/rally-link-a-file-that-exceeds-max-allo.html#:~:text=A%20user%20has%20a%20file,maximum%20allowed%2050%20MB%20limit.)

#### Resources

- [Rally Webservice](https://rally1.rallydev.com/slm/doc/webservice/)
- [Rally Python SDK](https://github.com/RallyTools/RallyRestToolkitForPython)
- [Clubhouse API](https://clubhouse.io/api/rest/v3)
