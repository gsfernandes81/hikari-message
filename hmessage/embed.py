from __future__ import annotations

import typing as t

import hikari as h
import yarl

from .constants import DEFAULT_COLOR, DESIGNATOR_PARAMETER_NAME


class MultiImageEmbedList(list):
    """A list of embeds with the same URL property and different image properties."""

    def __init__(
        self,
        *args,
        url: str,
        designator: int = None,
        images: list[str] = [],
        **kwargs,
    ):
        super().__init__()

        if kwargs.get("image"):
            raise ValueError(
                "Cannot set image property when using MultiImageEmbedList, "
                + "use images instead."
            )

        if not kwargs.get("description"):
            kwargs["description"] = ""

        if not kwargs.get("color") or kwargs.get("colour"):
            kwargs["color"] = DEFAULT_COLOR

        url: yarl.URL = yarl.URL(str(url))
        # Get the DESIGNATOR_PARAMETER from the url query
        # if it doesn't exist then use the designator parameter from the function
        # args.
        # if that doesn't exist then use the default value of 0
        designator = url.query.get(DESIGNATOR_PARAMETER_NAME, designator or 0)
        embed = h.Embed(
            *args,
            url=str(url % {DESIGNATOR_PARAMETER_NAME: designator}),
            **kwargs,
        )

        try:
            embed.set_image(images.pop(0))
        except IndexError:
            pass

        self.append(embed)

        for image in images:
            self.add_image(image)

    def add_image(self, image: str) -> "MultiImageEmbedList":
        """Add an image to the MultiImageEmbedList instance."""
        if self[-1].image:
            embed = h.Embed(
                url=self[0].url,
                description="",
                color=DEFAULT_COLOR,
            )
            embed.set_image(image)
            self.append(embed)
        else:
            self[-1].set_image(image)
        return self

    def add_images(self, images: list[str]) -> "MultiImageEmbedList":
        """Add multiple images to the MultiImageEmbedList instance."""
        for image in images:
            self.add_image(image)
        return self

    @classmethod
    def from_embed(
        cls,
        embed: h.Embed,
        designator=0,
        images: t.Optional[t.List[str]] = [],
        default_url: t.Union[str, yarl.URL, None] = None,
    ) -> "MultiImageEmbedList":
        # Create a MultiImageEmbed instance
        multi_image_embed: t.List[h.Embed] = cls(
            url=embed.url or default_url,
            designator=designator,
            description=embed.description,
            title=embed.title,
            color=embed.color or DEFAULT_COLOR,
            timestamp=embed.timestamp,
        )

        if multi_image_embed[0].url == None:
            raise ValueError(
                "If no default_url is provided then embeds must have a url."
            )

        if embed.image:
            multi_image_embed[0].set_image(embed.image.url)
        if embed.footer:
            multi_image_embed[0].set_footer(embed.footer.text, icon=embed.footer.icon)
        if embed.thumbnail:
            multi_image_embed[0].set_thumbnail(embed.thumbnail.url)
        if embed.author:
            multi_image_embed[0].set_author(
                name=embed.author.name, url=embed.author.url, icon=embed.author.icon
            )

        for field in embed.fields:
            multi_image_embed[0].add_field(
                field.name, field.value, inline=field.is_inline
            )

        # Loop through the image URLs and create and append new embeds with different image properties
        multi_image_embed.add_images(images)
        # Return the MultiImageEmbed instance
        return multi_image_embed
