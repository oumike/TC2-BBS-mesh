import configparser
import logging
import os
import random
import requests
import sqlite3
import time

from meshtastic import BROADCAST_NUM

from db_operations import (
    add_bulletin, add_mail, delete_mail,
    get_bulletin_content, get_bulletins,
    get_mail, get_mail_content,
    add_channel, get_channels, get_sender_id_by_mail_id
)
from utils import (
    get_node_id_from_num, get_node_info,
    get_node_short_name, send_message,
    update_user_state
)

# Read the configuration for menu options
config = configparser.ConfigParser()
config.read('config.ini')

main_menu_items = config['menu']['main_menu_items'].split(',')
bbs_menu_items = config['menu']['bbs_menu_items'].split(',')
utilities_menu_items = config['menu']['utilities_menu_items'].split(',')


def build_menu(items, menu_name):
    menu_str = f"{menu_name}\n"
    for item in items:
        if item.strip() == 'Q':
            menu_str += "[Q]uick Commands\n"
        elif item.strip() == 'B':
            if menu_name == "📰BBS Menu📰":
                menu_str += "[B]ulletins\n"
            else:
                menu_str += "[B]BS\n"
        elif item.strip() == 'U':
            menu_str += "[U]tilities\n"
        elif item.strip() == 'X':
            menu_str += "E[X]IT\n"
        elif item.strip() == 'M':
            menu_str += "[M]ail\n"
        elif item.strip() == 'C':
            menu_str += "[C]hannel Dir\n"
        elif item.strip() == 'J':
            menu_str += "[J]S8CALL\n"
        elif item.strip() == 'S':
            menu_str += "[S]tats\n"
        elif item.strip() == 'F':
            menu_str += "[F]ortune\n"
        elif item.strip() == 'W':
            menu_str += "[W]all of Shame\n"
        elif item.strip() == 'T':
            menu_str += "[T]op MQTT Topics\n"
        elif item.strip() == 'R':
            menu_str += "Weathe[R]\n"
        elif item.strip() == 'A':
            menu_str += "[A]nnouncement\n"
    return menu_str

def handle_help_command(sender_id, interface, menu_name=None):
    if menu_name:
        update_user_state(sender_id, {'command': 'MENU', 'menu': menu_name, 'step': 1})
        if menu_name == 'bbs':
            response = build_menu(bbs_menu_items, "📰BBS Menu📰")
        elif menu_name == 'utilities':
            response = build_menu(utilities_menu_items, "🛠️Utilities Menu🛠️")
    else:
        update_user_state(sender_id, {'command': 'MAIN_MENU', 'step': 1})  # Reset to main menu state
        mail = get_mail(get_node_id_from_num(sender_id, interface))
        response = build_menu(main_menu_items, f"💾TC² BBS💾 (✉️:{len(mail)})")
    send_message(response, sender_id, interface)

def get_node_name(node_id, interface):
    node_info = interface.nodes.get(node_id)
    if node_info:
        return node_info['user']['longName']
    return f"Node {node_id}"


def handle_mail_command(sender_id, interface):
    response = "✉️Mail Menu✉️\nWhat would you like to do with mail?\n[R]ead  [S]end E[X]IT"
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'MAIL', 'step': 1})



def handle_bulletin_command(sender_id, interface):
    response = f"📰Bulletin Menu📰\nWhich board would you like to enter?\n[G]eneral  [I]nfo  [N]ews  [U]rgent"
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'BULLETIN_MENU', 'step': 1})


def handle_exit_command(sender_id, interface):
    send_message("Type 'HELP' for a list of commands.", sender_id, interface)
    update_user_state(sender_id, None)


def handle_stats_command(sender_id, interface):
    response = "📊Stats Menu📊\nWhat stats would you like to view?\n[N]odes  [H]ardware  [R]oles  E[X]IT"
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'STATS', 'step': 1})


def handle_fortune_command(sender_id, interface):
    try:
        with open('fortunes.txt', 'r') as file:
            fortunes = file.readlines()
        if not fortunes:
            send_message("No fortunes available.", sender_id, interface)
            return
        fortune = random.choice(fortunes).strip()
        decorated_fortune = f"🔮 {fortune} 🔮"
        send_message(decorated_fortune, sender_id, interface)
    except Exception as e:
        send_message(f"Error generating fortune: {e}", sender_id, interface)


