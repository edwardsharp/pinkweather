"""
Severe weather alert display module
Handles display of severe weather alert icon overlay
"""

import displayio
from utils.logger import log


def create_alert_overlay(icon_loader, alerts_data):
    """Create severe weather alert icon overlay for display

    Args:
        icon_loader: Function to load icon bitmaps
        alerts_data: Alert data dict from weatherbit API

    Returns:
        DisplayIO group with alert icon, or None if no alerts
    """
    if not should_show_alert_icon(alerts_data):
        return None

    if not icon_loader:
        log("Alert overlay: No icon loader provided")
        return None

    try:
        # Load severe weather alert icon
        icon_sprite = icon_loader("severe-alert.bmp")
        if not icon_sprite:
            log("Alert overlay: Failed to load severe-alert.bmp")
            return None

        # Position in bottom right corner
        icon_x = 400 - 50
        icon_y = 300 - 50

        # Set position on the already-created TileGrid
        icon_sprite.x = icon_x
        icon_sprite.y = icon_y

        # Create group for the alert icon overlay
        alert_group = displayio.Group()
        alert_group.append(icon_sprite)

        alert_level = alerts_data.get("alert_level", "none")
        alert_count = alerts_data.get("alert_count", 0)
        log(
            f"Alert overlay: Showing {alert_level} alert icon ({alert_count} alerts) at ({icon_x}, {icon_y})"
        )

        return alert_group

    except Exception as e:
        log(f"Error creating alert overlay: {e}")
        return None


def should_show_alert_icon(alerts_data):
    """Determine if severe weather alert icon should be displayed

    Args:
        alerts_data: Alert data dict from weatherbit API

    Returns:
        bool: True if alert icon should be shown
    """
    if not alerts_data or not alerts_data.get("has_alerts", False):
        return False

    # Show icon only for warning level alerts
    alert_level = alerts_data.get("alert_level", "none")
    # for everyhing, do like:
    # return alert_level in ["advisory", "watch", "warning"]
    return alert_level == "warning"
