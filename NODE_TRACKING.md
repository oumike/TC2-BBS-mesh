# Node Tracking System

## Overview

The TC²-BBS system now includes comprehensive node tracking functionality that automatically stores and monitors all node information in a SQLite database. This feature captures metrics from all nodes on the mesh network, including battery levels, hardware information, location data, and network statistics.

## Database Files

The system uses separate database files for different purposes:

- **`nodes.db`** - Node tracking data (this feature)
- **`bulletins.db`** - Mail, bulletins, and channel directory
- **`mqtt_counts.db`** - MQTT topic statistics (optional monitoring)

## Features

### Automatic Data Collection

The system automatically collects and stores the following information for each node:

#### Identity Information
- **Node ID**: Unique identifier (e.g., `!0137af2d`)
- **Numeric ID**: Numeric representation of the node ID
- **Short Name**: 4-character node identifier
- **Long Name**: Full node name
- **Hardware Model**: Device hardware type
- **Role**: Node role in the mesh network

#### Power Metrics
- **Battery Level**: Percentage (0-100%)
- **Voltage**: Current battery voltage

#### Network Metrics
- **Channel Utilization**: Percentage of channel usage
- **Air Utilization TX**: Transmission air time usage
- **SNR**: Signal-to-Noise Ratio in dB

#### Environmental Data
- **Temperature**: Device temperature in Celsius

#### Location Information
- **Latitude**: GPS latitude coordinate
- **Longitude**: GPS longitude coordinate
- **Altitude**: Elevation in meters

#### Timestamps
- **First Seen**: When the node was first observed
- **Last Heard**: Last time a packet was received from the node
- **Last Updated**: Last time the database record was updated

## Database Schema

The node information is stored in the `nodes` table with the following structure:

```sql
CREATE TABLE nodes (
    node_id TEXT PRIMARY KEY,
    num INTEGER,
    short_name TEXT,
    long_name TEXT,
    hw_model TEXT,
    role TEXT,
    battery_level INTEGER,
    voltage REAL,
    channel_utilization REAL,
    air_util_tx REAL,
    temperature REAL,
    latitude REAL,
    longitude REAL,
    altitude INTEGER,
    snr REAL,
    last_heard INTEGER,
    first_seen INTEGER,
    last_updated INTEGER
);
```

## How It Works

### Real-Time Updates

The system updates node information in two ways:

1. **Packet Reception**: Every time a packet is received from a node, its information is automatically updated in the database.

2. **Periodic Sync**: A background thread runs every 5 minutes (300 seconds) to sync all known nodes from the interface to the database. This ensures that even nodes that haven't sent messages recently are tracked.

### Data Flow

```
┌─────────────────┐
│  Mesh Network   │
└────────┬────────┘
         │
         ├─→ Text Messages
         ├─→ Telemetry Data
         └─→ Node Info Updates
         │
         ▼
┌─────────────────┐
│  on_receive()   │  ← Receives all packets
└────────┬────────┘
         │
         ├─→ Updates node info in DB
         ├─→ Processes messages
         └─→ Handles BBS commands
         │
         ▼
┌─────────────────┐
│ SQLite Database │
│   (nodes.db)    │
└─────────────────┘
         │
         ├─→ node_stats.py
         └─→ Query tools
```

## Using the Node Stats Viewer

A command-line utility (`node_stats.py`) is provided to query and analyze the stored node data.

### List All Nodes

Display a summary table of all tracked nodes:

```bash
python node_stats.py list
```

Output example:
```
================================================================================
NODE SUMMARY (15 nodes)
================================================================================
Node ID         Short      Long Name                 HW Model        Battery  Last Heard
--------------------------------------------------------------------------------
!0137af2d       riex       Rhino Explorer MT         HELTEC_V3       85%      2026-02-28 14:30:25
!bb9c45e2       wolf       Wolf Tracker              RAK4631         92%      2026-02-28 14:28:13
!5dd0dd45       bear       Bear Station              T_BEAM          78%      2026-02-28 14:25:42
...
================================================================================
```

### View Statistics

Display database statistics and aggregated metrics:

```bash
python node_stats.py stats
```

Output example:
```
================================================================================
DATABASE STATISTICS
================================================================================

Total Nodes:         15
With Battery Data:   12 (80.0%)
With Location Data:  8 (53.3%)
With Temperature:    5 (33.3%)
Avg Battery Level:   84.2%
Low Battery (<20%):  1

-- Hardware Models --
HELTEC_V3            5
RAK4631              4
T_BEAM               3
TECHO                2
STATION_G2           1

-- Node Roles --
CLIENT               10
ROUTER               3
ROUTER_CLIENT        2
```

### View Detailed Node Information

Display all available information for a specific node:

```bash
python node_stats.py detail !0137af2d
```

Output example:
```
================================================================================
NODE DETAILS: !0137af2d
================================================================================

-- Identity --
Node ID:       !0137af2d
Numeric ID:    20529965
Short Name:    riex
Long Name:     Rhino Explorer MT
Hardware:      HELTEC_V3
Role:          CLIENT

-- Power Metrics --
Battery:       85%
Voltage:       4.12V

-- Network Metrics --
Channel Util:  12.5%
Air Util TX:   3.2%
SNR:           9.5 dB

-- Environmental --
Temperature:   22.3°C

-- Location --
Latitude:      42.331427
Longitude:     -83.045754
Altitude:      183m

-- Timestamps --
First Seen:    2026-02-15 08:23:14
Last Heard:    2026-02-28 14:30:25
Last Updated:  2026-02-28 14:30:26

================================================================================
```

