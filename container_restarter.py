#!/usr/bin/env python3
"""
Container Restarter - Automatically restart a Docker container at a scheduled time via Portainer API
"""

import os
import time
import requests
import logging
from datetime import datetime, timedelta
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PortainerAPI:
    """Wrapper for Portainer API operations"""

    def __init__(self, url, api_key=None, username=None, password=None):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.username = username
        self.password = password
        self.jwt_token = None
        self.jwt_expiry = None

    def _get_headers(self):
        """Get authentication headers for API requests"""
        if self.api_key:
            return {'X-API-Key': self.api_key}

        # Use JWT authentication
        if not self.jwt_token or datetime.now() >= self.jwt_expiry:
            self._authenticate()

        return {'Authorization': f'Bearer {self.jwt_token}'}

    def _authenticate(self):
        """Authenticate and obtain JWT token"""
        if not self.username or not self.password:
            raise ValueError("Either API_KEY or USERNAME and PASSWORD must be provided")

        auth_url = f"{self.url}/api/auth"
        payload = {
            'username': self.username,
            'password': self.password
        }

        try:
            response = requests.post(auth_url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.jwt_token = data['jwt']
            # JWT token expires in 8 hours, refresh 30 minutes before
            self.jwt_expiry = datetime.now() + timedelta(hours=7, minutes=30)
            logger.info("Successfully authenticated with Portainer")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def get_container_id(self, endpoint_id, container_name):
        """Get container ID from container name"""
        url = f"{self.url}/api/endpoints/{endpoint_id}/docker/containers/json?all=1"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            containers = response.json()

            for container in containers:
                # Container names start with '/', so we check both formats
                names = container.get('Names', [])
                if f'/{container_name}' in names or container_name in names:
                    return container['Id']
                # Also check if the provided name is already an ID
                if container['Id'].startswith(container_name):
                    return container['Id']

            raise ValueError(f"Container '{container_name}' not found")
        except Exception as e:
            logger.error(f"Failed to get container ID: {e}")
            raise

    def restart_container(self, endpoint_id, container_id):
        """Restart a container"""
        url = f"{self.url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}/restart"
        headers = self._get_headers()

        try:
            response = requests.post(url, headers=headers, timeout=30)
            response.raise_for_status()
            logger.info(f"Successfully restarted container {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to restart container: {e}")
            raise


class ContainerRestarter:
    """Scheduler for container restarts"""

    def __init__(self):
        self.portainer_url = os.getenv('PORTAINER_URL')
        self.api_key = os.getenv('PORTAINER_API_KEY')
        self.username = os.getenv('PORTAINER_USERNAME')
        self.password = os.getenv('PORTAINER_PASSWORD')
        self.endpoint_id = os.getenv('ENDPOINT_ID', '1')
        self.container_name = os.getenv('CONTAINER_NAME')
        self.restart_time = os.getenv('RESTART_TIME', '03:00')
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '60'))  # seconds

        self._validate_config()

        self.api = PortainerAPI(
            url=self.portainer_url,
            api_key=self.api_key,
            username=self.username,
            password=self.password
        )

        self.container_id = None
        self.last_restart_date = None

    def _validate_config(self):
        """Validate required environment variables"""
        if not self.portainer_url:
            raise ValueError("PORTAINER_URL environment variable is required")

        if not self.api_key and not (self.username and self.password):
            raise ValueError(
                "Either PORTAINER_API_KEY or both PORTAINER_USERNAME "
                "and PORTAINER_PASSWORD must be provided"
            )

        if not self.container_name:
            raise ValueError("CONTAINER_NAME environment variable is required")

        # Validate time format
        try:
            datetime.strptime(self.restart_time, '%H:%M')
        except ValueError:
            raise ValueError(
                f"RESTART_TIME must be in HH:MM format (24-hour), got: {self.restart_time}"
            )

    def _should_restart(self):
        """Check if it's time to restart the container"""
        now = datetime.now()
        target_time = datetime.strptime(self.restart_time, '%H:%M').time()
        current_time = now.time()
        current_date = now.date()

        # Check if we're within the time window and haven't restarted today
        time_match = (
            current_time.hour == target_time.hour and
            current_time.minute == target_time.minute
        )

        not_restarted_today = self.last_restart_date != current_date

        return time_match and not_restarted_today

    def run(self):
        """Main loop to check and restart container"""
        logger.info("Container Restarter starting...")
        logger.info(f"Portainer URL: {self.portainer_url}")
        logger.info(f"Endpoint ID: {self.endpoint_id}")
        logger.info(f"Container: {self.container_name}")
        logger.info(f"Scheduled restart time: {self.restart_time}")
        logger.info(f"Check interval: {self.check_interval} seconds")

        # Get container ID once at startup
        try:
            self.container_id = self.api.get_container_id(
                self.endpoint_id,
                self.container_name
            )
            logger.info(f"Found container ID: {self.container_id[:12]}...")
        except Exception as e:
            logger.error(f"Failed to find container at startup: {e}")
            logger.info("Will retry on each check...")

        while True:
            try:
                # Resolve container ID if not already done
                if not self.container_id:
                    self.container_id = self.api.get_container_id(
                        self.endpoint_id,
                        self.container_name
                    )
                    logger.info(f"Resolved container ID: {self.container_id[:12]}...")

                if self._should_restart():
                    logger.info(f"Time to restart container {self.container_name}")
                    self.api.restart_container(self.endpoint_id, self.container_id)
                    self.last_restart_date = datetime.now().date()
                    logger.info(f"Next restart scheduled for {self.restart_time} tomorrow")
                else:
                    next_run = datetime.strptime(self.restart_time, '%H:%M').time()
                    logger.debug(f"Next restart at {next_run}, currently {datetime.now().strftime('%H:%M')}")

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                # Reset container_id to retry resolution
                self.container_id = None

            time.sleep(self.check_interval)


def main():
    """Entry point"""
    try:
        restarter = ContainerRestarter()
        restarter.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