def handle_weather_command(sender_id, interface, location=None):
    """
    Fetch and display weather information for a given location.
    Location can be a zip code, or city,state format.
    If no location provided, uses default from config.
    """
    try:
        # Get API key and default location from config
        api_key = config.get('weather', 'api_key', fallback=None)
        
        if not api_key or api_key == 'YOUR_API_KEY_HERE':
            send_message("⚠️ Weather service not configured. Please set API key in config.ini", sender_id, interface)
            return
        
        # Use provided location or default from config
        if not location:
            location = config.get('weather', 'default_location', fallback='48336')
        
        units = config.get('weather', 'units', fallback='imperial')
        
        # Build API URL - OpenWeatherMap API
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        
        # Determine if location is a zip code or city name
        if location.isdigit():
            # Assume US zip code
            params = {
                'zip': f"{location},US",
                'appid': api_key,
                'units': units
            }
        else:
            # Assume city,state or city,country format
            params = {
                'q': location,
                'appid': api_key,
                'units': units
            }
        
        # Make API request
        response = requests.get(base_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract weather data
            location_name = data.get('name', 'Unknown')
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            humidity = data['main']['humidity']
            description = data['weather'][0]['description'].title()
            wind_speed = data['wind']['speed']
            
            # Determine temperature unit
            temp_unit = '°F' if units == 'imperial' else '°C'
            wind_unit = 'mph' if units == 'imperial' else 'm/s'
            
            # Format weather report
            weather_report = (
                f"🌤️ Weather for {location_name} 🌤️\n"
                f"Condition: {description}\n"
                f"Temp: {temp:.1f}{temp_unit}\n"
                f"Feels Like: {feels_like:.1f}{temp_unit}\n"
                f"Humidity: {humidity}%\n"
                f"Wind: {wind_speed:.1f} {wind_unit}"
            )
            
            send_message(weather_report, sender_id, interface)
        elif response.status_code == 404:
            send_message(f"❌ Location '{location}' not found. Try zip code or city,state format.", sender_id, interface)
        elif response.status_code == 401:
            send_message("⚠️ Invalid API key. Please check config.ini", sender_id, interface)
        else:
            send_message(f"❌ Weather service error: {response.status_code}", sender_id, interface)
            
    except requests.exceptions.Timeout:
        send_message("❌ Weather service timeout. Please try again.", sender_id, interface)
    except requests.exceptions.RequestException as e:
        logging.error(f"Weather API request error: {e}")
        send_message("❌ Unable to fetch weather data.", sender_id, interface)
    except Exception as e:
        logging.error(f"Error in weather command: {e}")
        send_message("❌ Error retrieving weather.", sender_id, interface)


def handle_stats_steps(sender_id, message, step, interface):
    message = message.lower().strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        choice = message
        if choice == 'x':
            handle_help_command(sender_id, interface)
            return
        elif choice == 'n':
            current_time = int(time.time())
            timeframes = {
                "All time": None,
                "Last 24 hours": 86400,
                "Last 8 hours": 28800,
                "Last hour": 3600
            }
            total_nodes_summary = []

            for period, seconds in timeframes.items():
                if seconds is None:
                    total_nodes = len(interface.nodes)
                else:
                    time_limit = current_time - seconds
                    total_nodes = sum(1 for node in interface.nodes.values() if node.get('lastHeard') is not None and node['lastHeard'] >= time_limit)
                total_nodes_summary.append(f"- {period}: {total_nodes}")

            response = "Total nodes seen:\n" + "\n".join(total_nodes_summary)
            send_message(response, sender_id, interface)
            handle_stats_command(sender_id, interface)
        elif choice == 'h':
            hw_models = {}
            for node in interface.nodes.values():
                hw_model = node['user'].get('hwModel', 'Unknown')
                hw_models[hw_model] = hw_models.get(hw_model, 0) + 1
            response = "Hardware Models:\n" + "\n".join([f"{model}: {count}" for model, count in hw_models.items()])
            send_message(response, sender_id, interface)
            handle_stats_command(sender_id, interface)
        elif choice == 'r':
            roles = {}
            for node in interface.nodes.values():
                role = node['user'].get('role', 'Unknown')
                roles[role] = roles.get(role, 0) + 1
            response = "Roles:\n" + "\n".join([f"{role}: {count}" for role, count in roles.items()])
            send_message(response, sender_id, interface)
            handle_stats_command(sender_id, interface)


def handle_bb_steps(sender_id, message, step, state, interface, bbs_nodes):
    boards = {0: "General", 1: "Info", 2: "News", 3: "Urgent"}
    if step == 1:
        if message.lower() == 'e':
            handle_help_command(sender_id, interface, 'bbs')
            return
        board_name = boards[int(message)]
        bulletins = get_bulletins(board_name)
        response = f"{board_name} has {len(bulletins)} messages.\n[R]ead  [P]ost"
        send_message(response, sender_id, interface)
        update_user_state(sender_id, {'command': 'BULLETIN_ACTION', 'step': 2, 'board': board_name})

    elif step == 2:
        board_name = state['board']
        if message.lower() == 'r':
            bulletins = get_bulletins(board_name)
            if bulletins:
                send_message(f"Select a bulletin number to view from {board_name}:", sender_id, interface)
                for bulletin in bulletins:
                    send_message(f"[{bulletin[0]}] {bulletin[1]}", sender_id, interface)
                update_user_state(sender_id, {'command': 'BULLETIN_READ', 'step': 3, 'board': board_name})
            else:
                send_message(f"No bulletins in {board_name}.", sender_id, interface)
                handle_bb_steps(sender_id, 'e', 1, state, interface, bbs_nodes)
        elif message.lower() == 'p':
            if board_name.lower() == 'urgent':
                node_id = get_node_id_from_num(sender_id, interface)
                allowed_nodes = interface.allowed_nodes
                logging.info(f"Checking permissions for node_id: {node_id} with allowed_nodes: {allowed_nodes}")  # Debug statement
                if allowed_nodes and node_id not in allowed_nodes:
                    send_message("You don't have permission to post to this board.", sender_id, interface)
                    handle_bb_steps(sender_id, 'e', 1, state, interface, bbs_nodes)
                    return
            send_message("What is the subject of your bulletin? Keep it short.", sender_id, interface)
            update_user_state(sender_id, {'command': 'BULLETIN_POST', 'step': 4, 'board': board_name})

    elif step == 3:
        bulletin_id = int(message)
        sender_short_name, date, subject, content, unique_id = get_bulletin_content(bulletin_id)
        send_message(f"From: {sender_short_name}\nDate: {date}\nSubject: {subject}\n- - - - - - -\n{content}", sender_id, interface)
        board_name = state['board']
        handle_bb_steps(sender_id, 'e', 1, state, interface, bbs_nodes)

    elif step == 4:
        subject = message
        send_message("Send the contents of your bulletin. Send a message with END when finished.", sender_id, interface)
        update_user_state(sender_id, {'command': 'BULLETIN_POST_CONTENT', 'step': 5, 'board': state['board'], 'subject': subject, 'content': ''})

    elif step == 5:
        if message.lower() == "end":
            board = state['board']
            subject = state['subject']
            content = state['content']
            node_id = get_node_id_from_num(sender_id, interface)
            node_info = interface.nodes.get(node_id)
            if node_info is None:
                send_message("Error: Unable to retrieve your node information.", sender_id, interface)
                update_user_state(sender_id, None)
                return
            sender_short_name = node_info['user'].get('shortName', f"Node {sender_id}")
            unique_id = add_bulletin(board, sender_short_name, subject, content, bbs_nodes, interface)
            send_message(f"Your bulletin '{subject}' has been posted to {board}.\n(╯°□°)╯📄📌[{board}]", sender_id, interface)
            handle_bb_steps(sender_id, 'e', 1, state, interface, bbs_nodes)
        else:
            state['content'] += message + "\n"
            update_user_state(sender_id, state)



def handle_mail_steps(sender_id, message, step, state, interface, bbs_nodes):
    message = message.strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        choice = message.lower()
        if choice == 'r':
            sender_node_id = get_node_id_from_num(sender_id, interface)
            mail = get_mail(sender_node_id)
            if mail:
                send_message(f"You have {len(mail)} mail messages. Select a message number to read:", sender_id, interface)
                for msg in mail:
                    send_message(f"-{msg[0]}-\nDate: {msg[3]}\nFrom: {msg[1]}\nSubject: {msg[2]}", sender_id, interface)
                update_user_state(sender_id, {'command': 'MAIL', 'step': 2})
            else:
                send_message("There are no messages in your mailbox.📭", sender_id, interface)
                update_user_state(sender_id, None)
        elif choice == 's':
            send_message("What is the Short Name of the node you want to leave a message for?", sender_id, interface)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 3})
        elif choice == 'x':
            handle_help_command(sender_id, interface)

    elif step == 2:
        mail_id = int(message)
        try:
            sender_node_id = get_node_id_from_num(sender_id, interface)
            sender, date, subject, content, unique_id = get_mail_content(mail_id, sender_node_id)
            send_message(f"Date: {date}\nFrom: {sender}\nSubject: {subject}\n{content}", sender_id, interface)
            send_message("What would you like to do with this message?\n[K]eep  [D]elete  [R]eply", sender_id, interface)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 4, 'mail_id': mail_id, 'unique_id': unique_id, 'sender': sender, 'subject': subject, 'content': content})
        except TypeError:
            logging.info(f"Node {sender_id} tried to access non-existent message")
            send_message("Mail not found", sender_id, interface)
            update_user_state(sender_id, None)

    elif step == 3:
        short_name = message.lower()
        nodes = get_node_info(interface, short_name)
        if not nodes:
            send_message("I'm unable to find that node in my database.", sender_id, interface)
            handle_mail_command(sender_id, interface)
        elif len(nodes) == 1:
            recipient_id = nodes[0]['num']
            recipient_name = get_node_name(recipient_id, interface)
            send_message(f"What is the subject of your message to {recipient_name}?\nKeep it short.", sender_id, interface)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 5, 'recipient_id': recipient_id})
        else:
            send_message("There are multiple nodes with that short name. Which one would you like to leave a message for?", sender_id, interface)
            for i, node in enumerate(nodes):
                send_message(f"[{i}] {node['longName']}", sender_id, interface)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 6, 'nodes': nodes})

    elif step == 4:
        if message.lower() == "d":
            unique_id = state['unique_id']
            sender_node_id = get_node_id_from_num(sender_id, interface)
            delete_mail(unique_id, sender_node_id, bbs_nodes, interface)
            send_message("The message has been deleted 🗑️", sender_id, interface)
            update_user_state(sender_id, None)
        elif message.lower() == "r":
            sender = state['sender']
            send_message(f"Send your reply to {sender} now, followed by a message with END", sender_id, interface)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 7, 'reply_to_mail_id': state['mail_id'], 'subject': f"Re: {state['subject']}", 'content': ''})
        else:
            send_message("The message has been kept in your inbox.✉️", sender_id, interface)
            update_user_state(sender_id, None)

    elif step == 5:
        subject = message
        send_message("Send your message. You can send it in multiple messages if it's too long for one.\nSend a single message with END when you're done", sender_id, interface)
        update_user_state(sender_id, {'command': 'MAIL', 'step': 7, 'recipient_id': state['recipient_id'], 'subject': subject, 'content': ''})

    elif step == 6:
        selected_node_index = int(message)
        selected_node = state['nodes'][selected_node_index]
        recipient_id = selected_node['num']
        recipient_name = get_node_name(recipient_id, interface)
        send_message(f"What is the subject of your message to {recipient_name}?\nKeep it short.", sender_id, interface)
        update_user_state(sender_id, {'command': 'MAIL', 'step': 5, 'recipient_id': recipient_id})

    elif step == 7:
        if message.lower() == "end":
            if 'reply_to_mail_id' in state:
                recipient_id = get_sender_id_by_mail_id(state['reply_to_mail_id'])  # Get the sender ID from the mail ID
            else:
                recipient_id = state.get('recipient_id')
            subject = state['subject']
            content = state['content']
            recipient_name = get_node_name(recipient_id, interface)

            sender_short_name = get_node_short_name(get_node_id_from_num(sender_id, interface), interface)
            unique_id = add_mail(get_node_id_from_num(sender_id, interface), sender_short_name, recipient_id, subject, content, bbs_nodes, interface)
            send_message(f"Mail has been posted to the mailbox of {recipient_name}.\n(╯°□°)╯📨📬", sender_id, interface)

            notification_message = f"You have a new mail message from {sender_short_name}. Check your mailbox by responding to this message with CM."
            send_message(notification_message, recipient_id, interface)

            update_user_state(sender_id, None)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 8})
        else:
            state['content'] += message + "\n"
            update_user_state(sender_id, state)

    elif step == 8:
        if message.lower() == "y":
            handle_mail_command(sender_id, interface)
        else:
            send_message("Okay, feel free to send another command.", sender_id, interface)
            update_user_state(sender_id, None)


