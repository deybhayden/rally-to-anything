import click
import toml
import tqdm

import src.rally


@click.group()
def cli():
    pass


@cli.command()
@click.option("-v", "--verbose", default=False, is_flag=True)
@click.option("--config", type=click.File(), required=True, default="./config.toml")
def dump_rally(verbose, config):
    config = toml.load(config)
    click.echo("Dumping from Rally...")
    rally = src.rally.Rally(config, verbose)

    for artifact in tqdm.tqdm(rally.artifacts, desc="Work Items"):
        for attachment in tqdm.tqdm(
            artifact.attachments(),
            desc="Attachments",
            total=artifact.number_of_attachments,
        ):
            attachment.cache_to_disk()

        click.echo(artifact.json())


@cli.command()
@click.option("--config", type=click.File(), default="./config.toml")
def migrate(config):
    click.echo("Migrating...")


if __name__ == "__main__":
    cli()
