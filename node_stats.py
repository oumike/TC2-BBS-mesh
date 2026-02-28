#!/usr/bin/env python3

"""
Node Statistics Viewer for TC²-BBS
Queries and displays node information stored in the database.
"""

import sqlite3
import sys
from datetime import datetime


def get_all_nodes():
    """Retrieve all nodes from the database."""
    conn = sqlite3.connect('nodes.db')
    c = conn.cursor()
    c.execute("SELECT * FROM nodes ORDER BY last_heard DESC")
    results = c.fetchall()
    columns = [description[0] for description in c.description]
    conn.close()
    
    if results:
        return [dict(zip(columns, row)) for row in results]
    return []


def get_node_by_id(node_id):
    """Retrieve a specific node by ID."""
    conn = sqlite3.connect('nodes.db')
    c = conn.cursor()
    c.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,))
    result = c.fetchone()
    columns = [description[0] for description in c.description]
    conn.close()
    
    if result:
        return dict(zip(columns, result))
    return None


def format_timestamp(ts):
    """Format a Unix timestamp to human-readable format."""
    if ts is None:
        return "Never"
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def display_node_summary(nodes):
    """Display a summary table of all nodes."""
    print(f"\n{'='*120}")
    print(f"NODE SUMMARY ({len(nodes)} nodes)")
    print(f"{'='*120}")
    print(f"{'Node ID':<15} {'Short':<10} {'Long Name':<25} {'HW Model':<15} {'Battery':<8} {'Last Heard':<20}")
    print(f"{'-'*120}")
    
    for node in nodes:
        node_id = node['node_id'] or 'Unknown'
        short = node['short_name'] or 'Unknown'
        long = node['long_name'] or 'Unknown'
        hw = node['hw_model'] or 'Unknown'
        battery = f"{node['battery_level']}%" if node['battery_level'] is not None else 'N/A'
        last_heard = format_timestamp(node['last_heard'])
        
        print(f"{node_id:<15} {short:<10} {long:<25} {hw:<15} {battery:<8} {last_heard:<20}")
    
    print(f"{'='*120}\n")


def display_node_details(node):
    """Display detailed information about a specific node."""
    if not node:
        print("Node not found.")
        return
    
    print(f"\n{'='*80}")
    print(f"NODE DETAILS: {node['node_id']}")
    print(f"{'='*80}")
    
    print(f"\n-- Identity --")
    print(f"Node ID:       {node['node_id']}")
    print(f"Numeric ID:    {node['num']}")
    print(f"Short Name:    {node['short_name']}")
    print(f"Long Name:     {node['long_name']}")
    print(f"Hardware:      {node['hw_model']}")
    print(f"Role:          {node['role']}")
    
    print(f"\n-- Power Metrics --")
    print(f"Battery:       {node['battery_level']}%" if node['battery_level'] is not None else "Battery:       N/A")
    print(f"Voltage:       {node['voltage']:.2f}V" if node['voltage'] is not None else "Voltage:       N/A")
    
    print(f"\n-- Network Metrics --")
    print(f"Channel Util:  {node['channel_utilization']:.1f}%" if node['channel_utilization'] is not None else "Channel Util:  N/A")
    print(f"Air Util TX:   {node['air_util_tx']:.1f}%" if node['air_util_tx'] is not None else "Air Util TX:   N/A")
    print(f"SNR:           {node['snr']:.1f} dB" if node['snr'] is not None else "SNR:           N/A")
    
    print(f"\n-- Environmental --")
    print(f"Temperature:   {node['temperature']:.1f}°C" if node['temperature'] is not None else "Temperature:   N/A")
    
    print(f"\n-- Location --")
    if node['latitude'] is not None and node['longitude'] is not None:
        print(f"Latitude:      {node['latitude']:.6f}")
        print(f"Longitude:     {node['longitude']:.6f}")
        print(f"Altitude:      {node['altitude']}m" if node['altitude'] is not None else "Altitude:      N/A")
    else:
        print("Location:      N/A")
    
    print(f"\n-- Timestamps --")
    print(f"First Seen:    {format_timestamp(node['first_seen'])}")
    print(f"Last Heard:    {format_timestamp(node['last_heard'])}")
    print(f"Last Updated:  {format_timestamp(node['last_updated'])}")
    
    print(f"\n{'='*80}\n")


def display_statistics(nodes):
    """Display statistics about the nodes."""
    if not nodes:
        print("No nodes in database.")
        return
    
    # Calculate statistics
    total = len(nodes)
    with_battery = [n for n in nodes if n['battery_level'] is not None]
    with_location = [n for n in nodes if n['latitude'] is not None and n['longitude'] is not None]
    with_temp = [n for n in nodes if n['temperature'] is not None]
    
    hw_models = {}
    for node in nodes:
        hw = node['hw_model'] or 'Unknown'
        hw_models[hw] = hw_models.get(hw, 0) + 1
    
    roles = {}
    for node in nodes:
        role = node['role'] or 'Unknown'
        roles[role] = roles.get(role, 0) + 1
    
    print(f"\n{'='*80}")
    print(f"DATABASE STATISTICS")
    print(f"{'='*80}")
    print(f"\nTotal Nodes:         {total}")
    print(f"With Battery Data:   {len(with_battery)} ({len(with_battery)/total*100:.1f}%)" if total > 0 else "With Battery Data:   0")
    print(f"With Location Data:  {len(with_location)} ({len(with_location)/total*100:.1f}%)" if total > 0 else "With Location Data:  0")
    print(f"With Temperature:    {len(with_temp)} ({len(with_temp)/total*100:.1f}%)" if total > 0 else "With Temperature:    0")
    
    if with_battery:
        avg_battery = sum(n['battery_level'] for n in with_battery) / len(with_battery)
        low_battery = [n for n in with_battery if n['battery_level'] < 20]
        print(f"Avg Battery Level:   {avg_battery:.1f}%")
        print(f"Low Battery (<20%):  {len(low_battery)}")
    
    print(f"\n-- Hardware Models --")
    for hw, count in sorted(hw_models.items(), key=lambda x: x[1], reverse=True):
        print(f"{hw:<20} {count:>3}")
    
    print(f"\n-- Node Roles --")
    for role, count in sorted(roles.items(), key=lambda x: x[1], reverse=True):
        print(f"{role:<20} {count:>3}")
    
    print(f"\n{'='*80}\n")


def main():
    """Main entry point for the node stats viewer."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'list':
            nodes = get_all_nodes()
            display_node_summary(nodes)
        
        elif command == 'stats':
            nodes = get_all_nodes()
            display_statistics(nodes)
        
        elif command == 'detail' and len(sys.argv) > 2:
            node_id = sys.argv[2]
            node = get_node_by_id(node_id)
            display_node_details(node)
        
        else:
            print("Unknown command or missing arguments.")
            print_usage()
    else:
        print_usage()


def print_usage():
    """Print usage information."""
    print("\nNode Statistics Viewer for TC²-BBS\n")
    print("Usage:")
    print("  python node_stats.py list              - List all nodes")
    print("  python node_stats.py stats             - Show database statistics")
    print("  python node_stats.py detail <node_id>  - Show detailed info for a specific node")
    print("\nExamples:")
    print("  python node_stats.py list")
    print("  python node_stats.py stats")
    print("  python node_stats.py detail !0137af2d")
    print()


if __name__ == "__main__":
    main()