def handle_wall_of_shame_command(sender_id, interface):
    response = "Devices with battery levels below 20%:\n"
    for node_id, node in interface.nodes.items():
        metrics = node.get('deviceMetrics', {})
        battery_level = metrics.get('batteryLevel', 101)
        if battery_level < 20:
            long_name = node['user']['longName']
            response += f"{long_name} - Battery {battery_level}%\n"
    if response == "Devices with battery levels below 20%:\n":
        response = "No devices with battery levels below 20% found."
    send_message(response, sender_id, interface)


def handle_mqtt_topics_command(sender_id, interface):
    db_path = 'mqtt_counts.db'
    if not os.path.exists(db_path):
        send_message("MQTT topic statistics are unavailable.", sender_id, interface)
        return

    try:
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute(
                """
                SELECT base_topic, subtopic, message_count
                FROM topic_counts
                ORDER BY message_count DESC
                LIMIT 15
                """
            )
            rows = cursor.fetchall()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        logging.error(f"Error reading MQTT topic stats: {exc}")
        send_message("Unable to read MQTT topic statistics.", sender_id, interface)
        return

    if not rows:
        send_message("MQTT topic statistics are unavailable.", sender_id, interface)
        return

    # Send header first
    send_message("🏆 Top 15 Topics 🏆", sender_id, interface)
    time.sleep(3)  # Delay before sending first chunk
    
    # Build all topic lines
    topic_lines = []
    for idx, (base_topic, subtopic, message_count) in enumerate(rows, start=1):
        topic = base_topic if not subtopic else f"{base_topic}/{subtopic}"
        # Remove msh/US/MI prefix to save space
        if topic.startswith("msh/US/MI/"):
            topic = topic[10:]  # Remove "msh/US/MI/"
        elif topic == "msh/US/MI":
            topic = "(base)"
        topic_lines.append(f"{idx:02d}. {topic} — {message_count:,}")
    
    # Send in chunks of 3 lines per message
    chunk_size = 3
    for i in range(0, len(topic_lines), chunk_size):
        chunk = topic_lines[i:i + chunk_size]
        send_message("\n".join(chunk), sender_id, interface)
        # Add delay between chunks to prevent message loss on mesh network
        if i + chunk_size < len(topic_lines):
            time.sleep(3)
    
    # Send end message
    time.sleep(3)
    send_message("🏁 End of Topics 🏁", sender_id, interface)


