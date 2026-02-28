import configparser
import logging
import sqlite3
import time

# Read configuration
config = configparser.ConfigParser()
config.read('config.ini')

user_states = {}


def update_user_state(user_id, state):
    user_states[user_id] = state


def get_user_state(user_id):
    return user_states.get(user_id, None)


def send_message(message, destination, interface):
    max_payload_size = 200
    for i in range(0, len(message), max_payload_size):
        chunk = message[i:i + max_payload_size]
        try:
            d = interface.sendText(
                text=chunk,
                destinationId=destination,
                wantAck=True,
                wantResponse=False
            )
            destid = get_node_id_from_num(destination, interface)
            chunk = chunk.replace('\n', '\\n')
            logging.info(f"Sending message to user '{get_node_short_name(destid, interface)}' ({destid}) with sendID {d.id}: \"{chunk}\"")
        except Exception as e:
            logging.info(f"REPLY SEND ERROR {e}")

        # Sleep between message chunks to avoid overwhelming the mesh network
        message_delay = config.getfloat('misc', 'message_delay', fallback=5.0)
        time.sleep(message_delay)


def get_node_info(interface, short_name):
    nodes = [{'num': node_id, 'shortName': node['user']['shortName'], 'longName': node['user']['longName']}
             for node_id, node in interface.nodes.items()
             if node['user']['shortName'].lower() == short_name]
    return nodes


def get_node_id_from_num(node_num, interface):
    for node_id, node in interface.nodes.items():
        if node['num'] == node_num:
            return node_id
    return None


def get_node_short_name(node_id, interface):
    node_info = interface.nodes.get(node_id)
    if node_info:
        return node_info['user']['shortName']
    return None


def send_bulletin_to_bbs_nodes(board, sender_short_name, subject, content, unique_id, bbs_nodes, interface):
    message = f"BULLETIN|{board}|{sender_short_name}|{subject}|{content}|{unique_id}"
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_mail_to_bbs_nodes(sender_id, sender_short_name, recipient_id, subject, content, unique_id, bbs_nodes,
                           interface):
    message = f"MAIL|{sender_id}|{sender_short_name}|{recipient_id}|{subject}|{content}|{unique_id}"
    logging.info(f"SERVER SYNC: Syncing new mail message {subject} sent from {sender_short_name} to other BBS systems.")
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_delete_bulletin_to_bbs_nodes(bulletin_id, bbs_nodes, interface):
    message = f"DELETE_BULLETIN|{bulletin_id}"
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_delete_mail_to_bbs_nodes(unique_id, bbs_nodes, interface):
    message = f"DELETE_MAIL|{unique_id}"
    logging.info(f"SERVER SYNC: Sending delete mail sync message with unique_id: {unique_id}")
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_channel_to_bbs_nodes(name, url, bbs_nodes, interface):
    message = f"CHANNEL|{name}|{url}"
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def normalize_message(message, exclude=None):
    """
    Normalize repeated character messages (e.g., 'xx' -> 'x').
    
    Args:
        message: The message to normalize
        exclude: Optional list of strings to exclude from normalization
    
    Returns:
        Normalized message string
    """
    if exclude and message.lower() in exclude:
        return message
    if len(message) == 2 and message[1].lower() == 'x':
        return message[0]
    return message


def get_sender_short_name(sender_id, interface):
    """
    Helper to get sender's short name from sender_id.
    
    Args:
        sender_id: The numeric sender ID
        interface: The Meshtastic interface object
    
    Returns:
        Short name string
    """
    return get_node_short_name(get_node_id_from_num(sender_id, interface), interface)


def validate_item_selection(message, items, item_type="item"):
    """
    Validate user's numeric selection from a list of items.
    
    Args:
        message: User's input message
        items: List of items to select from
        item_type: Type of item for error messages
    
    Returns:
        Tuple of (success: bool, result: int or error_message: str)
    """
    try:
        selection = int(message) - 1
        if selection < 0 or selection >= len(items):
            return False, f"Invalid {item_type} number. Please try again."
        return True, selection
    except ValueError:
        return False, f"Invalid input. Please enter a valid {item_type} number."


def execute_db_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """
    Execute a database query with consistent error handling.
    
    Args:
        query: SQL query string
        params: Query parameters tuple
        fetch_one: Return single result
        fetch_all: Return all results
        commit: Commit changes after query
    
    Returns:
        Query results or None
    """
    from db_operations import get_db_connection
    
    conn = get_db_connection()
    c = conn.cursor()
    
    if params:
        c.execute(query, params)
    else:
        c.execute(query)
    
    if commit:
        conn.commit()
        return None
    
    if fetch_one:
        return c.fetchone()
    elif fetch_all:
        return c.fetchall()
    
    return None


def send_startup_announcement(interface, channel_index, message_text):
    """
    Send a startup announcement to a specific channel.
    
    Args:
        interface: The Meshtastic interface object
        channel_index: The channel index to send the announcement to
        message_text: The message to send
    """
    from meshtastic import BROADCAST_NUM
    
    logging.info(f"Sending startup announcement to channel {channel_index}: {message_text}")
    
    # Split into chunks if needed
    max_payload_size = 200

    if len(message_text) > max_payload_size:
        logging.error(f"Startup announcement is too long ({len(message_text)} chars). Max allowed is {max_payload_size}. Announcement not sent.")
    else :
        interface.sendText(
                text=message_text,
                destinationId=BROADCAST_NUM,
                channelIndex=channel_index,
                wantAck=False,
                wantResponse=False
            )
        logging.info(f"Sent startup announcement to channel {channel_index}")


def send_announcement(interface, channel_idx, announcement_text, max_size=200):
    """
    Send an announcement to a specific channel with validation.
    
    Args:
        interface: The Meshtastic interface object
        channel_idx: The channel index
        announcement_text: The text to send
        max_size: Maximum message size (default 200)
    
    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    from meshtastic import BROADCAST_NUM
    
    if len(announcement_text) > max_size:
        return False, f"Announcement too long ({len(announcement_text)} chars). Max allowed is {max_size}."
    
    try:
        interface.sendText(
            text=announcement_text,
            destinationId=BROADCAST_NUM,
            channelIndex=channel_idx,
            wantAck=False,
            wantResponse=False
        )
        return True, None
    except Exception as e:
        logging.error(f"Error sending announcement: {e}")
        return False, str(e)


def send_urgent_bulletin_notification(sender_short_name, subject, interface):
    """
    Send a notification for urgent bulletin posting.
    
    Args:
        sender_short_name: Short name of the bulletin sender
        subject: Subject of the bulletin
        interface: The Meshtastic interface object
    """
    from meshtastic import BROADCAST_NUM
    
    notification_message = f"💥NEW URGENT BULLETIN💥\nFrom: {sender_short_name}\nTitle: {subject}\nDM 'CB,,Urgent' to view"
    send_message(notification_message, BROADCAST_NUM, interface)
        
