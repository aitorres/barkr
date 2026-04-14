"""
Module to implement a custom connection class for webhooks,
supporting writing messages to external webhook URLs.

This module uses the requests library for outgoing POST requests.
"""

import logging
import uuid
from typing import Final, Optional

import requests

from barkr.connections.base import Connection, ConnectionMode
from barkr.models import Message, MessageType

logger = logging.getLogger()

DEFAULT_WRITE_KEY: Final[str] = "content"

REQUESTS_TIMEOUT: Final[int] = 30


class WebhookConnection(Connection):
    """
    Custom connection class for webhooks, supporting writing messages
    to an external webhook URL.

    Messages are sent as JSON POST requests to the configured endpoint.
    """

    supported_message_type: MessageType = MessageType.TEXT_ONLY

    webhook_endpoint: str
    payload_key: str
    auth_token: Optional[str]

    def __init__(  # pylint: disable=too-many-arguments too-many-positional-arguments
        self,
        name: str,
        modes: list[ConnectionMode],
        webhook_endpoint: str,
        payload_key: str = DEFAULT_WRITE_KEY,
        auth_token: Optional[str] = None,
    ) -> None:
        """
        Initialize the WebhookConnection with the specified configuration.

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param webhook_endpoint: The URL to send webhook payloads to
        :param payload_key: The JSON key to use for message content (default: "content")
        :param auth_token: Optional auth token sent in Authorization header
        :raises NotImplementedError: If modes other than WRITE are specified
        :raises ValueError: If required parameters are missing or invalid
        """
        super().__init__(name, modes)

        logger.info("Initializing Webhook (%s) connection", self.name)
        if self.modes != [ConnectionMode.WRITE]:
            raise NotImplementedError("WebhookConnection only supports write mode.")

        if not webhook_endpoint or not webhook_endpoint.strip():
            raise ValueError(
                f"WebhookConnection '{name}' requires a non-empty webhook endpoint."
            )

        webhook_endpoint = webhook_endpoint.strip()
        if not (
            webhook_endpoint.startswith("http://")
            or webhook_endpoint.startswith("https://")
        ):
            raise ValueError(
                f"WebhookConnection '{name}' requires a valid URL webhook endpoint URL."
            )

        if not payload_key or not payload_key.strip():
            logger.warning(
                "WebhookConnection (%s): empty payload key, defaulting to '%s'.",
                self.name,
                DEFAULT_WRITE_KEY,
            )
            payload_key = DEFAULT_WRITE_KEY

        self.webhook_endpoint = webhook_endpoint
        self.payload_key = payload_key.strip()
        self.auth_token = auth_token.strip() if auth_token else None

        logger.info(
            "Webhook (%s) connection initialized successfully",
            self.name,
        )

    def _post(self, messages: list[Message]) -> list[str]:
        """
        Post a list of messages to the configured webhook endpoint.

        Each message is sent as a separate POST request with a JSON body
        containing the message content under the configured `payload_key`.

        :param messages: A list of messages to post
        :return: A list of generated message IDs for successfully posted messages
        """
        posted_ids: list[str] = []

        for message in messages:
            payload = {self.payload_key: message.message}

            try:
                response = requests.post(
                    self.webhook_endpoint,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=REQUESTS_TIMEOUT,
                )
                response.raise_for_status()

                # Random GUID as a message ID
                posted_ids.append(str(uuid.uuid4()))

                logger.info(
                    "Posted message to Webhook (%s) endpoint: %s (status: %d)",
                    self.name,
                    self.webhook_endpoint,
                    response.status_code,
                )

            except requests.RequestException as e:
                logger.error(
                    "Failed to post message to Webhook (%s) endpoint %s: %s",
                    self.name,
                    self.webhook_endpoint,
                    str(e),
                )

        return posted_ids

    def _get_headers(self) -> dict[str, str]:
        """
        Helper method to construct headers for the webhook POST request,
        including the Authorization header if an auth token is configured.

        :return: A dictionary of HTTP headers
        """

        headers: dict[str, str] = {"Content-Type": "application/json"}

        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        return headers
