# opentrack-osc

Bridges [OpenTrack](https://github.com/opentrack/opentrack) head-tracking output to any OSC-capable application over the network.
This is only relevant for macOS where OpenTrack](https://github.com/opentrack/opentrack) currently does not support OSC ouput directly.

OpenTrack sends pose data as raw UDP packets. This script receives those packets and re-sends each frame as an OSC message to a configurable host and port.

## Requirements

- Python 3.9 or newer
- OpenTrack with the **UDP over network** output protocol enabled

## Installation

```bash
pip install -r requirements.txt
```

## OpenTrack setup

1. Open OpenTrack and go to **Output → Select output** → choose **UDP over network**.
2. Click the wrench icon next to it and set:
   - **Address** — IP of the machine running this script (or `127.0.0.1` if running locally)
   - **Port** — must match `listen_port` in `config.toml` (default: `4242`)
3. Start tracking. OpenTrack will now stream pose data to this script.

## Running

```bash
python opentrack_osc.py
```

By default the script looks for `config.toml` in the same directory. Pass `-c` to use a different path:

```bash
python opentrack_osc.py -c /path/to/my_config.toml
```

Press `Ctrl+C` to stop.

## Configuration

All settings live in `config.toml`.

### `[opentrack]` — incoming UDP

```toml
[opentrack]
listen_host = "0.0.0.0"   # interface to bind ("0.0.0.0" = all interfaces)
listen_port = 4242         # must match OpenTrack's output port
```

### `[osc]` — outgoing OSC

```toml
[osc]
target_host = "192.168.1.50"  # IP of the OSC target application
target_port = 8000
```

### `[mapping]` — OSC address strings

Two modes are available:

**`bundle`** — all six axes sent as float arguments in a single OSC message:

```toml
[mapping]
mode = "bundle"
bundle_address = "/opentrack/pose"
```

The receiving application gets one message at `/opentrack/pose` with arguments `(x, y, z, yaw, pitch, roll)`.

**`split`** — OSC messages are split into position (x, y, z) and rotation (yaw, pitch, roll) containing three float arguments each:

```toml
[mapping]
mode = "split"

[mappling.split]
position = "/opentrack/position"
rotation = "/opentrack/rotation"
```

The receiving application gets one message at `/opentrack/pose` with arguments `(x, y, z, yaw, pitch, roll)`.


**`individual`** — one OSC message per axis:

```toml
[mapping]
mode = "individual"

[mapping.individual]
x     = "/opentrack/x"
y     = "/opentrack/y"
z     = "/opentrack/z"
yaw   = "/opentrack/yaw"
pitch = "/opentrack/pitch"
roll  = "/opentrack/roll"
```

Each address string can be set to whatever the target application expects.

### `[logging]`

```toml
[logging]
level = "INFO"          # DEBUG, INFO, WARNING, ERROR
show_values = false     # set to true to print every packet's values (verbose)
```

## Data format

OpenTrack sends one packet per frame containing six 64-bit little-endian doubles:

| Index | Axis  | Unit    |
|-------|-------|---------|
| 0     | X     | mm      |
| 1     | Y     | mm      |
| 2     | Z     | mm      |
| 3     | Yaw   | degrees |
| 4     | Pitch | degrees |
| 5     | Roll  | degrees |

All values are forwarded as OSC `float` (32-bit).

## Example configs

### TouchDesigner on the same machine

```toml
[opentrack]
listen_host = "0.0.0.0"
listen_port = 4242

[osc]
target_host = "127.0.0.1"
target_port = 7000

[mapping]
mode = "bundle"
bundle_address = "/tracker/head"
```

### Max/MSP on another machine, individual axes

```toml
[opentrack]
listen_host = "0.0.0.0"
listen_port = 4242

[osc]
target_host = "192.168.1.42"
target_port = 9000

[mapping]
mode = "individual"

[mapping.individual]
x     = "/head/x"
y     = "/head/y"
z     = "/head/z"
yaw   = "/head/yaw"
pitch = "/head/pitch"
roll  = "/head/roll"
```
