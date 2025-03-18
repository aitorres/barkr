# Barkr

**Barkr**[^1] is a social media cross-posting tool written in Python: set it up and never worry about manually posting the same message to multiple channels ever again!

With **Barkr** you can setup a series of channels (e.g. social media accounts) to read messages from and / or post messages to. You can mix and match read / write modes, and add multiple accounts of the same type of channel as well without worrying that the same message will be re-posted to a channel it comes from.

Note that **Barkr** is limited to text posts only. Want to see that change? Start a discussion on a new issue!

[^1]: "Barkr" (missing "e") as in "entity that barks". See: [dogs](https://en.wikipedia.org/wiki/Dog).

## Motivation

I wrote **Barkr** for a personal use case after noting how much fragmentation there currently is (as of 2023) in the social media space, as a way to reduce the cost of engaging with multiple social media platforms, and also as a (very simple) way to practice using threads in Python.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install `barkr`.

```bash
pip install barkr
```

## Usage

Create a Python script and specify all the channels you want to use. Channel connections are present in the [`barkr.connections`](./barkr/connections/) module.

A simple script showcasing how to set up three Mastodon connections with multiple modes that can run in the background is outlined below:

```python
from barkr.main import Barkr

from barkr.connections import (
    ConnectionMode,
    BlueskyConnection,
    DiscordConnection,
    MastodonConnection,
    RSSConnection,
    TelegramConnection,
    TwitterConnection,
)

from barkr.models import Message

barkr = Barkr(
    [
        # Barkr will read new messages posted by this account, and queue them to
        # other accounts on write mode, but will not post anything to it.
        MastodonConnection(
            "Read only connection",
            [ConnectionMode.READ],
            "<ACCESS TOKEN HERE>",
            "<INSTANCE URL HERE>",
        ),
        # Barkr will write queued messages to this account, but will not read anything
        # new posted to this account or queue anything from this account to other ones.
        DiscordConnection(
            "Write only connection",
            [ConnectionMode.WRITE],
            "<BOT TOKEN ID HERE>",
            "<CHANNEL ID HERE>",
        ),
        # Barkr will read new messages from this account to be queued onto others, and will
        # post new messages from other channels into this one as well.
        BlueskyConnection(
            "R/W connection",
            [ConnectionMode.READ, ConnectionMode.WRITE],
            "<BLUESKY HANDLE HERE>",
            "<PASSWORD / APP PASSWORD HERE>",
        ),
        # Another example using Twitter -- note that the TwitterConnection only
        # supports write-only mode through the Twitter V2 API
        TwitterConnection(
            "Write only Twitter Connection",
            [ConnectionMode.WRITE],
            "<CONSUMER KEY HERE>",
            "<CONSUMER SECRET HERE>",
            "<ACCESS KEY HERE>",
            "<ACCESS SECRET HERE>",
            "<BEARER TOKEN HERE>",
        ),
        # One more, showcasing a Telegram write-only connection
        TelegramConnection(
            "Write only Telegram connection",
            [ConnectionMode.WRITE],
            "<TELEGRAM BOT TOKEN HERE>",
            "<TELEGRAM CHAT / CHANNEL ID HERE>",
        ),
        # You can also read from an RSS feed!
        RSSConnection(
            "Read only RSS connection",
            [ConnectionMode.READ],
            "<RSS FEED URL HERE>"
        ),
    ]
)

# Blocking: will start reading and writing threads to keep the connections in sync
barkr.start()

# Non-blocking, if you only need to write messages to your connections
barkr.write_message(
    Message(
        id="123456",
        message="Hello, world!",
    )
)
```

Always keep in mind proper secret management practices when using Barkr: instead of hardcoding access tokens / cookies / user and passwords, use tools like environment variables, `dotenv` or other secret managers!

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. Contributions for issues that are already open by maintainers are welcome and encouraged.

Please make sure to update tests as appropriate; a minimum coverage of 80% is expected (and enforced by Github Actions!).

## License

This project is licensed under the [GNU Affero General Public License v3.0](./LICENSE).
