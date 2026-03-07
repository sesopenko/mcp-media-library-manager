<!-- This file is copy-pasted into Docker Hub as the repository overview.
     It is NOT developer documentation. Do not read this for project context.
     Edit it only when tools, config, Docker Compose examples, or endpoints change. -->
# mcp-base

A bare-bones [FastMCP](https://github.com/jlowin/fastmcp) server template. Fork this repository to build your own MCP server without starting from scratch.

[MCP (Model Context Protocol)](https://modelcontextprotocol.io/) is an open standard that lets AI assistants call external tools and services. This template implements MCP over HTTP so any MCP-compatible AI application can reach your server.

GitHub: [sesopenko/mcp-media-library-manager](https://github.com/sesopenko/mcp-media-library-manager)

---

## Quick Start

### Docker Compose

1. Create a `docker-compose.yml`:

   ```yaml
   services:
     mcp-base:
       image: sesopenko/mcp-media-library-manager:latest
       ports:
         - "8080:8080"
       volumes:
         - ./config.toml:/config/config.toml:ro
       restart: unless-stopped
   ```

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

---

## Connecting an AI Application

Point your MCP-compatible AI application at the server's MCP endpoint:

```
http://<host>:<port>/mcp
```

For example, if the server is running on `192.168.1.10` with the default port:

```
http://192.168.1.10:8080/mcp
```

Consult your AI application's documentation for how to register an MCP server.

---

## Available Tools

| Tool | Description |
|---|---|
| `health_check` | Returns `{"status": "ok"}` to confirm the server is running. |
| `ingest_tv_episode` | Ingests a ripped TV episode into the media library using structured metadata, with server-computed standardized destination paths that follow naming conventions and cannot be controlled by the caller. |

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
