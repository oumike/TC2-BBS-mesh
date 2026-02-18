# TC²-BBS Meshtastic Version

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/B0B1OZ22Z)

This is the TC²-BBS system integrated with Meshtastic devices. The system allows for message handling, bulletin boards, mail systems, and a channel directory.

### Docker

If you're a Docker user, TC²-BBS Meshtastic is available on Docker Hub!

[![Docker HUB](https://icon-icons.com/downloadimage.php?id=151885&root=2530/PNG/128/&file=docker_button_icon_151885.png)](https://hub.docker.com/r/thealhu/tc2-bbs-mesh)

## Setup

### Requirements

- Python 3.x
- Meshtastic
- pypubsub
- paho-mqtt (for MQTT topic monitoring)
- requests (for weather API integration)

### Update and Install Git
   
   ```sh
   sudo apt update
   sudo apt upgrade
   sudo apt install git
   ```

### Installation

1. Clone the repository:
   
   ```sh
   cd ~
   git clone https://github.com/TheCommsChannel/TC2-BBS-mesh.git
   cd TC2-BBS-mesh
   ```

2. Set up a Python virtual environment:  
   
   ```sh
   python -m venv venv
   ```

3. Activate the virtual environment:  
   
   - On Windows:  
   
   ```sh
   venv\Scripts\activate  
   ```
   
   - On macOS and Linux:
   
   ```sh
   source venv/bin/activate
   ```

4. Install the required packages:  
   
   ```sh
   pip install -r requirements.txt
   ```

5. Rename `example_config.ini`:

   ```sh
   mv example_config.ini config.ini
   ```

6. Set up the configuration in `config.ini`:  

   You'll need to open up the config.ini file in a text editor and make your changes following the instructions below
   
   **[interface]**  
   If using `type = serial` and you have multiple devices connected, you will need to uncomment the `port =` line and enter the port of your device.   
   
   Linux Example:  
   `port = /dev/ttyUSB0`   
   
   Windows Example:  
   `port = COM3`   
   
   If using type = tcp you will need to uncomment the hostname = 192.168.x.x line and put in the IP address of your Meshtastic device.  
   
   **[sync]**  
   Enter a list of other BBS nodes you would like to sync messages and bulletins with. Separate each by comma and no spaces as shown in the example below.   
   You can find the nodeID in the menu under `Radio Configuration > User` for each node, or use this script for getting nodedb data from a device:  
   
   [Meshtastic-Python-Examples/print-nodedb.py at main · pdxlocations/Meshtastic-Python-Examples (github.com)](https://github.com/pdxlocations/Meshtastic-Python-Examples/blob/main/print-nodedb.py)  
   
   Example Config:  
   
   ```ini
   [interface]  
   type = serial  
   # port = /dev/ttyUSB0  
   # hostname = 192.168.x.x  
   
   [sync]  
   bbs_nodes = !f53f4abc,!f3abc123  
   ```

### Running the Server

Run the server with:

```sh
python server.py
```

Be sure you've followed the Python virtual environment steps above and activated it before running.

## Command line arguments
```
$ python server.py --help

████████╗ ██████╗██████╗       ██████╗ ██████╗ ███████╗
╚══██╔══╝██╔════╝╚════██╗      ██╔══██╗██╔══██╗██╔════╝
   ██║   ██║      █████╔╝█████╗██████╔╝██████╔╝███████╗
   ██║   ██║     ██╔═══╝ ╚════╝██╔══██╗██╔══██╗╚════██║
   ██║   ╚██████╗███████╗      ██████╔╝██████╔╝███████║
   ╚═╝    ╚═════╝╚══════╝      ╚═════╝ ╚═════╝ ╚══════╝
Meshtastic Version

usage: server.py [-h] [--config CONFIG] [--interface-type {serial,tcp}] [--port PORT] [--host HOST] [--mqtt-topic MQTT_TOPIC]

Meshtastic BBS system

options:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        System configuration file
  --interface-type {serial,tcp}, -i {serial,tcp}
                        Node interface type
  --port PORT, -p PORT  Serial port
  --host HOST           TCP host address
  --mqtt-topic MQTT_TOPIC, -t MQTT_TOPIC
                        MQTT topic to subscribe
```



## Automatically run at boot

If you would like to have the script automatically run at boot, follow the steps below:

1. **Edit the service file**
   
   First, edit the mesh-bbs.service file using your preferred text editor. The 3 following lines in that file are what we need to edit:
   
   ```sh
   User=pi
   WorkingDirectory=/home/pi/TC2-BBS-mesh
   ExecStart=/home/pi/TC2-BBS-mesh/venv/bin/python3 /home/pi/TC2-BBS-mesh/server.py
   ```
   
   The file is currently setup for a user named 'pi' and assumes that the TC2-BBS-mesh directory is located in the home directory (which it should be if the earlier directions were followed)
   
   We just need to replace the 4 parts that have "pi" in those 3 lines with your username.

2. **Configuring systemd**
   
   From the TC2-BBS-mesh directory, run the following commands:
   
   ```sh
   sudo cp mesh-bbs.service /etc/systemd/system/
   ```
   
   ```sh
   sudo systemctl enable mesh-bbs.service
   ```
   
   ```sh
   sudo systemctl start mesh-bbs.service
   ```
   
   The service should be started now and should start anytime your device is powered on or rebooted. You can check the status of the service by running the following command:
   
   ```sh
   sudo systemctl status mesh-bbs.service
   ```
   
   If you need to stop the service, you can run the following:
   
   ```sh
   sudo systemctl stop mesh-bbs.service
   ```
   
   If you need to restart the service, you can do so with the following command:
   
   ```sh
   sudo systemctl restart mesh-bbs.service
   ```

2. **Viewing Logs**

   Viewing past logs:
   ```sh
   journalctl -u mesh-bbs.service
   ```

   Viewing live logs:
   ```sh
   journalctl -u mesh-bbs.service -f
   ```

## Radio Configuration

Note: There have been reports of issues with some device roles that may allow the BBS to communicate for a short time, but then the BBS will stop responding to requests. 

The following device roles have been working: 
- **Client**
- **Router_Client**

## Features

- **Mail System**: Send and receive mail messages.
- **Bulletin Boards**: Post and view bulletins on various boards.
- **Channel Directory**: Add and view channels in the directory.
- **Statistics**: View statistics about nodes, hardware, and roles.
- **Wall of Shame**: View devices with low battery levels.
- **Fortune Teller**: Get a random fortune. Pulls from the fortunes.txt file. Feel free to edit this file remove or add more if you like.
- **Weather Information**: Get current weather conditions for any location using OpenWeatherMap API.
- **MQTT Topic Monitor**: Track and display the most active MQTT topics on the mesh network.
- **Announcements**: Broadcast messages to specific channels on your Meshtastic device.
- **JS8Call Integration**: Integrate with JS8Call to receive messages into the BBS.

## Additional Features & Configuration

### Weather Integration

The BBS can fetch and display current weather conditions using the OpenWeatherMap API.

**Configuration** (`config.ini`):

```ini
[weather]
api_key = YOUR_API_KEY_HERE
default_location = 48336
units = imperial
```

- **api_key**: Get a free API key from [OpenWeatherMap](https://openweathermap.org/api)
- **default_location**: ZIP code or "city,state" or "city,country" format
- **units**: `imperial` (°F) or `metric` (°C)

**Usage**: 
- Send `WX` to get weather for the default location
- Send `WX,<location>` for a specific location (e.g., `WX,90210` or `WX,London,UK`)
- Access via Utilities menu → Weathe[R]

### MQTT Topic Monitoring

A standalone monitoring script (`monitor_mqtt_topics.py`) tracks MQTT message activity on the Meshtastic network and stores statistics in a SQLite database.

**Configuration** (`config.ini`):

```ini
[mqtt_monitor]
broker_host = mqtt.meshtastic.org
broker_port = 1883
base_topic = msh/US/MI
username = meshdev
password = large4cats
db_path = mqtt_counts.db
keepalive = 60
log_level = INFO
```

**Running the Monitor**:

```sh
python monitor_mqtt_topics.py
```

The script runs continuously and tracks message counts per subtopic. You can override any config setting with command-line arguments:

```sh
python monitor_mqtt_topics.py --base-topic msh/US/CA --log-level DEBUG
```

**Viewing Statistics**:
- Send `TT` as a quick command, or
- Access via Utilities menu → [T]op MQTT Topics
- Shows the top 15 most active topics from the monitoring database

**Running Monitor Automatically at Boot**:

To have the MQTT monitor script automatically start at boot:

1. **Edit the service file**
   
   Edit the `monitor-mqtt-topics.service` file and replace "pi" with your username in these lines:
   
   ```sh
   User=pi
   WorkingDirectory=/home/pi/TC2-BBS-mesh
   ExecStart=/home/pi/TC2-BBS-mesh/venv/bin/python3 /home/pi/TC2-BBS-mesh/monitor_mqtt_topics.py
   ```

2. **Install and enable the service**
   
   From the TC2-BBS-mesh directory, run:
   
   ```sh
   sudo cp monitor-mqtt-topics.service /etc/systemd/system/
   sudo systemctl enable monitor-mqtt-topics.service
   sudo systemctl start monitor-mqtt-topics.service
   ```
   
   Check the status:
   ```sh
   sudo systemctl status monitor-mqtt-topics.service
   ```
   
   View logs:
   ```sh
   journalctl -u monitor-mqtt-topics.service -f
   ```

### Announcements

Broadcast messages to specific channels configured on your Meshtastic device.

**Usage**:
1. Access via Utilities menu → [A]nnouncement
2. Select the channel number you want to broadcast to
3. Type your message
4. Message will be sent to all devices monitoring that channel

This is useful for making network-wide announcements or alerting specific groups.

### JS8Call Integration

Integrate with JS8Call to bring messages from JS8Call into the BBS system.

**Configuration** (`config.ini`):

```ini
[js8call]
host = 192.168.1.100
port = 2442
db_file = js8call.db
js8groups = @GRP1,@GRP2,@GRP3
store_messages = true
js8urgent = @URGNT
```

- **host**: IP address of the system running JS8Call
- **port**: JS8Call TCP API port (default: 2442)
- **db_file**: Database file for JS8Call messages (default: js8call.db)
- **js8groups**: Comma-separated list of JS8Call groups to monitor
- **store_messages**: Set to `true` to store all messages, `false` for group messages only
- **js8urgent**: Groups considered urgent (notifications sent to group chat)

Uncomment the section in `config.ini` and configure according to your JS8Call setup.

## Usage

You interact with the BBS by sending direct messages to the node that's connected to the system running the Python script. Sending any message to it will get a response with the main menu.  
Make selections by sending messages based on the letter or number in brackets - Send M for [M]ail Menu for example.

### Quick Commands

For faster access, you can use these shortcut commands without navigating through menus:

- **SM,,**`<recipient_id>,<subject>,<message>` - Send Mail directly
- **CM** - Check Mail
- **PB,,**`<board_name>,<subject>,<message>` - Post Bulletin directly
- **CB,,**`<board_name>` - Check Bulletins on a specific board
- **CHP,,**`<channel_name>,<channel_url>` - Post to Channel Directory
- **CHL** - List channels in Channel Directory
- **TT** - Show Top MQTT Topics
- **WX** - Get weather for default location
- **WX,**`<location>` - Get weather for specific location (e.g., `WX,90210` or `WX,Paris,FR`)

Send **Q** from the main menu to see the quick command reference on your device.

A video of it in use is available on our YouTube channel:

[![TC²-BBS-Mesh](https://img.youtube.com/vi/d6LhY4HoimU/0.jpg)](https://www.youtube.com/watch?v=d6LhY4HoimU)

## Thanks

**Meshtastic:**

Big thanks to [Meshtastic](https://github.com/meshtastic) and [pdxlocations](https://github.com/pdxlocations) for the great Python examples:

[python/examples at master · meshtastic/python (github.com)](https://github.com/meshtastic/python/tree/master/examples)

[pdxlocations/Meshtastic-Python-Examples (github.com)](https://github.com/pdxlocations/Meshtastic-Python-Examples)

**JS8Call:**

For the JS8Call side of things, big thanks to Jordan Sherer for JS8Call and the [example API Python script](https://bitbucket.org/widefido/js8call/src/js8call/tcp.py)

## License

GNU General Public License v3.0