def handle_channel_directory_command(sender_id, interface):
    response = "📚CHANNEL DIRECTORY📚\nWhat would you like to do?\n[V]iew  [P]ost  E[X]IT"
    send_message(response, sender_id, interface)
    update_user_state(sender_id, {'command': 'CHANNEL_DIRECTORY', 'step': 1})


def handle_channel_directory_steps(sender_id, message, step, state, interface):
    message = message.strip()
    if len(message) == 2 and message[1] == 'x':
        message = message[0]

    if step == 1:
        choice = message
        if choice.lower() == 'x':
            handle_help_command(sender_id, interface)
            return
        elif choice.lower() == 'v':
            channels = get_channels()
            if channels:
                response = "Select a channel number to view:\n" + "\n".join(
                    [f"[{i}] {channel[0]}" for i, channel in enumerate(channels)])
                send_message(response, sender_id, interface)
                update_user_state(sender_id, {'command': 'CHANNEL_DIRECTORY', 'step': 2})
            else:
                send_message("No channels available in the directory.", sender_id, interface)
                handle_channel_directory_command(sender_id, interface)
        elif choice.lower() == 'p':
            send_message("Name your channel for the directory:", sender_id, interface)
            update_user_state(sender_id, {'command': 'CHANNEL_DIRECTORY', 'step': 3})

    elif step == 2:
        channel_index = int(message)
        channels = get_channels()
        if 0 <= channel_index < len(channels):
            channel_name, channel_url = channels[channel_index]
            send_message(f"Channel Name: {channel_name}\nChannel URL:\n{channel_url}", sender_id, interface)
        handle_channel_directory_command(sender_id, interface)

    elif step == 3:
        channel_name = message
        send_message("Send a message with your channel URL or PSK:", sender_id, interface)
        update_user_state(sender_id, {'command': 'CHANNEL_DIRECTORY', 'step': 4, 'channel_name': channel_name})

    elif step == 4:
        channel_url = message
        channel_name = state['channel_name']
        add_channel(channel_name, channel_url)
        send_message(f"Your channel '{channel_name}' has been added to the directory.", sender_id, interface)
        handle_channel_directory_command(sender_id, interface)


