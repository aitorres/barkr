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
from barkr.connections import MastodonConnection

barkr = Barkr(
    [
        # Barkr will read new messages posted by this account, and queue them to
        # other accounts on write mode, but will not post anything to it.
        MastodonConnection(
            "Read only connection",
            [ConnectionModes.READ],
            "<ACCESS TOKEN HERE>",
            "<INSTANCE URL HERE>",
        ),
        # Barkr will write queued messages to this account, but will not read anything
        # new posted to this account or queue anything from this account to other ones
        MastodonConnection(
            "Write only connection",
            [ConnectionModes.WRITE],
            "<ACCESS TOKEN HERE>",
            "<INSTANCE URL HERE>",
        ),
        # Barkr will read new messages from this account to be queued onto others, and will
        # post new messages from other channels into this one as well.
        MastodonConnection(
            "R/W connection",
            [ConnectionModes.READ, ConnectionModes.WRITE],
            "<ACCESS TOKEN HERE>",
            "<INSTANCE URL HERE>",
        ),
    ]
)
barkr.start()
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. Contributions for issues that are already open by maintainers are welcome and encouraged.

Please make sure to update tests as appropriate; a minimum coverage of 80% is expected (and enforced by Github Actions!).

## License

This project is licensed under the [GNU Affero General Public License v3.0](./LICENSE).
