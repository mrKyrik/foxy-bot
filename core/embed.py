from __future__ import annotations
"""
core/embed.py
-------------
Zengin Discord embed'leri oluşturmak için Builder pattern.

Tüm cog'lar bu sınıfı import eder; discord.Embed'i doğrudan kullanmak yerine
bu wrapper, tutarlı görünüm ve kolay timestamp/footer yönetimi sağlar.

Kullanım:
    from core.embed import EmbedBuilder
    embed = (
        EmbedBuilder(title="Başarılı", description="Kullanıcı banlandı.", color=discord.Color.green())
        .set_footer("Azalea Bot")
        .set_timestamp()
        .build()
    )
    await ctx.send(embed=embed)
"""

import datetime
import discord


class EmbedBuilder:
    """Zincirleme (fluent) API ile discord.Embed oluşturucu."""

    def __init__(
        self,
        title: str | None = None,
        description: str | None = None,
        color: discord.Color = discord.Color.blurple(),
    ) -> None:
        self.embed = discord.Embed(
            title=title,
            description=description,
            color=color,
        )

    # ------------------------------------------------------------------
    # Fluent setters
    # ------------------------------------------------------------------

    def set_author(
        self,
        name: str,
        icon_url: str | None = None,
        url: str | None = None,
    ) -> "EmbedBuilder":
        self.embed.set_author(name=name, icon_url=icon_url, url=url)
        return self

    def set_thumbnail(self, url: str) -> "EmbedBuilder":
        self.embed.set_thumbnail(url=url)
        return self

    def set_image(self, url: str) -> "EmbedBuilder":
        self.embed.set_image(url=url)
        return self

    def set_footer(
        self, text: str, icon_url: str | None = None
    ) -> "EmbedBuilder":
        self.embed.set_footer(text=text, icon_url=icon_url)
        return self

    def add_field(
        self, name: str, value: str, inline: bool = False
    ) -> "EmbedBuilder":
        self.embed.add_field(name=name, value=value, inline=inline)
        return self

    def set_timestamp(
        self, dt: datetime.datetime | None = None
    ) -> "EmbedBuilder":
        """
        Embed'e zaman damgası ekle.
        dt verilmezse şu anki UTC zamanı kullanılır.
        """
        self.embed.timestamp = dt or datetime.datetime.now(datetime.timezone.utc)
        return self

    def set_color(self, color: discord.Color) -> "EmbedBuilder":
        self.embed.color = color
        return self

    # ------------------------------------------------------------------
    # Terminal
    # ------------------------------------------------------------------

    def build(self) -> discord.Embed:
        """Tamamlanmış discord.Embed nesnesini döndür."""
        return self.embed
