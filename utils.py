
import os
import discord.ext
import asyncio


def create_db_urls(message):
  guildName = message.channel.guild.name
  channelName = message.channel.name

  guild_dir_url = r'./{0}/{1}'.format(os.getenv('DBDIR'),guildName)
  channel_dir_url = r'{0}/{1}'.format(guild_dir_url,channelName)
  gamedb_url = r"{0}/game.db".format(channel_dir_url)

  return (guild_dir_url, channel_dir_url, gamedb_url)

async def send_confirm_box(message, messageText, bot): 

  def check_user(reaction, user):
    return user == message.author

  def check(message, reaction, user):
    return user == message.author and str(reaction.emoji) == '👍'

  restart_msg = await message.channel.send(messageText)
  await restart_msg.add_reaction("👍")
  await restart_msg.add_reaction("👎")

  try:
      reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check_user)
      print("reaction received")
      await message.channel.send(reaction.emoji)
      if check(message,reaction,user):
        return True
  except asyncio.TimeoutError:
      await message.channel.send('Timeout: Assuming 👎')
      return False
  else:
      print("other else")

