import discord
from datetime import datetime

from config import (
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_ERROR,
    COLOR_INFO
)


def build_success(title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=description,
        color=COLOR_SUCCESS,
        timestamp=datetime.utcnow()
    )
    return embed


def build_warning(title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=description,
        color=COLOR_WARNING,
        timestamp=datetime.utcnow()
    )
    return embed


def build_error(title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=description,
        color=COLOR_ERROR,
        timestamp=datetime.utcnow()
    )
    return embed


def build_info(title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=description,
        color=COLOR_INFO,
        timestamp=datetime.utcnow()
    )
    return embed
