import src.rally

import click
import tqdm
import toml


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--output-root",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    default="./rally",
)
@click.option("--config", type=click.File(), required=True, default="./config.toml")
def dump_rally(output_root, config):
    config = toml.load(config)
    click.echo("Dumping from Rally...")
    rally = src.rally.Rally(config)

    for artifact in tqdm.tqdm(rally.artifacts, desc="Work Items"):
        for attachment in tqdm.tqdm(
            artifact.attachments(),
            desc="Attachments",
            total=artifact.number_of_attachments,
        ):
            attachment._cache_to_disk()


@cli.command()
@click.option("--config", type=click.File(), default="./config.toml")
def migrate(config):
    click.echo("Migrating...")


if __name__ == "__main__":
    cli()