def handle_send_mail_command(sender_id, message, interface, bbs_nodes):
    try:
        parts = message.split(",,", 3)
        if len(parts) != 4:
            send_message("Send Mail Quick Command format:\nSM,,{short_name},,{subject},,{message}", sender_id, interface)
            return

        _, short_name, subject, content = parts
        nodes = get_node_info(interface, short_name.lower())
        if not nodes:
            send_message(f"Node with short name '{short_name}' not found.", sender_id, interface)
            return
        if len(nodes) > 1:
            send_message(f"Multiple nodes with short name '{short_name}' found. Please be more specific.", sender_id,
                         interface)
            return

        recipient_id = nodes[0]['num']
        recipient_name = get_node_name(recipient_id, interface)
        sender_short_name = get_node_short_name(get_node_id_from_num(sender_id, interface), interface)

        unique_id = add_mail(get_node_id_from_num(sender_id, interface), sender_short_name, recipient_id, subject,
                             content, bbs_nodes, interface)
        send_message(f"Mail has been sent to {recipient_name}.", sender_id, interface)

        notification_message = f"You have a new mail message from {sender_short_name}. Check your mailbox by responding to this message with CM."
        send_message(notification_message, recipient_id, interface)

    except Exception as e:
        logging.error(f"Error processing send mail command: {e}")
        send_message("Error processing send mail command.", sender_id, interface)


def handle_check_mail_command(sender_id, interface):
    try:
        sender_node_id = get_node_id_from_num(sender_id, interface)
        mail = get_mail(sender_node_id)
        if not mail:
            send_message("You have no new messages.", sender_id, interface)
            return

        response = "📬 You have the following messages:\n"
        for i, msg in enumerate(mail):
            response += f"{i + 1:02d}. From: {msg[1]}, Subject: {msg[2]}\n"
        response += "\nPlease reply with the number of the message you want to read."
        send_message(response, sender_id, interface)

        update_user_state(sender_id, {'command': 'CHECK_MAIL', 'step': 1, 'mail': mail})

    except Exception as e:
        logging.error(f"Error processing check mail command: {e}")
        send_message("Error processing check mail command.", sender_id, interface)


