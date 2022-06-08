# stactools-deltares

[![PyPI](https://img.shields.io/pypi/v/stactools-deltares)](https://pypi.org/project/stactools-deltares/)

- Name: deltares
- Package: `stactools.deltares`
- PyPI: https://pypi.org/project/stactools-deltares/
- Owner: @githubusername
- Dataset homepage: http://example.com
- STAC extensions used:
  - [proj](https://github.com/stac-extensions/projection/)
- Extra fields:
  - `deltares:custom`: A custom attribute

A short description of the package and its usage.

## STAC Examples

- [Collection](examples/collection.json)
- [Item](examples/item/item.json)

## Installation
```shell
pip install stactools-deltares
```

## Command-line Usage

Description of the command line functions

```shell
$ stac deltares create-item source destination
```

Use `stac deltares --help` to see all subcommands and options.

## Contributing

We use [pre-commit](https://pre-commit.com/) to check any changes.
To set up your development environment:

```shell
$ pip install -e .
$ pip install -r requirements-dev.txt
$ pre-commit install
```

To check all files:

```shell
$ pre-commit run --all-files
```

To run the tests:

```shell
$ pytest -vv
```
