"""
Module containing unit tests for Barkr utility functions.
"""

from unittest.mock import MagicMock, patch

from barkr.utils import extract_urls_from_text, wrap_while_true


def test_extract_urls_from_text():
    """
    Test that URL extraction works as expected, and
    all URLs are properly extracted from text strings.
    """

    assert extract_urls_from_text("This is a URL: https://example.com") == [
        "https://example.com"
    ]
    assert extract_urls_from_text("Nothing here") == []
    assert extract_urls_from_text(
        "Multiple URLs! https://example.com and http://example.org"
    ) == [
        "https://example.com",
        "http://example.org",
    ]
    assert extract_urls_from_text("A link: https://example.com/path/to/resource") == [
        "https://example.com/path/to/resource"
    ]
    assert extract_urls_from_text(
        "A link: https://example.com/path/to/resource?query=param"
    ) == ["https://example.com/path/to/resource?query=param"]
    assert extract_urls_from_text(
        "https://example.org/index I can also have text on the other side"
    ) == ["https://example.org/index"]
    assert extract_urls_from_text("https://example.com/path/to/resource#fragment") == [
        "https://example.com/path/to/resource#fragment"
    ]


def test_wrap_while_true():
    """
    Unit test to check that the wrap_while_true function
    wrapper behaves as expected: runs the callback function
    and then sleeps.
    """

    mock_callback = MagicMock()
    sleep_interval = 2

    wrapped_function = wrap_while_true(mock_callback, sleep_interval)

    with patch("barkr.utils.sleep", side_effect=InterruptedError):
        try:
            wrapped_function()
        except InterruptedError:
            pass

    mock_callback.assert_called()
