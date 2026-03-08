# mcp-media-library-manager

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE.txt)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/downloads/)

A [FastMCP](https://github.com/jlowin/fastmcp) server for managing the file operations of a media library, ensuring files follow common standards for Media Server Software such as Emby and Plex. Destination files are taken out of the hands of the LLM to ensure they follow standards and safe operations are performed that don't expose a library as easily to prompt injection.

## Example use cases

### Copying ripped shows to destination folders

Example destionation:  `/<path_to_your_library>/<show name> (<year first aired>)/Season XX/SXXEXX.mkv`

When archiving shows from blurays using tools such as [MakeMKV](https://www.makemkv.com/) the output filenames won't follow the structure needed for media server software. LLMs can handle the fuzzy tranlsation of file names to show names, season numbers, and episode numbers. Trusting the LLM with the file copies however risks non-adherence to the standards and the LLM potentially performing destructive operations, such as deleting your whole library. The LLM is instead given a clear tool with a source file path, show name, how year of first air, season number, episode number.  The tool then ensures the file is moved to the proper location and will report back with an error if a file already exists in the location.  Existing files in the library aren't altered by an LLM and the standard is follow.

## About MCP

[MCP (Model Context Protocol)](https://modelcontextprotocol.io/) is an open standard that gives AI assistants real
capabilities. Instead of only generating text, AI can use MCP servers to access tools, services, and data through a
shared interface—making it possible for any MCP-compatible app to interact with real systems.

---

## Prerequisites

- **Docker** — for the Docker Compose deployment path
- **uv** — for the source deployment path (see [Installing uv](https://docs.astral.sh/uv/getting-started/installation/))
- **Node.js** — required for the git commit hooks; the hooks use [commitlint](https://commitlint.js.org/) to enforce Conventional Commits, which is the best-in-class Node.js tool for commit message validation

---

## Quick Start

### Option A — Docker Compose

1. Create a `docker-compose.yml`:

   ```yaml
   services:
     mcp-media-library-manager:
       image: sesopenko/mcp-media-library-manager:latest
       user: "${PUID:-1000}:${PGID:-1000}"
       ports:
         - "8080:8080"
       volumes:
         - ./config.toml:/config/config.toml:ro
         - /home/rip_location:/media/rip_location
         - /home/my_user/Videos/tv_shows:/media/tv_shows
         - /mnt/usb_hard_drive/tv_shows:/media/tv_shows_2
       restart: unless-stopped
   ```

   The `user:` directive runs the container process as the given UID and GID so that ingested files are owned by your user account rather than root. `PUID` and `PGID` default to `1000`. To find your own IDs, run:

   ```bash
   id
   ```

   This outputs something like `uid=1000(yourname) gid=1000(yourname) ...`. Use the `uid` value as `PUID` and the `gid` value as `PGID`. Create a `.env` file next to `docker-compose.yml`:

   ```
   PUID=1000
   PGID=1000
   ```

   To verify file ownership after ingestion, run:

   ```bash
   stat -c "%u %g %n" /path/to/ingested/file
   ```

   The first two numbers should match your `PUID` and `PGID`.

2. Copy the example config and edit it:

   ```bash
   cp config.toml.example config.toml
   ```

3. Start the server:

   ```bash
   docker compose up -d
   ```

### Option B — Run from Source

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you haven't already.

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Copy the example config and edit it:

   ```bash
   cp config.toml.example config.toml
   ```

4. Start the server:

   ```bash
   uv run python -m mcp_media_library_manager
   ```

---

## Security

This server has **no authentication** on its MCP endpoint. It is designed for LAN use only.

**Do not expose this server directly to the internet.**

If you need to access it remotely, place it behind a reverse proxy that handles TLS termination and access control. Configuring a reverse proxy is outside the scope of this project.

---

## Configuration

Create a `config.toml` in the working directory (or pass `--config <path>`):

```toml
[server]
host = "0.0.0.0"
port = 8080
# Comma-separated list of source locations — ingest operations can only read/move files from here
source_roots = "/media/rip_location"
# Comma-separated list of show root folders — ingest operations can only write to these locations
show_roots = "/media/tv_shows,/media/tv_shows_2"

[logging]
level = "info"
```

### [server]

| Key           | Default              | Description                                              |
|---------------|----------------------|----------------------------------------------------------|
| `host`        | `"0.0.0.0"`          | Address the MCP server listens on. `0.0.0.0` binds all interfaces. |
| `port`        | `8080`               | Port the MCP server listens on.                          |
| `source_roots` | Required | Comma-separated list of source locations. Ingest operations can only read/move files from these paths. |
| `show_roots` | Required | Comma-separated list of destination root folders for TV shows. Ingest operations can only write to these paths. |

### [logging]

| Key | Default | Description |
|---|---|---|
| `level` | `"info"` | Log verbosity. One of: `debug`, `info`, `warning`, `error`. |

---

## Connecting an AI Application

This server uses the **Streamable HTTP** MCP transport. Clients communicate via HTTP POST with streaming responses — opening the endpoint in a browser will return a `Not Acceptable` error, which is expected.

Point your MCP-compatible AI application at the server's MCP endpoint:

```
http://<host>:<port>/mcp
```

For example, if the server is running on `192.168.1.10` with the default port:

```
http://192.168.1.10:8080/mcp
```

Consult your AI application's documentation for how to register an MCP server. Ensure it supports the Streamable HTTP transport (most modern MCP clients do).

---

## Available Tools

| Tool | Description                                                                                                                                                              |
|---|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `health_check` | Returns `{"status": "ok"}` to confirm the server is running.                                                                                                             |
| `ingest_tv_episode` | Ingests a ripped TV episode into the media library using structured metadata, with server-computed standardized destination paths that follow naming conventions and cannot be controlled by the caller. |
| `list_queued_ingestions` | List all currently queued episode ingest jobs. |

### Tool Reference

#### `ingest_tv_episode`

Safely ingests a TV episode file into the media library at a standardized location determined by server-side rules.

**Arguments:**
- `source_file_path` (string): Path to the source episode file. Must be within a configured source root.
- `show_name` (string): The TV show name. Cannot contain path separators (`/` or `\`) or control characters.
- `first_air_year` (integer): The year the show first aired.
- `season_number` (integer): The season number (1-based). Will be zero-padded to two digits in the destination filename.
- `episode_number` (integer): The episode number (1-based). Will be zero-padded to two digits in the destination filename.

**Destination Path Format:**

The tool automatically computes the destination path using the standardized format:
```
/<show_root>/<show_name> (<first_air_year>)/Season <XX>/<SXXEXX>.mkv
```

Where:
- `<show_root>` is one of the configured show roots (the first matching root is selected)
- `<show_name>` is the provided show name
- `<first_air_year>` is the provided year
- `<XX>` is the zero-padded season number (e.g., `01`, `10`, `23`)
- `<SXXEXX>` is the standard episodic notation (e.g., `S01E05`, `S10E12`)

**Error Conditions:**

The tool rejects the operation with an explicit error if:
- The source file path is outside all configured source roots
- The source file does not exist or is not a regular file
- The show name contains path separators or control characters
- The computed destination path is outside all configured show roots
- The destination file already exists (no overwriting)
- Season or episode numbers are invalid
- A directory creation or file move operation fails

**Behavior:**

- Missing destination directories are created automatically
- The operation is safe by default: no file overwrites, no caller-controlled destination paths, strict input validation

---

## Development Architecture

The template follows a clean three-layer separation:

| File | Purpose |
|---|---|
| `src/mcp_media_library_manager/tools.py` | Pure Python functions — one function per tool, no framework coupling |
| `src/mcp_media_library_manager/server.py` | FastMCP wiring — registers tool functions with `@mcp.tool()` and runs the server |
| `src/mcp_media_library_manager/config.py` | TOML config loading — typed dataclasses for `[server]` and `[logging]` sections |
| `src/mcp_media_library_manager/logging.py` | Structured logger factory |

### Adding a tool

1. Add a function to `src/mcp_media_library_manager/tools.py` with a Google-style docstring and full type annotations.
2. Import the function in `src/mcp_media_library_manager/server.py` and register it with `@mcp.tool()`.
3. Add a unit test in `tests/unit/`.
4. Add a row to the **Available Tools** table in this README.

---

## Running Tests

```bash
uv run pytest tests/unit/
```

---

## Contributing / Maintaining

See [MAINTAINERS.md](MAINTAINERS.md) for setup, development commands, AI agent rails, and how to run tests.

---

## License

Copyright (c) Sean Esopenko 2026

This project is licensed under the [GNU General Public License v3.0](LICENSE.txt).

---

## Acknowledgement: Riding on the Backs of Giants

This project was built with the assistance of [Claude Code](https://claude.ai/code), an AI coding assistant developed by Anthropic.

AI assistants like Claude are trained on enormous amounts of data — much of it written by the open-source community: the libraries, tools, documentation, and decades of shared knowledge that developers have contributed freely. Without that foundation, tools like this would not be possible.

In recognition of that debt, this project is released under the [GNU General Public License v3.0](LICENSE.txt). The GPL ensures that this code — and any derivative work — remains open source. It is a small act of reciprocity: giving back to the commons that made it possible.

To every developer who ever pushed a commit to a public repo, wrote a Stack Overflow answer, or published a package under an open license — thank you.
