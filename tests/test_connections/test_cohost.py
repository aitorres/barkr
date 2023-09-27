"""
Module to implement unit tests for the Cohost connection class
"""

from dataclasses import dataclass
from typing import Any

import pytest

from barkr.connections.base import ConnectionMode
from barkr.connections.cohost import CohostConnection
from barkr.models.message import Message


def test_cohost_connection_init() -> None:
    """
    Basic unit tests for the CohostConnection class
    init validations.
    """

    with pytest.raises(
        ValueError,
        match=(
            "No authentication method provided, please set either "
            "`cookie` OR `username` and `password`."
        ),
    ):
        CohostConnection(
            "CohostClass", [ConnectionMode.READ, ConnectionMode.WRITE], "test_project"
        )

    with pytest.raises(
        ValueError,
        match="Username provided but no password provided, please set `password`.",
    ):
        CohostConnection(
            "CohostClass",
            [ConnectionMode.READ, ConnectionMode.WRITE],
            "test_project",
            username="test_user",
        )


def test_cohost_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Basic unit tests for the CohostConnection class
    """

    monkeypatch.setattr(
        "barkr.connections.cohost.User.userInfo",
        lambda _: {
            "email": "test@example.org",
            "userId": "12345678",
            "modMode": False,
            "activated": True,
            "readOnly": False,
        },
    )

    monkeypatch.setattr(
        "cohost.models.user.fetchTrpc",
        lambda m, _: {
            "result": {
                "data": {
                    "projects": [{"projectId": "12345678", "handle": "testProject"}]
                }
            }
        }
        if m == "projects.listEditedProjects"
        else None,
    )

    monkeypatch.setattr(
        "cohost.models.project.Project.getPostsRaw",
        lambda *_args, **_kwargs: {
            "items": [{"postId": "12345678", "plainTextBody": "comment body"}]
        },
    )

    cohost = CohostConnection(
        "Cohost Connection",
        [ConnectionMode.READ, ConnectionMode.WRITE],
        "testProject",
        cookie="test_cookie",
    )

    assert cohost.name == "Cohost Connection"
    assert cohost.modes == [ConnectionMode.READ, ConnectionMode.WRITE]
    assert cohost.project.handle == "testProject"
    assert cohost.min_id == "12345678"

    # fetch
    monkeypatch.setattr(
        "cohost.models.project.Project.getPostsRaw",
        lambda *_args, **_kwargs: {
            "items": [
                {
                    "postId": "12345680",
                    "headline": None,
                    "plainTextBody": "comment body 3",
                },
                {
                    "postId": "12345679",
                    "headline": "Hey, Listen",
                    "plainTextBody": "comment body 2",
                },
                {
                    "postId": "12345678",
                    "headline": "",
                    "plainTextBody": "comment body 1",
                },
            ]
        },
    )
    messages = cohost.read()
    assert messages == [
        Message(id="12345680", message="comment body 3"),
        Message(id="12345679", message="Hey, Listen\ncomment body 2"),
    ]
    assert cohost.min_id == "12345680"

    monkeypatch.setattr(
        "cohost.models.project.Project.getPostsRaw",
        lambda *_args, **_kwargs: {"items": []},
    )
    messages = cohost.read()
    assert not messages
    assert cohost.min_id == "12345680"

    # post
    posted_messages: list[str] = []

    @dataclass
    class PostMockup(dict):
        """
        Mockup of the Cohost post response"""

        # pylint: disable=invalid-name
        postId: str

    def status_post_mockup(_, message: str) -> dict[str, Any]:
        posted_messages.append(message)

        return PostMockup("12121212" if message == "test message 3" else "23232323")

    monkeypatch.setattr(
        "barkr.connections.cohost.EditableProject.post", status_post_mockup
    )

    cohost.write(
        [
            Message(id="ForeignId1", message="test message 3"),
            Message(id="ForeignId2", message="test message 4"),
        ]
    )
    assert posted_messages == ["test message 3", "test message 4"]
    assert cohost.posted_message_ids == {"12121212", "23232323"}

    # misc init tests
    monkeypatch.setattr(
        "cohost.models.project.Project.getPostsRaw",
        lambda *_args, **_kwargs: {"items": []},
    )

    cohost_at_sign = CohostConnection(
        "Cohost Connection",
        [ConnectionMode.READ, ConnectionMode.WRITE],
        "@testProject",
        cookie="test_cookie",
    )

    assert cohost_at_sign.project.handle == "testProject"
    assert cohost_at_sign.min_id == ""

    with pytest.raises(ValueError, match="Project does not exist or is not writtable"):
        CohostConnection(
            "Cohost Connection",
            [ConnectionMode.READ, ConnectionMode.WRITE],
            "@NotTestProject",
            cookie="test_cookie",
        )
