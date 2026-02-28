import logging
import sqlite3
import threading
import uuid
from datetime import datetime

from meshtastic import BROADCAST_NUM

from utils import (
    send_bulletin_to_bbs_nodes,
    send_delete_bulletin_to_bbs_nodes,
    send_delete_mail_to_bbs_nodes,
    send_mail_to_bbs_nodes, send_message, send_channel_to_bbs_nodes,
    send_urgent_bulletin_notification
)


thread_local = threading.local()

def get_db_connection():
    if not hasattr(thread_local, 'connection'):
        thread_local.connection = sqlite3.connect('bulletins.db')
    return thread_local.connection

def get_nodes_db_connection():
    if not hasattr(thread_local, 'nodes_connection'):
        thread_local.nodes_connection = sqlite3.connect('nodes.db')
    return thread_local.nodes_connection

def initialize_database():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bulletins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board TEXT NOT NULL,
                    sender_short_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    unique_id TEXT NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS mail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    sender_short_name TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    date TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    unique_id TEXT NOT NULL
                );''')
    c.execute('''CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL
                );''')
    conn.commit()
    print("Database schema initialized.")

def initialize_nodes_database():
    conn = get_nodes_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS nodes (
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
                );''')
    conn.commit()
    print("Nodes database schema initialized.")

