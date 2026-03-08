<!-- This file is copy-pasted into Docker Hub as the repository overview.
     It is NOT developer documentation. Edit it only when tools, config, Docker Compose examples, or endpoints change. -->

# mcp-media-library-manager

A [FastMCP](https://github.com/jlowin/fastmcp) server for managing the file operations of a media library, ensuring files follow common standards for Media Server Software such as Emby and Plex. Destination files are taken out of the hands of the LLM to ensure they follow standards and safe operations are performed that don't expose a library as easily to prompt injection.

[MCP (Model Context Protocol)](https://modelcontextprotocol.io/) is an open standard that gives AI assistants real capabilities. Instead of only generating text, AI can use MCP servers to access tools, services, and data through a shared interface—making it possible for any MCP-compatible app to interact with real systems.

GitHub: [sesopenko/mcp-media-library-manager](https://github.com/sesopenko/mcp-media-library-manager)

---

## Use Case: Organizing Ripped TV Shows

When archiving shows from Blu-rays using tools like [MakeMKV](https://www.makemkv.com/), the output filenames won't follow the structure needed for media server software. This server lets an LLM handle the fuzzy translation of filenames to show names, season numbers, and episode numbers—while the server itself handles the safe placement of files.

Instead of trusting an LLM with file operations (risking non-standard organization or destructive mistakes), the `ingest_tv_episode` tool receives structured inputs and ensures files are moved to the proper location following the standard:

```
/<path_to_your_library>/<show name> (<year first aired>)/Season XX/SXXEXX.mkv
```

The server rejects unsafe operations and reports back with an error if a file already exists. Your library structure and existing files remain safe.

---

## Available Tools

### health_check

Returns `{"status": "ok"}` to confirm the server is running.

### ingest_tv_episode

Safely ingests a ripped TV episode into the media library at a standardized location determined by server-side rules.

**Arguments:**

- `source_file_path` (string): Path to the source episode file. Must be within a configured source root.
- `show_name` (string): The TV show name. Cannot contain path separators (`/` or `\`) or control characters.
- `first_air_year` (integer): The year the show first aired.
- `season_number` (integer): The season number (1-based, e.g., 1, 2, 10). Will be zero-padded to two digits in the destination filename (e.g., S01, S02, S10).
- `episode_number` (integer): The episode number (1-based, e.g., 1, 5, 12). Will be zero-padded to two digits in the destination filename (e.g., E01, E05, E12).

**Destination Path Format:**

The tool automatically computes the destination path using the standardized format:

```
/<show_root>/<show_name> (<first_air_year>)/Season <XX>/<SXXEXX>.mkv
```

Example: `/media/tv_shows/Breaking Bad (2008)/Season 01/S01E01.mkv`

**What It Does:**

- Validates the source file exists and is within a configured source root
- Validates the show name contains no path separators or control characters
- Computes the standardized destination path using the provided metadata
- Verifies the destination path is within a configured show root
- Creates missing destination directories automatically
- Moves the file to the destination
- Returns success with the computed destination path, or failure with an error message

**Error Conditions:**

The tool rejects the operation with an explicit error if:

- The source file path is outside all configured source roots (source root enforcement)
- The source file does not exist or is not a regular file
- The show name contains path separators (`/` or `\`) or control characters
- The computed destination path is outside all configured show roots (show root enforcement)
- The destination file already exists (no file overwrites)
- Season or episode numbers are invalid
- Directory creation fails
- File move operation fails

**Safety Guarantees:**

- No caller-controlled destination paths — the server computes destinations from validated structured inputs
- No file overwrites — the operation fails explicitly if the destination already exists
- Strict input validation — unsafe or ambiguous inputs are rejected immediately
- Source and show root enforcement — files can only be read from and written to configured locations

---

## Quick Start

### Docker Compose

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

---

## Configuration

Create a `config.toml` in the working directory (or pass `--config <path>`):

```toml
[server]
# Address the MCP server listens on. Use 0.0.0.0 to accept connections on all interfaces.
host = "0.0.0.0"
# Port the MCP server listens on.
port = 8080
# Comma-separated list of source locations. Ingest operations can only read/move files from these paths.
source_roots = "/media/rip_location"
# Comma-separated list of destination root folders for TV shows. Ingest operations can only write to these paths.
show_roots = "/media/tv_shows,/media/tv_shows_2"

[logging]
# Log verbosity level. One of: debug, info, warning, error.
level = "info"
```

### [server] Section

| Key | Description |
|---|---|
| `host` | Address the MCP server listens on. `0.0.0.0` accepts connections on all interfaces. Default: `"0.0.0.0"` |
| `port` | Port the MCP server listens on. Default: `8080` |
| `source_roots` | **Required.** Comma-separated list of source locations. Ingest operations can only read/move files from these paths. This restricts the server to specific source directories for security. |
| `show_roots` | **Required.** Comma-separated list of destination root folders for TV shows. Ingest operations can only write files to these paths. This ensures ingested episodes stay within designated library locations. |

### [logging] Section

| Key | Description |
|---|---|
| `level` | Log verbosity level. One of: `debug`, `info`, `warning`, `error`. Default: `"info"` |

---

## Security

This server has **no authentication** on its MCP endpoint. It is designed for **LAN use only**.

**Do not expose this server directly to the internet.**

If you need to access it remotely, place it behind a reverse proxy that handles TLS termination and access control.

---

## Connecting an AI Application

This server uses the **Streamable HTTP** MCP transport. Clients communicate via HTTP POST with streaming responses.

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

## License

Copyright (c) Sean Esopenko 2026

Licensed under the [GNU General Public License v3.0](https://github.com/sesopenko/mcp-media-library-manager/blob/main/LICENSE.txt).

---

## Acknowledgement: Riding on the Backs of Giants

This project was built with the assistance of [Claude Code](https://claude.ai/code), an AI coding assistant developed by Anthropic.

AI assistants like Claude are trained on enormous amounts of data — much of it written by the open-source community: the libraries, tools, documentation, and decades of shared knowledge that developers have contributed freely. Without that foundation, tools like this would not be possible.

In recognition of that debt, this project is released under the [GNU General Public License v3.0](https://github.com/sesopenko/mcp-media-library-manager/blob/main/LICENSE.txt). The GPL ensures that this code — and any derivative work — remains open source. It is a small act of reciprocity: giving back to the commons that made it possible.

To every developer who ever pushed a commit to a public repo, wrote a Stack Overflow answer, or published a package under an open license — thank you.