def handle_read_mail_command(sender_id, message, state, interface):
    try:
        mail = state.get('mail', [])
        message_number = int(message) - 1

        if message_number < 0 or message_number >= len(mail):
            send_message("Invalid message number. Please try again.", sender_id, interface)
            return

        mail_id = mail[message_number][0]
        sender_node_id = get_node_id_from_num(sender_id, interface)
        sender, date, subject, content, unique_id = get_mail_content(mail_id, sender_node_id)
        response = f"Date: {date}\nFrom: {sender}\nSubject: {subject}\n\n{content}"
        send_message(response, sender_id, interface)
        send_message("What would you like to do with this message?\n[K]eep  [D]elete  [R]eply", sender_id, interface)
        update_user_state(sender_id, {'command': 'CHECK_MAIL', 'step': 2, 'mail_id': mail_id, 'unique_id': unique_id, 'sender': sender, 'subject': subject, 'content': content})

    except ValueError:
        send_message("Invalid input. Please enter a valid message number.", sender_id, interface)
    except Exception as e:
        logging.error(f"Error processing read mail command: {e}")
        send_message("Error processing read mail command.", sender_id, interface)


def handle_delete_mail_confirmation(sender_id, message, state, interface, bbs_nodes):
    try:
        choice = message.lower().strip()
        if len(choice) == 2 and choice[1] == 'x':
            choice = choice[0]

        if choice == 'd':
            unique_id = state['unique_id']
            sender_node_id = get_node_id_from_num(sender_id, interface)
            delete_mail(unique_id, sender_node_id, bbs_nodes, interface)
            send_message("The message has been deleted 🗑️", sender_id, interface)
            update_user_state(sender_id, None)
        elif choice == 'r':
            sender = state['sender']
            send_message(f"Send your reply to {sender} now, followed by a message with END", sender_id, interface)
            update_user_state(sender_id, {'command': 'MAIL', 'step': 7, 'reply_to_mail_id': state['mail_id'], 'subject': f"Re: {state['subject']}", 'content': ''})
        else:
            send_message("The message has been kept in your inbox.✉️", sender_id, interface)
            update_user_state(sender_id, None)

    except Exception as e:
        logging.error(f"Error processing delete mail confirmation: {e}")
        send_message("Error processing delete mail confirmation.", sender_id, interface)



def handle_post_bulletin_command(sender_id, message, interface, bbs_nodes):
    try:
        parts = message.split(",,", 3)
        if len(parts) != 4:
            send_message("Post Bulletin Quick Command format:\nPB,,{board_name},,{subject},,{content}", sender_id, interface)
            return

        _, board_name, subject, content = parts
        sender_short_name = get_node_short_name(get_node_id_from_num(sender_id, interface), interface)

        unique_id = add_bulletin(board_name, sender_short_name, subject, content, bbs_nodes, interface)
        send_message(f"Your bulletin '{subject}' has been posted to {board_name}.", sender_id, interface)


    except Exception as e:
        logging.error(f"Error processing post bulletin command: {e}")
        send_message("Error processing post bulletin command.", sender_id, interface)


def handle_check_bulletin_command(sender_id, message, interface):
    try:
        # Split the message only once
        parts = message.split(",,", 1)
        if len(parts) != 2 or not parts[1].strip():
            send_message("Check Bulletins Quick Command format:\nCB,,board_name", sender_id, interface)
            return

        boards = {0: "General", 1: "Info", 2: "News", 3: "Urgent"} #list of boards
        board_name = parts[1].strip().capitalize() #get board name from quick command and capitalize it
        board_name = boards[next(key for key, value in boards.items() if value == board_name)] #search for board name in list

        bulletins = get_bulletins(board_name)
        if not bulletins:
            send_message(f"No bulletins available on {board_name} board.", sender_id, interface)
            return

        response = f"📰 Bulletins on {board_name} board:\n"
        for i, bulletin in enumerate(bulletins):
            response += f"[{i+1:02d}] Subject: {bulletin[1]}, From: {bulletin[2]}, Date: {bulletin[3]}\n"
        response += "\nPlease reply with the number of the bulletin you want to read."
        send_message(response, sender_id, interface)

        update_user_state(sender_id, {'command': 'CHECK_BULLETIN', 'step': 1, 'board_name': board_name, 'bulletins': bulletins})

    except Exception as e:
        logging.error(f"Error processing check bulletin command: {e}")
        send_message("Error processing check bulletin command.", sender_id, interface)

def handle_read_bulletin_command(sender_id, message, state, interface):
    try:
        bulletins = state.get('bulletins', [])
        message_number = int(message) - 1

        if message_number < 0 or message_number >= len(bulletins):
            send_message("Invalid bulletin number. Please try again.", sender_id, interface)
            return

        bulletin_id = bulletins[message_number][0]
        sender, date, subject, content, unique_id = get_bulletin_content(bulletin_id)
        response = f"Date: {date}\nFrom: {sender}\nSubject: {subject}\n\n{content}"
        send_message(response, sender_id, interface)

        update_user_state(sender_id, None)

    except ValueError:
        send_message("Invalid input. Please enter a valid bulletin number.", sender_id, interface)
    except Exception as e:
        logging.error(f"Error processing read bulletin command: {e}")
        send_message("Error processing read bulletin command.", sender_id, interface)