def add_channel(name, url, bbs_nodes=None, interface=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO channels (name, url) VALUES (?, ?)", (name, url))
    conn.commit()

    if bbs_nodes and interface:
        send_channel_to_bbs_nodes(name, url, bbs_nodes, interface)


def get_channels():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, url FROM channels")
    return c.fetchall()



def add_bulletin(board, sender_short_name, subject, content, bbs_nodes, interface, unique_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    date = datetime.now().strftime('%Y-%m-%d %H:%M')
    if not unique_id:
        unique_id = str(uuid.uuid4())
    c.execute(
        "INSERT INTO bulletins (board, sender_short_name, date, subject, content, unique_id) VALUES (?, ?, ?, ?, ?, ?)",
        (board, sender_short_name, date, subject, content, unique_id))
    conn.commit()
    if bbs_nodes and interface:
        send_bulletin_to_bbs_nodes(board, sender_short_name, subject, content, unique_id, bbs_nodes, interface)

    # Send group chat notification for urgent bulletins
    if board.lower() == "urgent" and interface:
        send_urgent_bulletin_notification(sender_short_name, subject, interface)

    return unique_id


def get_bulletins(board):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, subject, sender_short_name, date, unique_id FROM bulletins WHERE board = ? COLLATE NOCASE", (board,))
    return c.fetchall()

def get_bulletin_content(bulletin_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT sender_short_name, date, subject, content, unique_id FROM bulletins WHERE id = ?", (bulletin_id,))
    return c.fetchone()


def delete_bulletin(bulletin_id, bbs_nodes, interface):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM bulletins WHERE id = ?", (bulletin_id,))
    conn.commit()
    send_delete_bulletin_to_bbs_nodes(bulletin_id, bbs_nodes, interface)

def add_mail(sender_id, sender_short_name, recipient_id, subject, content, bbs_nodes, interface, unique_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    date = datetime.now().strftime('%Y-%m-%d %H:%M')
    if not unique_id:
        unique_id = str(uuid.uuid4())
    c.execute("INSERT INTO mail (sender, sender_short_name, recipient, date, subject, content, unique_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (sender_id, sender_short_name, recipient_id, date, subject, content, unique_id))
    conn.commit()
    if bbs_nodes and interface:
        send_mail_to_bbs_nodes(sender_id, sender_short_name, recipient_id, subject, content, unique_id, bbs_nodes, interface)
    return unique_id

def get_mail(recipient_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, sender_short_name, subject, date, unique_id FROM mail WHERE recipient = ?", (recipient_id,))
    return c.fetchall()

def get_mail_content(mail_id, recipient_id):
    # TODO: ensure only recipient can read mail
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT sender_short_name, date, subject, content, unique_id FROM mail WHERE id = ? and recipient = ?", (mail_id, recipient_id,))
    return c.fetchone()

def delete_mail(unique_id, recipient_id, bbs_nodes, interface):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT recipient FROM mail WHERE unique_id = ?", (unique_id,))
        result = c.fetchone()
        if result is None:
            logging.error(f"No mail found with unique_id: {unique_id}")
            return  # Early exit if no matching mail found
        recipient_id = result[0]
        logging.info(f"Attempting to delete mail with unique_id: {unique_id} by {recipient_id}")
        c.execute("DELETE FROM mail WHERE unique_id = ? and recipient = ?", (unique_id, recipient_id,))
        conn.commit()
        send_delete_mail_to_bbs_nodes(unique_id, bbs_nodes, interface)
        logging.info(f"Mail with unique_id: {unique_id} deleted and sync message sent.")
    except Exception as e:
        logging.error(f"Error deleting mail with unique_id {unique_id}: {e}")
        raise


def get_sender_id_by_mail_id(mail_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT sender FROM mail WHERE id = ?", (mail_id,))
    result = c.fetchone()
    if result:
        return result[0]
    return None


def upsert_node_info(node_id, node_data):
    """
    Insert or update node information in the database.
    
    Args:
        node_id: The node's ID (e.g., '!0137af2d')
        node_data: Dictionary containing node information
    """
    import time
    
    conn = get_nodes_db_connection()
    c = conn.cursor()
    
    # Extract user data
    user_data = node_data.get('user', {})
    num = node_data.get('num')
    short_name = user_data.get('shortName')
    long_name = user_data.get('longName')
    hw_model = user_data.get('hwModel')
    role = user_data.get('role')
    
    # Extract device metrics
    metrics = node_data.get('deviceMetrics', {})
    battery_level = metrics.get('batteryLevel')
    voltage = metrics.get('voltage')
    channel_utilization = metrics.get('channelUtilization')
    air_util_tx = metrics.get('airUtilTx')
    temperature = metrics.get('temperature')
    
    # Extract position data
    position = node_data.get('position', {})
    latitude = position.get('latitude')
    longitude = position.get('longitude')
    altitude = position.get('altitude')
    
    # Extract other metadata
    snr = node_data.get('snr')
    last_heard = node_data.get('lastHeard')
    
    current_time = int(time.time())
    
    # Check if node exists
    c.execute("SELECT first_seen FROM nodes WHERE node_id = ?", (node_id,))
    result = c.fetchone()
    
    if result:
        # Update existing node
        c.execute('''UPDATE nodes SET 
                        num = ?,
                        short_name = ?,
                        long_name = ?,
                        hw_model = ?,
                        role = ?,
                        battery_level = ?,
                        voltage = ?,
                        channel_utilization = ?,
                        air_util_tx = ?,
                        temperature = ?,
                        latitude = ?,
                        longitude = ?,
                        altitude = ?,
                        snr = ?,
                        last_heard = ?,
                        last_updated = ?
                     WHERE node_id = ?''',
                  (num, short_name, long_name, hw_model, role,
                   battery_level, voltage, channel_utilization, air_util_tx, temperature,
                   latitude, longitude, altitude, snr, last_heard, current_time, node_id))
    else:
        # Insert new node
        first_seen = last_heard if last_heard else current_time
        c.execute('''INSERT INTO nodes (
                        node_id, num, short_name, long_name, hw_model, role,
                        battery_level, voltage, channel_utilization, air_util_tx, temperature,
                        latitude, longitude, altitude, snr, last_heard, first_seen, last_updated
                     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (node_id, num, short_name, long_name, hw_model, role,
                   battery_level, voltage, channel_utilization, air_util_tx, temperature,
                   latitude, longitude, altitude, snr, last_heard, first_seen, current_time))
    
    conn.commit()
    logging.debug(f"Node {node_id} ({short_name}) information updated in database")


def get_node_from_db(node_id):
    """
    Retrieve node information from the database.
    
    Args:
        node_id: The node's ID
    
    Returns:
        Dictionary with node information or None if not found
    """
    conn = get_nodes_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,))
    result = c.fetchone()
    
    if result:
        columns = [description[0] for description in c.description]
        return dict(zip(columns, result))
    return None


def get_node_by_shortname_from_db(short_name):
    """
    Retrieve node information from the database by short name (case-insensitive).
    
    Args:
        short_name: The node's short name
    
    Returns:
        List of dictionaries with node information
    """
    conn = get_nodes_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM nodes WHERE LOWER(short_name) = LOWER(?)", (short_name,))
    results = c.fetchall()
    
    if results:
        columns = [description[0] for description in c.description]
        return [dict(zip(columns, row)) for row in results]
    return []


def get_all_nodes_from_db():
    """
    Retrieve all nodes from the database.
    
    Returns:
        List of dictionaries with node information
    """
    conn = get_nodes_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM nodes ORDER BY last_heard DESC")
    results = c.fetchall()
    
    if results:
        columns = [description[0] for description in c.description]
        return [dict(zip(columns, row)) for row in results]
    return []


def sync_all_nodes_to_db(interface):
    """
    Sync all nodes from the interface to the database.
    
    Args:
        interface: The Meshtastic interface object
    """
    node_count = 0
    for node_id, node_data in interface.nodes.items():
        try:
            upsert_node_info(node_id, node_data)
            node_count += 1
        except Exception as e:
            logging.error(f"Error syncing node {node_id}: {e}")
    
    logging.info(f"Synced {node_count} nodes to database")
    return node_count
