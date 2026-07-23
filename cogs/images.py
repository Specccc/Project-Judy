import time
from urllib.parse import urlparse

import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

from config import (
    COLOR_JUDY,
    IMAGE_CACHE_SECONDS,
    IMAGE_COMMAND_COOLDOWN_SECONDS,
    IMAGE_SEARCH_COUNTRY,
    IMAGE_SEARCH_LANGUAGE,
    IMAGE_SEARCH_MAX_RESULTS,
    SERPER_API_KEY,
)


SERPER_API_URL = (
    "https://google.serper.dev/images"
)

WIKIMEDIA_API_URL = (
    "https://commons.wikimedia.org/w/api.php"
)


def valid_url(value):
    if not isinstance(value, str):
        return False

    try:
        parsed = urlparse(value)

        return (
            parsed.scheme in {
                "http",
                "https"
            }
            and bool(parsed.netloc)
        )

    except ValueError:
        return False


def shorten(value, maximum):
    value = str(value)

    if len(value) <= maximum:
        return value

    return (
        value[:maximum - 3]
        + "..."
    )


class ImageBrowser(discord.ui.View):
    def __init__(
        self,
        requester_id,
        query,
        results,
        provider
    ):
        super().__init__(timeout=180)

        self.requester_id = requester_id
        self.query = query
        self.results = results
        self.provider = provider
        self.position = 0
        self.message = None

        self.update_buttons()

    def update_buttons(self):
        self.previous_button.disabled = (
            self.position == 0
        )

        self.next_button.disabled = (
            self.position
            >= len(self.results) - 1
        )

    def create_embed(self):
        result = self.results[
            self.position
        ]

        title = (
            result.get("title")
            or self.query
        )

        image_url = result[
            "image_url"
        ]

        source_page = result.get(
            "source_page"
        )

        source_name = (
            result.get("source_name")
            or self.provider
        )

        embed = discord.Embed(
            title=shorten(
                title,
                256
            ),
            description=(
                f"Search: "
                f"**{shorten(self.query, 200)}**\n"
                f"Result {self.position + 1} "
                f"of {len(self.results)}"
            ),
            color=COLOR_JUDY
        )

        if valid_url(source_page):
            embed.url = source_page

        embed.set_image(
            url=image_url
        )

        embed.set_footer(
            text=(
                f"Source: {source_name} "
                f"• {self.provider}"
            )
        )

        return embed

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):
        if (
            interaction.user.id
            != self.requester_id
        ):
            await interaction.response.send_message(
                "Run your own image search "
                "to control these results.",
                ephemeral=True
            )

            return False

        return True

    @discord.ui.button(
        label="Previous",
        style=discord.ButtonStyle.secondary
    )
    async def previous_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if self.position > 0:
            self.position -= 1

        self.update_buttons()

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )

    @discord.ui.button(
        label="Next",
        style=discord.ButtonStyle.primary
    )
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if (
            self.position
            < len(self.results) - 1
        ):
            self.position += 1

        self.update_buttons()

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(
                    view=self
                )

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                pass


