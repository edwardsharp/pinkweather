"""
Weatherbit.io API integration for severe weather alerts
"""

from utils.logger import log, log_error


def fetch_weatherbit_alerts(http_client, lat, lon, api_key):
    """Fetch severe weather alerts from Weatherbit.io API"""
    if not api_key or not lat or not lon:
        log("Weatherbit alerts: Missing required parameters")
        return None

    # Build API URL
    url = f"https://api.weatherbit.io/v2.0/alerts?lat={lat}&lon={lon}&key={api_key}"

    try:
        log("Fetching severe weather alerts from Weatherbit...")
        api_response = http_client.get(url)

        if not api_response:
            log("Weatherbit alerts: Empty response")
            return None

        return parse_weatherbit_alerts(api_response)

    except Exception as e:
        log_error(f"Weatherbit alerts API error: {e}")
        return None


def parse_weatherbit_alerts(api_response):
    """Parse Weatherbit alerts response into simplified format"""
    try:
        alerts = api_response.get("alerts", [])

        if not alerts:
            log("No severe weather alerts")
            return {"has_alerts": False, "alerts": []}

        # Process alerts and categorize by severity
        processed_alerts = []
        has_warning = False
        has_watch = False
        has_advisory = False

        for alert in alerts:
            severity = alert.get("severity", "").lower()
            title = alert.get("title", "")

            processed_alert = {
                "title": title,
                "severity": severity,
                "effective_local": alert.get("effective_local", ""),
                "expires_local": alert.get("expires_local", ""),
                "description": alert.get("description", "")[:200] + "..."
                if len(alert.get("description", "")) > 200
                else alert.get("description", ""),
            }

            processed_alerts.append(processed_alert)

            # Track severity levels
            if severity == "warning":
                has_warning = True
            elif severity == "watch":
                has_watch = True
            elif severity == "advisory":
                has_advisory = True

        # Determine overall alert level (highest severity)
        alert_level = "none"
        if has_warning:
            alert_level = "warning"
        elif has_watch:
            alert_level = "watch"
        elif has_advisory:
            alert_level = "advisory"

        log(
            f"Severe weather alerts found: {len(alerts)} alerts, highest severity: {alert_level}"
        )

        return {
            "has_alerts": True,
            "alert_level": alert_level,
            "alert_count": len(alerts),
            "alerts": processed_alerts,
        }

    except Exception as e:
        log_error(f"Error parsing Weatherbit alerts: {e}")
        return {"has_alerts": False, "alerts": []}


def should_show_alert_icon(alerts_data):
    """Determine if severe weather alert icon should be displayed"""
    if not alerts_data or not alerts_data.get("has_alerts", False):
        return False

    # Show icon only for warning level alerts
    alert_level = alerts_data.get("alert_level", "none")
    return alert_level == "warning"
