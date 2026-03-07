# Requirements

This is a living requirements document for `mcp-media-library-manager`. It captures requirements that are not yet fully met by the current implementation, or that are likely to be affected by upcoming development. Stable baseline capabilities that are already implemented are intentionally omitted to keep this document focused.

## Functional Requirements

**FR-05 — Source Root Configuration**

The application shall support configuration of one or more source root paths that define the only filesystem locations from which media ingest operations may read or move files.

**FR-06 — Show Root Configuration**

The application shall support configuration of one or more show root paths that define the only filesystem locations into which TV show media files may be placed.

**FR-07 — TV Episode Ingest Tool**

The server shall expose an MCP tool for ingesting a ripped TV episode into the media library using structured metadata rather than a model-generated destination path. At minimum, the tool shall accept a source file path, show name, first-air year, season number, and episode number.

**FR-08 — Standardized TV Show Destination Path**

The TV episode ingest tool shall derive the destination path from the supplied metadata using the destination structure documented in the README section "Copying ripped shows to destination folders": `/<path_to_your_library>/<show name> (<year first aired>)/Season XX/SXXEXX.mkv`. The destination path shall be computed by the server from validated inputs and server-side rules rather than accepted as an arbitrary destination path from the caller.

**FR-09 — Episode Filename Standardization**

The TV episode ingest tool shall generate the destination episode filename using the naming standard documented in the README section "Copying ripped shows to destination folders": `SXXEXX.mkv`, where season and episode numbers are zero-padded to two digits and are derived from the validated season number and episode number inputs.

**FR-10 — Destination Root Enforcement**

The application shall ensure that any destination path chosen for a TV episode ingest operation resolves within a configured show root and shall reject any operation that would write outside the configured show roots.

**FR-11 — Source Root Enforcement**

The application shall ensure that any source path provided to a TV episode ingest operation resolves within a configured source root and shall reject any operation that would read from or move a file outside the configured source roots.

**FR-12 — Existing File Collision Handling**

The TV episode ingest tool shall detect when the computed destination file already exists and shall fail the operation with an explicit error instead of overwriting or modifying the existing file.

**FR-14 — Tool Result Reporting**

The application shall return a clear success or failure result for each tool invocation, including enough information for a caller to understand what operation was performed or why it was rejected.

**FR-15 — Destination Directory Creation**

The TV episode ingest workflow shall create any missing destination directories required by the computed standardized destination path before placing the media file, provided the destination remains within a configured show root and all validation checks pass.

**FR-16 — Show Name Path Character Rejection**

The TV episode ingest workflow shall reject a provided show name if it contains characters that could alter path structure or be interpreted as path separators, including forward slash and backslash characters. The tool shall fail with an explicit error indicating that the show name cannot contain pathing characters.

## Non-Functional Requirements

**NFR-001 — Safe Cross-Platform Path Handling**

All filesystem paths and generated path components used by media ingest tools shall be normalized and validated before use so that path traversal, root escape, control characters, embedded newlines, and equivalent unsafe path manipulation techniques are prevented. Generated paths shall be represented using Linux-style forward-slash path notation, but every generated folder name and filename component shall be restricted to characters that are valid for Windows filesystems so that the resulting media library remains usable on both Linux and Windows, including when accessed through a network share.

**NFR-002 — Safe-by-Default File Operations**

The application shall prefer non-destructive behavior and shall reject unsafe or ambiguous operations rather than attempting to guess or recover in a way that could damage the media library.

**NFR-003 — Prompt-Injection Resistance by Design**

The system shall minimize trust in model-supplied filesystem destinations by deriving destination paths from validated structured inputs and server-side rules.

**NFR-004 — Fail-Fast Configuration Validation**

The application shall fail startup or configuration loading with an explicit error when required configuration sections or keys are missing, malformed, or invalid.

**NFR-008 — Typed Python Implementation**

Application code for tools, configuration, and server wiring shall use explicit Python type annotations.

**NFR-009 — Test Coverage for Implemented Behavior**

Each implemented tool and each critical configuration behavior shall have automated unit tests covering successful execution and expected failure modes.

**NFR-010 — Maintainable Separation of Concerns**

The codebase shall preserve a separation between pure tool logic, MCP server wiring, configuration loading, and logging concerns so that tools remain testable without framework coupling.

**NFR-011 — Documentation Synchronization**

Project documentation shall be kept in sync with the implemented server behavior, including configuration keys, transport details, and the list of available tools.

