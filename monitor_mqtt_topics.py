#!/usr/bin/env python3

import argparse
import logging
import signal
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import paho.mqtt.client as mqtt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor MQTT topics and tally message counts per subtopic.")
    parser.add_argument("--broker-host", default="mqtt.meshtastic.org", help="MQTT broker hostname or IP address")
    parser.add_argument("--broker-port", type=int, default=1883, help="MQTT broker TCP port")
    parser.add_argument(
        "--base-topic",
        default="msh/US/MI",
        help="Base topic to monitor; script subscribes to <base-topic>/#",
    )
    parser.add_argument("--client-id", default=None, help="Custom MQTT client identifier")
    parser.add_argument("--username", default="meshdev", help="Username for broker authentication")
    parser.add_argument("--password", default="large4cats", help="Password for broker authentication")
    parser.add_argument("--db-path", default="mqtt_counts.db", help="Path to SQLite database for storing counts")
    parser.add_argument("--keepalive", type=int, default=60, help="MQTT keepalive in seconds")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Suppress all logging output regardless of log level",
    )
    return parser.parse_args()


def create_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    # Limit WAL file to ~20MB (5000 pages * 4KB default page size)
    conn.execute("PRAGMA wal_autocheckpoint=5000;")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS topic_counts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            base_topic TEXT NOT NULL,
            subtopic TEXT NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            UNIQUE(base_topic, subtopic)
        )
        """
    )
    conn.commit()


def normalize_base_topic(topic: str) -> str:
    cleaned = topic.strip()
    if cleaned.endswith("/#"):
        cleaned = cleaned[:-2]
    return cleaned.rstrip("/")


def extract_subtopic(full_topic: str, base_topic: str) -> str:
    base = normalize_base_topic(base_topic)
    if full_topic == base:
        return ""
    if full_topic.startswith(base + "/"):
        return full_topic[len(base) + 1 :]
    return full_topic


def canonicalize_subtopic(raw_subtopic: str) -> Optional[str]:
    """Derive the routing bucket identifier from the raw subtopic."""
    if raw_subtopic == "":
        return ""

    trimmed = raw_subtopic
    excl_index = trimmed.find("/!")
    if excl_index != -1:
        trimmed = trimmed[:excl_index]

    parts: list[str] = []
    for segment in trimmed.split("/"):
        if not segment or segment.startswith("!"):
            continue
        parts.append(segment)

    if not parts:
        return None

    return parts[-1]


class TopicCounter:
    def __init__(self, conn: sqlite3.Connection, base_topic: str):
        self.conn = conn
        self.base_topic = normalize_base_topic(base_topic)
        self.lock = threading.Lock()

    def increment(self, subtopic: str) -> Optional[int]:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

        with self.lock:
            self.conn.execute(
                """
                INSERT INTO topic_counts (base_topic, subtopic, message_count, first_seen, last_seen)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(base_topic, subtopic)
                DO UPDATE SET
                    message_count = message_count + 1,
                    last_seen = excluded.last_seen
                """,
                (self.base_topic, subtopic, timestamp, timestamp),
            )
            self.conn.commit()

            cursor = self.conn.execute(
                "SELECT message_count FROM topic_counts WHERE base_topic = ? AND subtopic = ?",
                (self.base_topic, subtopic),
            )
            row = cursor.fetchone()

        if row is None:
            return None
        return row[0]


def setup_logging(level: str, silent: bool) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if silent:
        logging.disable(logging.CRITICAL)


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level, args.silent)

    conn = create_connection(args.db_path)
    ensure_schema(conn)

    counter = TopicCounter(conn, args.base_topic)
    subscribe_topic = f"{counter.base_topic}/#"

    stop_event = threading.Event()

    def handle_signal(signum, frame):
        logging.info("Signal received; shutting down.")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    client = mqtt.Client(
        client_id=args.client_id,
        userdata={"counter": counter},
        protocol=mqtt.MQTTv311,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    if args.username:
        client.username_pw_set(args.username, args.password)

    def on_connect(_client, _userdata, _flags, reason_code, _properties=None):
        if reason_code == 0:
            logging.info("Connected to MQTT broker %s:%s", args.broker_host, args.broker_port)
            _client.subscribe(subscribe_topic)
            logging.info("Subscribed to %s", subscribe_topic)
        else:
            logging.warning("MQTT connection failed: %s", reason_code)

    def on_disconnect(_client, _userdata, reason_code, _properties=None):
        if reason_code != mqtt.MQTT_ERR_SUCCESS:
            logging.warning("Unexpected disconnect (%s); attempting reconnect.", reason_code)
        else:
            logging.info("Disconnected from MQTT broker.")

    def on_message(_client, userdata, message):
        topic_counter: TopicCounter = userdata["counter"]
        raw_subtopic = extract_subtopic(message.topic, topic_counter.base_topic)
        canonical_subtopic = canonicalize_subtopic(raw_subtopic)
        if canonical_subtopic is None:
            logging.debug("Skipping %s (untracked subtopic)", message.topic)
            return
        if "map" in canonical_subtopic.lower():
            logging.debug("Skipping %s (contains 'map')", message.topic)
            return
        new_total = topic_counter.increment(canonical_subtopic)
        if new_total is not None:
            label = canonical_subtopic or "<base>"
            logging.info("Count for %s is now %s", label, new_total)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    client.reconnect_delay_set(min_delay=1, max_delay=30)

    try:
        client.connect(args.broker_host, args.broker_port, keepalive=args.keepalive)
    except Exception as exc:
        logging.error("Failed to connect to MQTT broker: %s", exc)
        conn.close()
        raise SystemExit(1) from exc

    client.loop_start()

    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    finally:
        stop_event.set()
        client.loop_stop()
        client.disconnect()
        conn.close()
        logging.info("MQTT monitor stopped.")


if __name__ == "__main__":
    main()
