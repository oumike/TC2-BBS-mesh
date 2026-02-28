#!/usr/bin/env python3

"""
TC²-BBS Server for Meshtastic by TheCommsChannel (TC²)
Date: 07/14/2024
Version: 0.1.6

Description:
The system allows for mail message handling, bulletin boards, and a channel
directory. It uses a configuration file for setup details and an SQLite3
database for data storage. Mail messages and bulletins are synced with
other BBS servers listed in the config.ini file.
"""

import logging
import threading
import time

from config_init import initialize_config, get_interface, init_cli_parser, merge_config
from db_operations import initialize_database, initialize_nodes_database, sync_all_nodes_to_db
from js8call_integration import JS8CallClient
from message_processing import on_receive
from pubsub import pub
from utils import send_startup_announcement

# General logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# JS8Call logging
js8call_logger = logging.getLogger('js8call')
js8call_logger.setLevel(logging.DEBUG)
js8call_handler = logging.StreamHandler()
js8call_handler.setLevel(logging.DEBUG)
js8call_formatter = logging.Formatter('%(asctime)s - JS8Call - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
js8call_handler.setFormatter(js8call_formatter)
js8call_logger.addHandler(js8call_handler)

def display_banner():
    banner = """
████████╗ ██████╗██████╗       ██████╗ ██████╗ ███████╗
╚══██╔══╝██╔════╝╚════██╗      ██╔══██╗██╔══██╗██╔════╝
   ██║   ██║      █████╔╝█████╗██████╔╝██████╔╝███████╗
   ██║   ██║     ██╔═══╝ ╚════╝██╔══██╗██╔══██╗╚════██║
   ██║   ╚██████╗███████╗      ██████╔╝██████╔╝███████║
   ╚═╝    ╚═════╝╚══════╝      ╚═════╝ ╚═════╝ ╚══════╝
Meshtastic Version
"""
    print(banner)


def node_sync_worker(interface, sync_interval=300):
    """
    Background worker to periodically sync all nodes to the database.
    
    Args:
        interface: The Meshtastic interface object
        sync_interval: Interval in seconds between syncs (default: 300 = 5 minutes)
    """
    logging.info(f"Node sync worker started. Will sync every {sync_interval} seconds.")
    
    # Initial sync after a short delay to let interface populate
    time.sleep(30)
    try:
        sync_all_nodes_to_db(interface)
    except Exception as e:
        logging.error(f"Error in initial node sync: {e}")
    
    # Periodic sync
    while True:
        try:
            time.sleep(sync_interval)
            sync_all_nodes_to_db(interface)
        except Exception as e:
            logging.error(f"Error in periodic node sync: {e}")


def main():
    display_banner()
    args = init_cli_parser()
    config_file = None
    if args.config is not None:
        config_file = args.config
    system_config = initialize_config(config_file)

    merge_config(system_config, args)

    interface = get_interface(system_config)
    interface.bbs_nodes = system_config['bbs_nodes']
    interface.allowed_nodes = system_config['allowed_nodes']

    logging.info(f"TC²-BBS is running on {system_config['interface_type']} interface...")

    initialize_database()
    initialize_nodes_database()

    # Start background node sync worker
    sync_thread = threading.Thread(target=node_sync_worker, args=(interface,), daemon=True)
    sync_thread.start()
    logging.info("Node sync background worker started")

    def receive_packet(packet, interface):
        on_receive(packet, interface)

    pub.subscribe(receive_packet, system_config['mqtt_topic'])

    # Initialize and start JS8Call Client if configured
    js8call_client = JS8CallClient(interface)
    js8call_client.logger = js8call_logger

    if js8call_client.db_conn:
        js8call_client.connect()

    # Send startup announcement if configured
    if system_config['startup_enabled']:
        logging.info("Waiting 10 seconds before sending startup announcement...")
        time.sleep(10)  # Wait for the interface to be fully ready
        send_startup_announcement(
            interface,
            system_config['startup_channel_index'],
            system_config['startup_message']
        )

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Shutting down the server...")
        interface.close()
        if js8call_client.connected:
            js8call_client.close()

if __name__ == "__main__":
    main()