def handle_post_channel_command(sender_id, message, interface):
    try:
        parts = message.split("|", 3)
        if len(parts) != 3:
            send_message("Post Channel Quick Command format:\nCHP,,{channel_name},,{channel_url}", sender_id, interface)
            return

        _, channel_name, channel_url = parts
        bbs_nodes = interface.bbs_nodes
        add_channel(channel_name, channel_url, bbs_nodes, interface)
        send_message(f"Channel '{channel_name}' has been added to the directory.", sender_id, interface)

    except Exception as e:
        logging.error(f"Error processing post channel command: {e}")
        send_message("Error processing post channel command.", sender_id, interface)


def handle_check_channel_command(sender_id, interface):
    try:
        channels = get_channels()
        if not channels:
            send_message("No channels available in the directory.", sender_id, interface)
            return

        response = "Available Channels:\n"
        for i, channel in enumerate(channels):
            response += f"{i + 1:02d}. Name: {channel[0]}\n"
        response += "\nPlease reply with the number of the channel you want to view."
        send_message(response, sender_id, interface)

        update_user_state(sender_id, {'command': 'CHECK_CHANNEL', 'step': 1, 'channels': channels})

    except Exception as e:
        logging.error(f"Error processing check channel command: {e}")
        send_message("Error processing check channel command.", sender_id, interface)


def handle_read_channel_command(sender_id, message, state, interface):
    try:
        channels = state.get('channels', [])
        message_number = int(message) - 1

        if message_number < 0 or message_number >= len(channels):
            send_message("Invalid channel number. Please try again.", sender_id, interface)
            return

        channel_name, channel_url = channels[message_number]
        response = f"Channel Name: {channel_name}\nChannel URL: {channel_url}"
        send_message(response, sender_id, interface)

        update_user_state(sender_id, None)

    except ValueError:
        send_message("Invalid input. Please enter a valid channel number.", sender_id, interface)
    except Exception as e:
        logging.error(f"Error processing read channel command: {e}")
        send_message("Error processing read channel command.", sender_id, interface)


def handle_list_channels_command(sender_id, interface):
    try:
        channels = get_channels()
        if not channels:
            send_message("No channels available in the directory.", sender_id, interface)
            return

        response = "Available Channels:\n"
        for i, channel in enumerate(channels):
            response += f"{i+1:02d}. Name: {channel[0]}\n"
        response += "\nPlease reply with the number of the channel you want to view."
        send_message(response, sender_id, interface)

        update_user_state(sender_id, {'command': 'LIST_CHANNELS', 'step': 1, 'channels': channels})

    except Exception as e:
        logging.error(f"Error processing list channels command: {e}")
        send_message("Error processing list channels command.", sender_id, interface)


def handle_quick_help_command(sender_id, interface):
    response = ("✈️QUICK COMMANDS✈️\nSend command below for usage info:\nSM,, - Send "
                "Mail\nCM - Check Mail\nPB,, - Post Bulletin\nCB,, - Check Bulletins\nTT - Top MQTT Topics\n"
                "WX - Weather (WX or WX,location)\n")
    send_message(response, sender_id, interface)


def get_channel_list(interface):
    """
    Retrieve the list of channels from the Meshtastic device.
    
    Args:
        interface: The Meshtastic interface object
        
    Returns:
        list: List of channel dictionaries with channel information
    """
    try:
        channels = []
        
        # Access channels from the local node
        if hasattr(interface, 'localNode') and hasattr(interface.localNode, 'channels'):
            for idx, channel in enumerate(interface.localNode.channels):
                if channel.settings and (channel.settings.name or idx == 0):
                    channel_info = {
                        'index': idx,
                        'name': channel.settings.name if channel.settings.name else f"Channel {idx}",
                        'role': channel.role
                    }
                    channels.append(channel_info)
        
        return channels
    except Exception as e:
        logging.error(f"Error retrieving channels: {e}")
        return []


