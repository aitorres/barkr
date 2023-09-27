"""
Module to implement unit tests for the Cohost connection class
"""

import pytest

from barkr.connections.base import ConnectionMode
from barkr.connections.cohost import CohostConnection


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

    cohost_at_sign = CohostConnection(
        "Cohost Connection",
        [ConnectionMode.READ, ConnectionMode.WRITE],
        "@testProject",
        cookie="test_cookie",
    )

    assert cohost_at_sign.project.handle == "testProject"

    with pytest.raises(ValueError, match="Project does not exist or is not writtable"):
        CohostConnection(
            "Cohost Connection",
            [ConnectionMode.READ, ConnectionMode.WRITE],
            "@NotTestProject",
            cookie="test_cookie",
        )
