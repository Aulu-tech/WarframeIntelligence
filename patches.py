"""Adds is_blacklisted() onto nextcord.User and nextcord.Member"""
import nextcord
import storage


def _is_blacklisted(self):
    return str(self.id) in storage.data["blacklist"]


def install():
    nextcord.User.is_blacklisted = _is_blacklisted
    nextcord.Member.is_blacklisted = _is_blacklisted
    nextcord.ClientUser.is_blacklisted = _is_blacklisted
