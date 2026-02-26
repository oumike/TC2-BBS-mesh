import logging
import time

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
            logging.info(f"REPLY SEND ERROR {e.message}")

        
        time.sleep(2)


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


def get_sender_node_id(sender_id, interface):
    """
    Get the sender's node ID from their numeric ID.
    This is a convenience wrapper around get_node_id_from_num.
    
    Args:
        sender_id: The numeric sender ID
        interface: The Meshtastic interface object
    
    Returns:
        The node ID (hex string) or None
    """
    return get_node_id_from_num(sender_id, interface)


def get_sender_short_name(sender_id, interface):
    """
    Get the sender's short name directly from their numeric ID.
    
    Args:
        sender_id: The numeric sender ID
        interface: The Meshtastic interface object
    
    Returns:
        The short name or None
    """
    node_id = get_node_id_from_num(sender_id, interface)
    if node_id:
        return get_node_short_name(node_id, interface)
    return None


def broadcast_to_bbs_nodes(message, bbs_nodes, interface, log_message=None):
    """
    Broadcast a message to all BBS nodes.
    
    Args:
        message: The message to broadcast
        bbs_nodes: List of BBS node IDs to send to
        interface: The Meshtastic interface object
        log_message: Optional log message to output
    """
    if log_message:
        logging.info(log_message)
    
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_bulletin_to_bbs_nodes(board, sender_short_name, subject, content, unique_id, bbs_nodes, interface):
    message = f"BULLETIN|{board}|{sender_short_name}|{subject}|{content}|{unique_id}"
    broadcast_to_bbs_nodes(message, bbs_nodes, interface)


def send_mail_to_bbs_nodes(sender_id, sender_short_name, recipient_id, subject, content, unique_id, bbs_nodes,
                           interface):
    message = f"MAIL|{sender_id}|{sender_short_name}|{recipient_id}|{subject}|{content}|{unique_id}"
    log_msg = f"SERVER SYNC: Syncing new mail message {subject} sent from {sender_short_name} to other BBS systems."
    broadcast_to_bbs_nodes(message, bbs_nodes, interface, log_msg)


def send_delete_bulletin_to_bbs_nodes(bulletin_id, bbs_nodes, interface):
    message = f"DELETE_BULLETIN|{bulletin_id}"
    broadcast_to_bbs_nodes(message, bbs_nodes, interface)


def send_delete_mail_to_bbs_nodes(unique_id, bbs_nodes, interface):
    message = f"DELETE_MAIL|{unique_id}"
    log_msg = f"SERVER SYNC: Sending delete mail sync message with unique_id: {unique_id}"
    broadcast_to_bbs_nodes(message, bbs_nodes, interface, log_msg)


def send_channel_to_bbs_nodes(name, url, bbs_nodes, interface):
    message = f"CHANNEL|{name}|{url}"
    broadcast_to_bbs_nodes(message, bbs_nodes, interface)


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
        
