# Vogelfrei

An OSR tabletop role-playing game of exile, survival, and fortune — inspired by LotFP and the Old School Renaissance.

**[vogelfrei.ru](https://vogelfrei.ru)** — play the game online.

## About

Vogelfrei is a classless, career-based RPG set in a dark fantasy world. Characters are defined by their history and the careers they've pursued, not abstract class archetypes. The rules emphasize danger, resource management, and meaningful player choices.

This repository contains the full source for the Vogelfrei rulebook, built as a static site with [Zensical](https://github.com/zensical/zensical).

## Building

### Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (package manager)

Install uv if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Setup

```bash
uv sync
```

### Commands

```bash
# Build the static site (output → site/)
uv run zensical build

# Serve locally with live reload (http://localhost:8000)
uv run zensical serve
```

## Structure

```
docs/          # Markdown source files (edit these)
zensical.toml  # Site configuration
site/          # Generated output (not committed)
```

## License

Copyright © 2026 Vogelfrei
