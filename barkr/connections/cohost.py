"""
Module to implement a custom connection class for Cohost accounts,
supporting reading and writing messages from any of the user's projects.

Please read https://github.com/valknight/Cohost.py#readme for more information
regarding authenticating with cookies and / or user and password combinations.
"""

import logging
from typing import Optional

from cohost.models.post import Post  # type: ignore

# NOTE(2023-09-26): keep an eye on https://github.com/valknight/Cohost.py/pull/33
from cohost.models.project import EditableProject  # type: ignore
from cohost.models.user import User  # type: ignore

from barkr.connections.base import Connection, ConnectionMode
from barkr.models.message import Message

logger = logging.getLogger()


class CohostConnection(Connection):
    """
    Custom connection class for Cohost accounts,
    supporting reading and writing messages from any of the user's projects.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        name: str,
        modes: list[ConnectionMode],
        project: str,
        cookie: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        """
        Initializes the connection with a name and a list of modes,
        as well as setting up access to the user's account.

        Validates the user's credentials by connecting to Cohost and verifying that
        the provided project exists.

        Attempts to connect by cookie first, then by user and password combination
        if cookie is not provided.

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param project: The name of the project to connect to
        :param cookie: The cookie for the authenticated user
        :param username: The username of the authenticated user
        :param password: The password of the authenticated user
        """

        super().__init__(name, modes)

        if username is not None and password is None:
            raise ValueError(
                "Username provided but no password provided, please set `password`."
            )

        logger.debug(
            "Initializing Cohost (%s) connection to project %s",
            self.name,
            project,
        )

        if cookie is not None:
            user: User = User.loginWithCookie(cookie)
        elif username is not None and password is not None:
            user = User.login(username, password)
        else:
            raise ValueError(
                "No authentication method provided, please set either "
                "`cookie` OR `username` and `password`."
            )

        if project.startswith("@"):
            project = project[1:]

        if project not in [p.handle for p in user.editedProjects]:
            raise ValueError(
                "Project does not exist or is not writtable, please check "
                "your spelling and try again."
            )

        project_instance = user.getProject(project)
        assert project_instance is not None

        self.project: EditableProject = project_instance

        logger.info(
            "Cohost (%s) connection initialized! (Project handle: %s)",
            self.name,
            self.project.handle,
        )

        posts: list[Post] = self.project.getPosts()

        if posts:
            self.min_id = posts[0].postId
            logger.debug("Cohost (%s) initial min_id: %s", self.name, self.min_id)
        else:
            self.min_id = ""
            logger.debug("Cohost (%s) initial min_id not set.", self.name)

    def _fetch(self) -> list[Message]:
        """
        Fetch messages from this connection

        :return: A list of messages
        """

        posts: list[Post] = [
            post for post in self.project.getPosts() if post.postId > self.min_id
        ]

        if posts:
            logger.info("Fetched %s new posts from Cohost (%s)", len(posts), self.name)
            self.min_id = posts[0].postId
        else:
            logger.debug("No new posts fetched from Cohost (%s)", self.name)

        return [
            Message(
                id=post.postId,
                message=f"{post.headline}\n{post.plainTextBody}"
                if post.headline
                else post.plainTextBody,
            )
            for post in posts
        ]

    def _post(self, messages: list[Message]) -> list[str]:
        """
        Post messages from a list to this Cohost project

        :param messages: A list of messages to be posted
        """

        posted_message_ids = []

        for message in messages:
            new_post: Post = self.project.post(message.message)
            posted_message_ids.append(new_post.postId)
            logger.info("Cohost (%s) posted message: %s", self.name, message)

        return posted_message_ids
