---
project: moff-cli
---

# Overview

This folder directory is the specification of the `moff-cli` application. It provides the documentation and requirements for its development, containing all the features and their specifications.

`moff-cli` (the library's name) or simply `moff` is a command-line tool which helps keeping the documentation clean and organized. The opinionated idea behind it is to make it easier to develop applications with the help of Large Language Models (LLMs). LLMs are good in markdown but keeping a certain structure for each document is somehow unreliable. `moff`'s purpose is to provide a command-line tool the LLM in IDE's like Cursor, VSCode or Zed can use to check the structure of the documentation (directory structure and of the file contents) and verify itself.

# Features

## settings

The settings feature allows the user to configure the application's behavior in a JSON file with the name `settings.json`. Possible settings are:

- root detection method and override path
- ignore patterns for directories/files to skip
- file prefixes and their validation rules:
  - filename patterns (e.g., `project_*.md`)
  - location constraints (`root_only`, `subdirs_only`, `any`)
  - required and optional frontmatter fields with types
  - required and optional headers with level and text matching
  - header order enforcement (`strict`, `in-order`, `any`)

If no `settings.json` exists, the defaults are used. The CLI creates a default `settings.json` on first run if not already present.

> Feature file: `settings/feature_settings.md`

## collector

Discovers the documentation root (via `project_*.md` or override), traverses the directory tree while respecting ignore patterns, and collects all markdown files matching configured prefixes. The `collector` feature is the foundation for the `check` and `tree` commands.

The collector parses each file using the `markdown-to-data` library and returns a structured dictionary containing the root directory, metadata about root detection, and grouped files by prefix with their parsed content and location annotations.

> Feature file: `collector/feature_collector.md`

## tree

The tree feature (`moff tree` command) displays the documentation structure as a tree in the terminal, showing only directories and markdown files. It can optionally highlight inconsistencies detected by the `check` feature, helping visualize the documentation organization.

> Feature file: `tree/feature_tree.md`

## check

The `check` feature is the main command for the `moff-cli` application. It validates the collected documentation against the rules in `settings.json`, checking location constraints, frontmatter schemas, and required headers. Results are printed to the terminal and can be saved to `moff_results.txt` via the `save` sub-feature.

Example usage: `moff check` or `moff check --save`

### save

Sub-feature of `check` that persists validation results to `moff_results.txt` in the documentation root, including timestamp, summary statistics, and detailed violation list.

> Feature file: `check/save/feature_save.md`
