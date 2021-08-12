import random
import typing
from pathlib import Path
import difflib

import discord
from discord import emoji
from discord.colour import Color
from discord.embeds import Embed
from discord.emoji import Emoji
from discord.enums import ChannelType
from discord.message import Message
from fuzzywuzzy import process
from async_lru import alru_cache
from ICBOT.utils.meteo import weather_forecasts

from ICBOT.utils.ttl_hash import get_ttl_hash

from ..BotResponse import BotResponse
from ..channels import CHANNELS
from ..constants import Commands, Constants, ErrorMessages, Messages
from ..exceptions import InvalidArgument, NoArgument
from ..templates import EmebedWithFile, StandardMessage
from ..utils.data_loader import (
    ALL_FILES_DRIVE,
    ALL_SUBJECTS_DRIVE,
    DRIVE_PATH,
)
from ..utils.logging import logger


class Help(BotResponse):
    def to_message(self) -> discord.Embed:
        resp = StandardMessage("AIDE :", content="", show_doc=False)
        for command in Commands.ALL():
            resp.add_field(name=command.name, value=command.help_message)
        resp.add_field(
            name="Voir le code / Contribuer :", value=Messages.CONTRIBUTING_MESSAGE
        )
        return resp

    @staticmethod
    def _generate_help():
        return "\n".join([command.help_message for command in Commands.ALL()])


class Delegates(BotResponse):
    def to_message(self) -> None:
        return (
            StandardMessage("Délégués :", content=Messages.DELEGATES, show_doc=False)
            .add_field(name="IN", value=Messages.DELEGATES_IN)
            .add_field(name="SC", value=Messages.DELEGATES_SC)
        )


class Drive(BotResponse):
    def __init__(
        self, subject: str, files_names: typing.Iterable[typing.Tuple[str, int]]
    ) -> None:
        self.files_names = files_names
        self.subject = subject

    # TODO, drive features.
    def to_message(self) -> discord.Embed:
        temp_path = self.files_names[0].replace("\n", "")[2:]
        embed = StandardMessage(
            title="Drive :",
            content=f"Résultats pour {self.subject}: ```"
            + "\n".join([f"{c}" for c in self.files_names])
            + "```",
        )
        file_ = discord.File(Path.joinpath(DRIVE_PATH, temp_path), filename=temp_path)
        return EmebedWithFile(file_, embed)

    @classmethod
    async def build_with_args(
        cls: "Drive", args: typing.Iterable[str], original_message: discord.Message
    ) -> "BotResponse":
        if len(args) == 0:
            raise NoArgument(Commands.DRIVE.name)
        if len(args) < 2:
            raise InvalidArgument(ErrorMessages.DRIVE_NO_FILE_SPECIFIED)

        logger.info("Searching for " + " ".join(args))
        probable_subject = difflib.get_close_matches(
            args[0], ALL_SUBJECTS_DRIVE, cutoff=0.1
        )[0]
        probable_files = difflib.get_close_matches(
            "".join(args[1:]), ALL_FILES_DRIVE[probable_subject], cutoff=0.1
        )
        return cls(probable_subject, probable_files)


class RandomPanda(BotResponse):
    def __init__(self, emojis: typing.Iterable[Emoji]) -> None:
        self.emojis = emojis

    def to_message(self) -> discord.Embed:
        return " ".join([str(e) for e in self.emojis])

    @classmethod
    async def build_with_args(
        cls, args: typing.Iterable[str], message: discord.Message
    ) -> "BotResponse":
        amount_of_pandas = 1
        if len(args) > 0:
            try:
                amount_of_pandas = int(args[0])
            except ValueError:
                pass
        amount_of_pandas = min(max(1, amount_of_pandas), Constants.MAX_AMOUNT_PANDAS)
        pandas = list(
            filter(lambda e: e.name.startswith("panda"), message.guild.emojis)
        )
        pandas_resp = []
        for i in range(amount_of_pandas):
            pandas_resp.append(random.choice(pandas))
        return cls(pandas_resp)


class RandomCopiePate(BotResponse):
    def __init__(self, copiepate: str, submitter: str, link_to_message: str):
        self.copiepate = copiepate
        self.submitter = submitter
        self._link_to_message = link_to_message

    def to_message(self) -> discord.Embed:
        resp = f"**{self.copiepate}** \n\n_[Soumis]({self._link_to_message}) par_ <@{self.submitter}>"
        return StandardMessage(content=resp, show_doc=False)

    @classmethod
    async def build_with_args(
        cls, args: typing.Iterable[str], original_message: discord.Message
    ) -> "BotResponse":
        copie_pates = await RandomCopiePate._load_copiepates(get_ttl_hash(600))
        copie_pate = random.choice(copie_pates)
        return cls(copie_pate.clean_content, copie_pate.author.id, copie_pate.jump_url)

    @staticmethod
    @alru_cache(maxsize=1)
    async def _load_copiepates(ttl=None):
        return await CHANNELS["copie-pates"].history(limit=400).flatten()


class RandomMeme(BotResponse):
    def __init__(
        self, url_to_meme: str, author_mention: str, link_to_message: str
    ) -> None:
        super().__init__()
        self.url_to_meme = url_to_meme
        self.author = author_mention
        self.link_to_message = link_to_message

    def to_message(self) -> discord.Embed:
        content = f"[Soumis]({self.link_to_message}) par {self.author} "
        r = StandardMessage(title="MEME:", content=content, show_doc=False).set_image(
            url=self.url_to_meme
        )
        return r

    @classmethod
    async def build_with_args(
        cls, args: typing.Iterable[str], original_message: discord.Message
    ) -> "BotResponse":
        message = random.choice(await RandomMeme._load_memes(get_ttl_hash(600)))
        return cls(message.attachments[0].url, message.author.mention, message.jump_url)

    @staticmethod
    @alru_cache(maxsize=1)
    async def _load_memes(ttl_hash=None):
        return (
            await CHANNELS["memes"]
            .history(limit=400)
            .filter(
                lambda m: len(m.attachments) > 0
                and m.attachments[0].content_type.startswith("image")
            )
            .flatten()
        )


class Meteo(BotResponse):
    def to_message(self) -> discord.Embed:
        return StandardMessage(
            title="Météo à Lausanne :",
            content="\n".join(str(v) for v in weather_forecasts()[:12]),
            show_doc=False,
        )
        # return await super().build_with_args(args=args, original_message=original_message)
