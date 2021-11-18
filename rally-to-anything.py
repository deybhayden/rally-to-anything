import click
import toml
import tqdm

import src.rally
import src.jira


@click.group()
def cli():
    pass


@cli.command()
@click.option("-v", "--verbose", default=False, is_flag=True)
@click.option("-c", "--clear-cache", default=False, is_flag=True)
@click.option("-a", "--attachments", default=False, is_flag=True)
@click.option("--config", type=click.File(), required=True, default="./config.toml")
def dump_rally(verbose, clear_cache, attachments, config):
    config = toml.load(config)
    click.echo("Dumping from Rally...")
    rally = src.rally.Rally(config, verbose)
    if verbose and clear_cache:
        click.echo("Clearing local Rally artifact cache...")

    for artifact in tqdm.tqdm(rally.artifacts, desc="Artifacts"):
        if attachments:
            for attachment in tqdm.tqdm(
                artifact.attachments(),
                desc="Attachments",
                total=artifact.number_of_attachments,
                disable=artifact.number_of_attachments == 0,
            ):
                attachment.cache_to_disk(force=clear_cache)

        artifact.cache_to_disk(force=clear_cache)


@cli.command()
@click.option("-v", "--verbose", default=False, is_flag=True)
@click.option("--config", type=click.File(), required=True, default="./config.toml")
def migrate_jira(verbose, config):
    config = toml.load(config)
    click.echo("Migrating local Rally store to Jira Cloud...")
    jira = src.jira.Jira(config, verbose)
    jira.migrate_rally_artifacts()


if __name__ == "__main__":
    cli()
