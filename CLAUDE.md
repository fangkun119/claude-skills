# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This repo is a **Claude Code plugin marketplace** (`office-tool-marketplace`) containing two plugins published via the Claude Code plugin system. It also houses development workspaces, regression tests, and chat transcripts for plugin development.

## Plugin Architecture

### Marketplace Entry Point

`.claude-plugin/marketplace.json` registers all plugins with their source paths. Plugins are installed by users via `/plugin marketplace add` and `/plugin install`.

### pyramid Plugin

Document rewriting based on Barbara Minto's Pyramid Principle.

- **agents/**: Sub-agents invoked by Claude Code
  - `md-rewriter` — orchestrates the 5-step rewrite workflow (title refinement → content rewrite → gap filling → coverage check)
  - `md-content-gap-filler` — fills gaps between original and rewritten content
  - `transcription-corrector` — corrects voice-to-text transcription errors
- **commands/**: Slash commands invoked by users
  - `md-pyramid-rewrite` — main rewrite command (expression optimization + bold strategy)
  - `md-refine-titles` — title/heading optimization
  - `md-refine-expression` — expression refinement
  - `md-check-coverage` — verify original content coverage in rewritten output
  - `md-fix-transcription` — fix voice transcription artifacts

### note-tool Plugin

Document format conversion and directory archiving.

- **skills/doc-to-md/**: Converts PDF/DOCX/DOC/PPT/PPTX/HTML to Markdown using `markitdown==0.1.3` in a Python 3.12+ venv. Uses TUNA PyPI mirror for dependency installation.
- **skills/dir-archive/**: Archives directories to `.tar.gz` with incremental update support. Includes a Python script at `scripts/archive_dir.py`.

### Key Convention: Plugin Structure

Each plugin lives in its own top-level directory with:
```
<plugin-name>/
  .claude-plugin/
    plugin.json          # name, description, version, author
  agents/                # sub-agents (markdown frontmatter: name, description, model, color)
  commands/              # slash commands (markdown with usage instructions)
  skills/                # skills (SKILL.md with frontmatter: name, description, allowed-tools)
```

## Development Directories

- **repo-desktop/workspaces/**: Development workspaces for each plugin (pyramid, note-tool). Temporary files generated during the development and testing are all placed in this directory.
- **repo-desktop/regression/**: Regression test specs (markdown format) for plugin features
- **repo-desktop/chats/**: Chat transcripts and notes from plugin development sessions
- **.claude/commands/**: Project-level slash commands (e.g., `md-fix-voice-text`)


## Python Development

Use `uv` to create a Python 3.12 venv (`.venv`) for any Python code in this repo. Reuse existing `.venv` if present.

## Runtime Dependencies

- Python ≥3.12 + `uv` package manager (for note-tool skills)
- `markitdown[all]==0.1.3` (installed on-demand into `.venv`)
- TUNA PyPI mirror (`https://pypi.tuna.tsinghua.edu.cn/simple/`) used for Chinese network acceleration

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->

## Naming Convensions

Naming must use precise, clear, and concise phrasing to express its meaning. For example, you can use names like ‘titles_scripts_tests’ to precisely indicate the test subject, while names like ‘quest_check_tests’ that are vague and general should not be used.


