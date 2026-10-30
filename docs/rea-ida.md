# REA + IDA Pro on Windows

Paths below are for this machine: IDA Professional 9.0 at `C:\Program Files\IDA Professional 9.0`.

## One-time setup

```bash
# mcp 2.x renamed FastMCP, which breaks ida-pro-mcp 1.30; pin v1
uv tool install --force ida-pro-mcp --with "mcp<2"

# installs %APPDATA%\Hex-Rays\IDA Pro\plugins\mcp-plugin.py
ida-pro-mcp --install

# point idapro at the installation (writes %APPDATA%\Hex-Rays\IDA Pro\ida-config.json)
python "C:/Program Files/IDA Professional 9.0/idalib/python/py-activate-idalib.py" \
  -d "C:/Program Files/IDA Professional 9.0"
```

## Per-session

1. Open the target in IDA. Wait for auto-analysis to finish.
2. Start the plugin: `Edit -> Plugins -> MCP` (`Ctrl-Alt-M`). Verify: `netstat -ano | grep 13337`.
3. Point REA at the registration file:

```bash
export REA_IDA_MCP_CONFIG="C:/Users/ezan/Documents/decode-anything/scratch/rea-ida.json"
rea doctor | grep -A2 ida-registration
```

`scratch/rea-ida.json` spawns the stdio bridge that talks to the running GUI:

```json
{"type":"stdio","mode":"attached","command":"C:\\Users\\ezan\\.local\\bin\\ida-pro-mcp.exe","args":["--transport","stdio"],"env":{}}
```

## Commands

```bash
rea analyze <pe> --provider ida --format json
rea search <pe> "pattern" --mode regex --provider ida
rea search <pe> "name" --kind procedures --provider ida
rea xrefs <pe> 0xADDRESS --provider ida
rea decompile <pe> 0xADDRESS --provider ida
rea instructions <pe> 0xADDRESS --provider ida
```

## Behaviour notes

- Attached mode hashes the target open in IDA and refuses the request when it differs from the path passed to REA.
- The adapter identifies as `ida-pro-mcp 1.30.0`, compatibility profile `legacy-1.4`; decompile/search/xrefs/instructions are the usable surface.
- `idalib-mcp` (headless) serves MCP over SSE (`/sse`) only. REA speaks stdio or streamable HTTP, so the GUI plugin is the working path.
- REA decompile has a 300 s ceiling. Hex-Rays can blow it on small functions (observed on `sub_1800710C0`, 0xcf bytes); `rea instructions` on the same address returns immediately.