def handle_announcement_command(sender_id, interface):
    """Handle the announcement command - shows available channels."""
    try:
        channels = get_channel_list(interface)
        
        if not channels:
            send_message("❌ No channels available on device.", sender_id, interface)
            handle_help_command(sender_id, interface, 'utilities')
            return
        
        # Send header message first
        send_message("📢 ANNOUNCEMENT 📢\nSelect a channel to broadcast to:", sender_id, interface)
        time.sleep(3)
        
        # Split channels into two messages
        mid_point = (len(channels) + 1) // 2
        
        # First half of channels
        response1 = ""
        for channel in channels[:mid_point]:
            if channel['name'] == "Channel 0":
                display_name = "Default"
            else:
                display_name = channel['name']

            response1 += f"[{channel['index']}] {display_name}\n"
        send_message(response1.strip(), sender_id, interface)
        time.sleep(3)
        
        # Second half of channels
        response2 = ""
        for channel in channels[mid_point:]:
            if channel['name'] == "Channel 0":
                display_name = "Default"
            else:
                display_name = channel['name']
            response2 += f"[{channel['index']}] {display_name}\n"
        send_message(response2.strip(), sender_id, interface)
        time.sleep(3)
        
        # Send instructions as separate message
        send_message("Reply with channel number or X to cancel", sender_id, interface)
        
        update_user_state(sender_id, {'command': 'ANNOUNCEMENT', 'step': 1, 'channels': channels})
        
    except Exception as e:
        logging.error(f"Error in announcement command: {e}")
        send_message("❌ Error retrieving channels.", sender_id, interface)
        handle_help_command(sender_id, interface, 'utilities')


def handle_announcement_steps(sender_id, message, step, state, interface):
    """Handle the multi-step announcement process."""
    message_lower = message.lower().strip()
    
    try:
        if step == 1:
            # Channel selection
            if message_lower == 'x':
                send_message("Announcement cancelled.", sender_id, interface)
                handle_help_command(sender_id, interface, 'utilities')
                return
            
            try:
                channel_idx = int(message.strip())
                channels = state.get('channels', [])
                
                # Validate channel selection
                selected_channel = next((ch for ch in channels if ch['index'] == channel_idx), None)
                
                if not selected_channel:
                    send_message("Invalid channel number. Please try again or send X to cancel.", sender_id, interface)
                    return
                
                send_message(f"Selected: {selected_channel['name']}\nEnter your announcement message.\nType END on a new line when finished.", sender_id, interface)
                update_user_state(sender_id, {
                    'command': 'ANNOUNCEMENT',
                    'step': 2,
                    'channel_idx': channel_idx,
                    'channel_name': selected_channel['name'],
                    'message': ''
                })
                
            except ValueError:
                send_message("Invalid input. Please enter a channel number or X to cancel.", sender_id, interface)
                return
        
        elif step == 2:
            # Message input
            if message_lower == 'end':
                announcement_text = state.get('message', '').strip()
                
                if not announcement_text:
                    send_message("No message entered. Announcement cancelled.", sender_id, interface)
                    handle_help_command(sender_id, interface, 'utilities')
                    return
                
                # Show preview and ask for confirmation
                channel_name = state.get('channel_name', 'Unknown')
                preview = f"📢 PREVIEW 📢\nChannel: {channel_name}\n---\n{announcement_text}\n---\nSend this? [Y]es or [N]o"
                send_message(preview, sender_id, interface)
                update_user_state(sender_id, {
                    'command': 'ANNOUNCEMENT',
                    'step': 3,
                    'channel_idx': state['channel_idx'],
                    'channel_name': channel_name,
                    'message': announcement_text
                })
            else:
                # Accumulate message
                current_message = state.get('message', '')
                if current_message:
                    current_message += '\n'
                current_message += message
                
                state['message'] = current_message
                update_user_state(sender_id, state)
        
        elif step == 3:
            # Confirmation
            if message_lower == 'y':
                channel_idx = state.get('channel_idx')
                announcement_text = state.get('message', '')
                
                # Send the announcement
                from meshtastic import BROADCAST_NUM
                
                # Split into chunks if needed
                max_payload_size = 200
                chunks = [announcement_text[i:i + max_payload_size] 
                         for i in range(0, len(announcement_text), max_payload_size)]
                
                logging.info(f"Sending announcement to channel {channel_idx} in {len(chunks)} chunk(s)")
                
                for i, chunk in enumerate(chunks):
                    try:
                        interface.sendText(
                            text=chunk,
                            destinationId=BROADCAST_NUM,
                            channelIndex=channel_idx,
                            wantAck=False,
                            wantResponse=False
                        )
                        logging.info(f"Sent announcement chunk {i+1}/{len(chunks)}")
                        
                        if i < len(chunks) - 1:
                            time.sleep(2)
                    except Exception as e:
                        logging.error(f"Error sending announcement chunk {i+1}: {e}")
                        send_message(f"❌ Error sending announcement: {e}", sender_id, interface)
                        update_user_state(sender_id, None)
                        return
                
                send_message("✅ Announcement sent successfully!", sender_id, interface)
                update_user_state(sender_id, None)
                
            elif message_lower == 'n':
                send_message("Announcement cancelled.", sender_id, interface)
                handle_help_command(sender_id, interface, 'utilities')
            else:
                send_message("Please reply with Y to send or N to cancel.", sender_id, interface)
                
    except Exception as e:
        logging.error(f"Error in announcement steps: {e}")
        send_message(f"❌ Error processing announcement: {e}", sender_id, interface)
        update_user_state(sender_id, None)

