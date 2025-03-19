"""
Module containing unit tests for Barkr utility functions.
"""

from barkr.utils import extract_urls_from_text


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
