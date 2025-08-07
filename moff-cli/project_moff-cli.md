---
project: moff-cli
---

# Overview: moff_project

This folder directory is the specification of the `moff-cli` application. It provides the documentation and requirements for its development, containing all the features and their specifications.

`moff-cli` (the library's name) or simply `moff` is a command-line tool which helps keeping the documentation clean and organized. The opinionated idea behind it is to make it easier to develop applications with the help of Large Language Models (LLMs). LLMs are good in markdown but keeping a certain structure for each document is somehow unreliable. `moff`'s purpose is to provide a command-line tool the LLM in IDE's like Cursor, VSCode or Zed can use to check the structure of the documentation (directory structure and of the file contents) and verify itself.

# Features

## settings

The settings feature allows the user to configure the application's behavior in a JSON file with the name `settings.json`. Possible settings are:

- file prefixes for allowed files
  - within root directory
  - within subdirectories
- for each prefix the file structure, like...
  - metadata
  - headers, their level and order
- documentation guildlines (text for the LLM)

If no `settings.json` exists in the root directory, the defaults - based on this documentation - are used.

> Feature file: `settings/feature_settings.md`

## collector

Detects all markdown files - starting from the root directory - and collects their content (metadata, structure, etc.). The `collector` feature is the leading process for the `check` and `tree` commands.
The `collector` feature returns a list of all markdown files and their content in a python dictionary, by making use of the `markdown-to-data` library.

> Feature file: `collector/feature_collector.md`

## tree

The tree feature is a command

> Feature file: `tree/feature_tree.md`

## check

The `check` feature is also the main command for the `moff-cli` application. It verifies the structure of the documentation's directory and the content of the files based on the configuration in the `settings.json` file.

Example usage: `moff check`
