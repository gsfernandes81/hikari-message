from __future__ import annotations

import logging
import typing as t

import attr
import hikari as h

from .constants import DEFAULT_COLOR
from .embed import MultiImageEmbedList


class HMessageEmbed(h.Embed):
    def __eq__(self, other: t.Any) -> bool:
        if not isinstance(other, type(self)):
            if isinstance(other, h.Embed):
                other = type(self).from_embed(other)
            else:
                return False

        for attrsib in self.__slots__:
            # Image equality override
            if attrsib == "_image":
                if str(getattr(self, attrsib).url) != str(getattr(other, attrsib).url):
                    break
            elif getattr(self, attrsib) != getattr(other, attrsib):
                break
        else:
            return True
        return False

    @classmethod
    def from_embed(cls, embed: h.Embed):
        return cls.from_received_embed(
            title=embed._title,
            description=embed._description,
            url=embed._url,
            color=embed._color,
            timestamp=embed._timestamp,
            image=embed._image,
            thumbnail=embed._thumbnail,
            video=embed._video,
            author=embed._author,
            provider=embed._provider,
            footer=embed._footer,
            fields=embed._fields,
        )


@attr.s
class HMessage:
    """A prototype for a message to be sent to a channel."""

    content: str = attr.ib(default="", converter=str)
    embeds: t.List[h.Embed] = attr.ib(default=attr.Factory(list))
    embed_default_colour: h.Color = attr.ib(
        default=DEFAULT_COLOR, converter=h.Color, eq=False
    )
    attachments: t.List[h.Attachment] = attr.ib(default=attr.Factory(list))
    id: t.Optional[int] = attr.ib(default=0, converter=int, eq=False)

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
            embeds=[HMessageEmbed.from_embed(embed) for embed in message.embeds],
            attachments=[att.url for att in message.attachments],
            id=message.id,
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

        if self.content.endswith("\n") or other.content.startswith("\n"):
            use_endline = False
        else:
            use_endline = True

        return self.__class__(
            content=(self.content + ("\n" if use_endline else "") + other.content),
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
        self.merge_url_as_image_into_embed(
            self.embeds[embed_no].url, embed_no, designator
        )
        self.embeds[embed_no].url = None
        return self

    def merge_url_as_image_into_embed(
        self, url: str, embed_no: int = 0, designator: int = 0
    ):
        if url is None:
            logging.warning("Cannot merge NoneType URL into embed")
            return

        if not self.embeds:
            self.embeds = [h.Embed(color=DEFAULT_COLOR)]

        embed_no = int(embed_no) % len(self.embeds)

        embed = self.embeds.pop(embed_no)
        embeds = MultiImageEmbedList.from_embed(
            embed,
            designator,
            [url],
        )

        for embed in embeds[::-1]:
            self.embeds.insert(embed_no, embed)

        return self

    def remove_all_embed_thumbnails(self):
        for embed in self.embeds:
            embed.set_thumbnail(None)
        return self

    def merge_attachements_into_embed(
        self,
        embed_no: int = -1,
        designator: int = 0,
        new_embed: bool = False,
        default_url: str = None,
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

        attachments_to_embeds_list = []
        attachments_remaining_list = []
        for attachment in self.attachments:
            if hasattr(attachment, "media_type") and str(
                attachment.media_type
            ).startswith("image"):
                attachments_to_embeds_list.append(attachment.url)
            else:
                attachments_remaining_list.append(attachment)

        embeds = MultiImageEmbedList.from_embed(
            self.embeds.pop(embed_no),
            designator,
            attachments_to_embeds_list,
            default_url=default_url,
        )

        for embed in embeds[::-1]:
            self.embeds.insert(embed_no, embed)

        self.attachments = attachments_remaining_list

        return self
