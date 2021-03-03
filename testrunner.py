#import pytest
import main
#from main import creat_game_db
from os import path

def test_make_game():
  guild_dir_url = "testguild"
  channel_dir_url = guild_dir_url + "/guild_dir_url"
  gamedb_url = channel_dir_url + "/testgame.db"
  create_game_db(guild_dir_url, channel_dir_url, gamedb_url, gamedb_url)

  #assert path.exists(gamedb_url)