class Images(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.cache = {}

    async def get_session(self):
        if (
            self.session is None
            or self.session.closed
        ):
            timeout = aiohttp.ClientTimeout(
                total=20
            )

            self.session = (
                aiohttp.ClientSession(
                    timeout=timeout,
                    headers={
                        "User-Agent": (
                            "Project-Judy/1.7"
                        )
                    }
                )
            )

        return self.session

    async def cog_unload(self):
        if (
            self.session is not None
            and not self.session.closed
        ):
            await self.session.close()

    def get_cached_results(
        self,
        query
    ):
        cache_key = (
            query.casefold().strip()
        )

        cached = self.cache.get(
            cache_key
        )

        if cached is None:
            return None

        saved_time, results, provider = (
            cached
        )

        age = (
            time.monotonic()
            - saved_time
        )

        if age > IMAGE_CACHE_SECONDS:
            del self.cache[cache_key]
            return None

        return results, provider

    def save_to_cache(
        self,
        query,
        results,
        provider
    ):
        cache_key = (
            query.casefold().strip()
        )

        self.cache[cache_key] = (
            time.monotonic(),
            results,
            provider
        )

    async def search_google_images(
        self,
        query
    ):
        if not SERPER_API_KEY:
            raise RuntimeError(
                "SERPER_API_KEY is missing."
            )

        session = await self.get_session()

        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": (
                "application/json"
            )
        }

        payload = {
            "q": query,
            "gl": IMAGE_SEARCH_COUNTRY,
            "hl": IMAGE_SEARCH_LANGUAGE,
            "num": (
                IMAGE_SEARCH_MAX_RESULTS
            ),
            "autocorrect": True
        }

        async with session.post(
            SERPER_API_URL,
            headers=headers,
            json=payload
        ) as response:
            if response.status == 429:
                raise RuntimeError(
                    "Image-search rate "
                    "limit reached."
                )

            if response.status in {
                401,
                403
            }:
                raise RuntimeError(
                    "SERPER_API_KEY "
                    "was rejected."
                )

            if response.status != 200:
                error_text = (
                    await response.text()
                )

                raise RuntimeError(
                    f"Image search returned "
                    f"HTTP {response.status}: "
                    f"{shorten(error_text, 300)}"
                )

            data = await response.json()

        raw_results = data.get(
            "images",
            []
        )

        results = []
        seen_urls = set()

        for item in raw_results:
            image_url = item.get(
                "imageUrl"
            )

            if not valid_url(image_url):
                image_url = item.get(
                    "thumbnailUrl"
                )

            if not valid_url(image_url):
                continue

            if image_url in seen_urls:
                continue

            if image_url.lower().endswith(
                ".svg"
            ):
                continue

            width = (
                item.get("imageWidth")
                or 0
            )

            height = (
                item.get("imageHeight")
                or 0
            )

            if width and height:
                if (
                    width < 300
                    or height < 300
                ):
                    continue

            results.append({
                "title": (
                    item.get("title")
                    or query
                ),
                "image_url": image_url,
                "source_page": item.get(
                    "link"
                ),
                "source_name": (
                    item.get("source")
                    or item.get("domain")
                    or "Web result"
                )
            })

            seen_urls.add(image_url)

            if (
                len(results)
                >= IMAGE_SEARCH_MAX_RESULTS
            ):
                break

        return results

    async def search_wikimedia(
        self,
        query
    ):
        session = await self.get_session()

        parameters = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": "6",
            "gsrlimit": str(
                IMAGE_SEARCH_MAX_RESULTS
            ),
            "prop": "imageinfo",
            "iiprop": "url|mime",
            "iiurlwidth": "1600",
            "origin": "*"
        }

        async with session.get(
            WIKIMEDIA_API_URL,
            params=parameters
        ) as response:
            if response.status != 200:
                return []

            data = await response.json()

        pages = (
            data
            .get("query", {})
            .get("pages", {})
            .values()
        )

        ordered_pages = sorted(
            pages,
            key=lambda page: page.get(
                "index",
                9999
            )
        )

        results = []

        for page in ordered_pages:
            image_information = page.get(
                "imageinfo",
                []
            )

            if not image_information:
                continue

            information = (
                image_information[0]
            )

            mime_type = information.get(
                "mime",
                ""
            )

            if mime_type not in {
                "image/jpeg",
                "image/png",
                "image/webp",
                "image/gif"
            }:
                continue

            image_url = (
                information.get("thumburl")
                or information.get("url")
            )

            if not valid_url(image_url):
                continue

            page_id = page.get(
                "pageid"
            )

            if page_id:
                source_page = (
                    "https://commons.wikimedia.org/"
                    f"?curid={page_id}"
                )

            else:
                source_page = (
                    "https://commons.wikimedia.org/"
                )

            title = page.get(
                "title",
                query
            )

            if title.startswith("File:"):
                title = title[5:]

            results.append({
                "title": title,
                "image_url": image_url,
                "source_page": source_page,
                "source_name": (
                    "Wikimedia Commons"
                )
            })

        return results

    async def find_images(
        self,
        query
    ):
        cached = self.get_cached_results(
            query
        )

        if cached is not None:
            return cached

        google_error = None

        try:
            results = (
                await self.search_google_images(
                    query
                )
            )

            if results:
                provider = (
                    "Google Images via Serper"
                )

                self.save_to_cache(
                    query,
                    results,
                    provider
                )

                return results, provider

        except Exception as error:
            google_error = error

            print(
                "[IMAGE SEARCH] "
                f"Google provider failed: "
                f"{error}"
            )

        try:
            results = (
                await self.search_wikimedia(
                    query
                )
            )

            if results:
                provider = (
                    "Wikimedia fallback"
                )

                self.save_to_cache(
                    query,
                    results,
                    provider
                )

                return results, provider

        except Exception as error:
            print(
                "[IMAGE SEARCH] "
                f"Wikimedia provider failed: "
                f"{error}"
            )

        if google_error is not None:
            raise google_error

        return [], "No provider"

    @app_commands.command(
        name="image",
        description="Search for relevant images from the web."
    )
    @app_commands.describe(
        query="What Judy should find an image of"
    )
    @app_commands.checks.cooldown(
        1,
        IMAGE_COMMAND_COOLDOWN_SECONDS,
        key=lambda interaction: (
            interaction.user.id
        )
    )
    async def image(
        self,
        interaction: discord.Interaction,
        query: str
    ):
        query = query.strip()

        if len(query) < 2:
            await interaction.response.send_message(
                "Give me something real "
                "to search for, choom.",
                ephemeral=True
            )
            return

        if len(query) > 200:
            await interaction.response.send_message(
                "Keep the search under "
                "200 characters.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            thinking=True
        )

        try:
            results, provider = (
                await self.find_images(
                    query
                )
            )

            if not results:
                await interaction.followup.send(
                    "Couldn't find a usable "
                    "image for that search."
                )
                return

            browser = ImageBrowser(
                interaction.user.id,
                query,
                results,
                provider
            )

            message = (
                await interaction.followup.send(
                    embed=browser.create_embed(),
                    view=browser,
                    wait=True
                )
            )

            browser.message = message

        except Exception as error:
            print(
                f"[IMAGE SEARCH ERROR] {error}"
            )

            await interaction.followup.send(
                "The image search failed. "
                "Check `/diagnostics`."
            )

    @image.error
    async def image_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        if isinstance(
            error,
            app_commands.CommandOnCooldown
        ):
            message = (
                "Image search is cooling down. "
                f"Try again in "
                f"{error.retry_after:.1f} seconds."
            )

        else:
            print(
                f"[IMAGE COMMAND ERROR] {error}"
            )

            message = (
                "The image command hit an "
                "unexpected error."
            )

        if interaction.response.is_done():
            await interaction.followup.send(
                message,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Images(bot))