## Configuration

### Sync Interval

By default, the background sync runs every 5 minutes (300 seconds). You can modify this in `server.py`:

```python
sync_thread = threading.Thread(
    target=node_sync_worker, 
    args=(interface, 600),  # Change to 600 for 10-minute intervals
    daemon=True
)
```

### Initial Sync Delay

The system waits 30 seconds after startup before performing the first sync. This allows the interface to populate with node data. Adjust if needed in `server.py`:

```python
def node_sync_worker(interface, sync_interval=300):
    time.sleep(30)  # Change this delay if needed
    sync_all_nodes_to_db(interface)
    ...
```

## Database Functions

### Available Functions

The following functions are available in `db_operations.py`:

#### `upsert_node_info(node_id, node_data)`
Insert or update node information in the database.

```python
from db_operations import upsert_node_info

node_data = interface.nodes['!0137af2d']
upsert_node_info('!0137af2d', node_data)
```

#### `get_node_from_db(node_id)`
Retrieve a specific node's information from the database.

```python
from db_operations import get_node_from_db

node = get_node_from_db('!0137af2d')
if node:
    print(f"Node: {node['short_name']} - Battery: {node['battery_level']}%")
```

#### `get_all_nodes_from_db()`
Retrieve all nodes from the database, ordered by last heard (most recent first).

```python
from db_operations import get_all_nodes_from_db

nodes = get_all_nodes_from_db()
for node in nodes:
    print(f"{node['short_name']}: {node['battery_level']}%")
```

#### `sync_all_nodes_to_db(interface)`
Manually sync all nodes from the interface to the database.

```python
from db_operations import sync_all_nodes_to_db

count = sync_all_nodes_to_db(interface)
print(f"Synced {count} nodes to database")
```

## Use Cases

### Battery Monitoring

Track battery levels across all nodes:

```bash
python node_stats.py stats
```

Check for nodes with low battery:

```python
from db_operations import get_all_nodes_from_db

nodes = get_all_nodes_from_db()
low_battery = [n for n in nodes if n['battery_level'] and n['battery_level'] < 20]

for node in low_battery:
    print(f"⚠️ {node['short_name']} ({node['long_name']}): {node['battery_level']}%")
```

### Network Activity Analysis

Identify active versus inactive nodes:

```python
import time
from db_operations import get_all_nodes_from_db

nodes = get_all_nodes_from_db()
current_time = int(time.time())
one_hour_ago = current_time - 3600

active = [n for n in nodes if n['last_heard'] and n['last_heard'] > one_hour_ago]
inactive = [n for n in nodes if not n['last_heard'] or n['last_heard'] <= one_hour_ago]

print(f"Active (last hour): {len(active)}")
print(f"Inactive: {len(inactive)}")
```

### Hardware Inventory

Track what hardware is deployed:

```bash
python node_stats.py stats
```

### Location Mapping

Export node locations for mapping:

```python
from db_operations import get_all_nodes_from_db
import json

nodes = get_all_nodes_from_db()
locations = []

for node in nodes:
    if node['latitude'] and node['longitude']:
        locations.append({
            'name': node['long_name'],
            'lat': node['latitude'],
            'lon': node['longitude'],
            'alt': node['altitude']
        })

with open('node_locations.json', 'w') as f:
    json.dump(locations, f, indent=2)

print(f"Exported {len(locations)} node locations")
```

## Troubleshooting

### Database Location

The node data is stored in `nodes.db` in the same directory as the BBS server. Make sure you have write permissions to this directory.

Note: This is separate from `bulletins.db` (which stores mail, bulletins, and channels) to keep node tracking data independent.

### Logging

Node sync operations are logged. Check the logs for sync status:

```
2026-02-28 14:30:00 - INFO - Node sync worker started. Will sync every 300 seconds.
2026-02-28 14:30:30 - INFO - Synced 15 nodes to database
```

### Missing Data

Some metrics may not be available for all nodes:
- Battery data requires the node to be reporting power metrics
- Location data requires GPS to be enabled and acquiring satellites
- Temperature sensors are not available on all hardware

These fields will be `NULL` (or `None` in Python) if not available.

## Future Enhancements

Potential future additions to the node tracking system:

- Historical data tracking (store multiple readings over time)
- Alerts for low battery or offline nodes
- Web dashboard for visualization
- Export to CSV or other formats
- Integration with mapping services
- Node uptime statistics
- Network topology visualization

## Performance Considerations

- The periodic sync runs in a background thread and doesn't block BBS operations
- Database writes are optimized using UPSERT operations
- Only changed data is updated in the database
- The sync interval can be adjusted based on network size and activity

## Database Maintenance

To reset the node database:

```bash
# Backup first
cp nodes.db nodes.db.backup

# Delete node data
sqlite3 nodes.db "DELETE FROM nodes;"
```

To check database size:

```bash
ls -lh nodes.db
```

The database will automatically compact over time, but you can manually optimize it:

```bash
sqlite3 nodes.db "VACUUM;"
```
