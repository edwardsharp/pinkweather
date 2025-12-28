"""
HTTP client for weather API requests on CircuitPython hardware
"""


class HTTPClient:
    """HTTP client using CircuitPython adafruit_requests"""

    def __init__(self):
        import ssl

        import adafruit_requests
        import socketpool
        import wifi

        pool = socketpool.SocketPool(wifi.radio)
        self.session = adafruit_requests.Session(pool, ssl.create_default_context())

    def get(self, url):
        """Make GET request and return JSON response"""
        response = self.session.get(url)
        json_data = response.json()
        response.close()
        return json_data
