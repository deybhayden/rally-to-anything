import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rally-to-anything",
    version="0.0.1",
    author="Ben Hayden",
    author_email="hayden767@gmail.com",
    description="A set of tools to migrate Rally installations to literally anything else.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/deybhayden/rally-to-anything",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Public Domain",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=["click", "pyral", "toml", "tqdm", "jira"],
    scripts=["bin/rally-to-anything", "bin/manage-jira-users"],
)
