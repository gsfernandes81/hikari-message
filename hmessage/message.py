from __future__ import annotations

import typing as t

import attr
import hikari as h

from .constants import DEFAULT_COLOR
from .embed import MultiImageEmbedList


@attr.s
class HMessage:
    """A prototype for a message to be sent to a channel."""

    content: str = attr.ib(default="", converter=str)
    embeds: t.List[h.Embed] = attr.ib(default=attr.Factory(list))
    embed_default_colour: h.Color = attr.ib(default=DEFAULT_COLOR, converter=h.Color)
    attachments: t.List[h.Attachment] = attr.ib(default=attr.Factory(list))

    @content.validator
    def _validate_content(self, attribute, value):
        if len(value) > 2000:
            raise ValueError(
                "Cannot send more than 2000 characters in a single message"
            )

    @embeds.validator
    def _validate_embeds(self, attribute, value):
        if len(value) > 10:
            raise ValueError("Cannot send more than 10 embeds in a single message")

    @attachments.validator
    def _validate_attachments(self, attribute, value):
        if len(value) > 10:
            raise ValueError("Cannot send more than 10 attachments in a single message")

    @classmethod
    def from_message(cls, message: h.Message) -> "HMessage":
        """Create a MessagePrototype instance from a message."""
        return cls(
            content=message.content or "",
            embeds=message.embeds,
            attachments=message.attachments,
        )

    def to_message_kwargs(self) -> t.Dict[str, t.Any]:
        """Convert the MessagePrototype instance into a dict of kwargs to be passed to
        `hikari.Messageable.send`."""
        return {
            "content": self.content,
            "embeds": self.embeds,
            "attachments": self.attachments,
        }

    def __add__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"Cannot add MessagePrototype to {other.__class__.__name__}"
            )

        return self.__class__(
            content=self.content + other.content,
            embeds=self.embeds + other.embeds,
            attachments=self.attachments + other.attachments,
        )

    def merge_content_into_embed(
        self, embed_no: int = 0, prepend: bool = True
    ) -> "HMessage":
        """Merge the content of a message into the description of an embed.

        Args:
            embed_no (int, optional): The index of the embed to merge the content into.
            prepend (bool, optional): Whether to prepend the content to the embed description.
                If False, the content will be appended to the embed description. Defaults to True.
        """
        content = str(self.content or "")
        self.content = ""

        if not self.embeds:
            self.embeds = [h.Embed(description=content, color=DEFAULT_COLOR)]
            return self

        embed_no = int(embed_no) % (len(self.embeds) or 1)

        if not isinstance(self.embeds[embed_no].description, str):
            self.embeds[embed_no].description = ""

        if prepend:
            self.embeds[embed_no].description = (
                content + "\n\n" + self.embeds[embed_no].description
            )
        else:
            self.embeds[embed_no].description = (
                self.embeds[embed_no].description + "\n\n" + content
            )

        return self

    def merge_embed_url_as_embed_image_into_embed(
        self, embed_no: int = 0, designator: int = 0
    ) -> "HMessage":
        if not self.embeds:
            self.embeds = [h.Embed(color=DEFAULT_COLOR)]

        embed_no = int(embed_no) % len(self.embeds)

        embed = self.embeds.pop(embed_no)
        embeds = MultiImageEmbedList.from_embed(
            embed,
            designator,
            [embed.url],
        )
        embeds[0].set_thumbnail(None)

        for embed in embeds[::-1]:
            self.embeds.insert(embed_no, embed)

        return self

    def merge_attachements_into_embed(
        self,
        embed_no: int = -1,
        designator: int = 0,
        new_embed: bool = False,
    ) -> "HMessage":
        """Merge the attachments of a message into the embed.

        Args:
            embed_no (int, optional): The index of the embed to merge the attachments into.
            designator (int, optional): The designator to use for the embed. Defaults to 0.
            new_embed (bool, optional): Whether to create a new embed for the attachments.
                                        sets embed_no to the last embed. Defaults to False.
        """
        if not self.embeds:
            self.embeds = [h.Embed(color=DEFAULT_COLOR)]

        if new_embed:
            embed_no = len(self.embeds)
            self.embeds.append(h.Embed(color=DEFAULT_COLOR, description="."))

        embed_no = int(embed_no) % len(self.embeds)

        embeds = MultiImageEmbedList.from_embed(
            self.embeds.pop(embed_no),
            designator,
            [
                attachment.url
                for attachment in self.attachments
                if str(attachment.media_type).startswith("image")
            ],
        )

        for embed in embeds[::-1]:
            self.embeds.insert(embed_no, embed)

        self.attachments = [
            attachment
            for attachment in self.attachments
            if not str(attachment.media_type).startswith("image")
        ]

        return self
