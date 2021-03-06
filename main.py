import discord
import discord.ext
from discord.ext import tasks, commands
import os
from os import path
import sqlite3
from sqlite3 import Error, IntegrityError
import json

from hex_map import create_requested_map_image, create_map
from utils import create_db_urls, send_confirm_box
from PIL import Image, ImageSequence

continue_ticking = False

query_dic = dict()

bot = commands.Bot(command_prefix=os.getenv("COMMAND_PREFIX"))

all_game_db_urls = []


#region message handling functions
def create_game_db(guild_dir_url, channel_dir_url, gamedb_url):

    conn = None
    c = None
    try:
        print("Creating game: " + gamedb_url)
        if not path.exists(guild_dir_url):
            os.mkdir(guild_dir_url)
        if not path.exists(channel_dir_url):
            os.mkdir(channel_dir_url)

        if path.exists(gamedb_url):
            os.remove(gamedb_url)

        conn = sqlite3.connect(gamedb_url)
        c = conn.cursor()
    except Error as e:
        print(e)

    sql_create_game_table = """ CREATE TABLE IF NOT EXISTS game (
                              lock INTEGER UNIQUE CHECK(lock=1) DEFAULT 1,
                              last_tick INTEGER
                              );"""

    c.execute(sql_create_game_table)

    sql_insert_initial_game_info = "INSERT INTO game (last_tick) VALUES (0);"
    c.execute(sql_insert_initial_game_info)
    conn.commit()

    sql_create_players_table = """ CREATE TABLE IF NOT EXISTS players (
                                      name TEXT PRIMARY KEY NOT NULL,
                                      cash REAL DEFAULT 0,
                                      debt REAL DEFAULT 0,
                                      carbon_amt REAL NOT NULL DEFAULT 0.0,
                                      aluminum_amt REAL NOT NULL DEFAULT 0.0,
                                      silicon_amt REAL NOT NULL DEFAULT 0.0,
                                      water_amt REAL NOT NULL DEFAULT 0.0
                                  ); """
    c.execute(sql_create_players_table)

    print("table created...")

    sql_create_map_table = """ CREATE TABLE IF NOT EXISTS tiles (
                                      tile_ind TEXT PRIMARY KEY NOT NULL,
                                      carbon_strength REAL,
                                      aluminum_strength REAL,
                                      iron_strength REAL,
                                      height_power REAL,
                                      silicon_strength REAL,
                                      uranium_strength REAL,
                                      water_strength REAL,
                                      oxygen_strength REAL
                                      terrain TEXT
                                  ); """
    c.execute(sql_create_map_table)
    create_map(20, 20, 20, conn, guild_dir_url, channel_dir_url, gamedb_url)

    sql_create_building_table = """ CREATE TABLE IF NOT EXISTS buildings (
                                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                                      type TEXT NOT NULL,
                                      tile_ind TEXT UNIQUE NOT NULL,
                                      owner REAL NOT NULL,
                                      FOREIGN KEY (type) REFERENCES building_info(type),
                                      FOREIGN KEY (tile_ind) REFERENCES tiles(tile_ind),
                                      FOREIGN KEY (owner) REFERENCES players(name)

                                  ); """
    c.execute(sql_create_building_table)

    sql_create_building_info_table = """ CREATE TABLE IF NOT EXISTS production_building_info (
                                      type TEXT PRIMARY KEY NOT NULL,
                                      category TEXT NOT NULL,
                                      carbon_gen REAL,
                                      aluminum_gen REAL,
                                      power_gen REAL,
                                      silicon_gen REAL,
                                      water_gen REAL,
                                      oxygen_gen REAL,
                                      required_terrain TEXT NOT NULL

                                  ); """
    c.execute(sql_create_building_info_table)

    sql_create_resource_table = """ CREATE TABLE IF NOT EXISTS resources (
                                      resource TEXT PRIMARY KEY NOT NULL,
                                      abbreviation TEXT NOT NULL,
                                      type TEXT NOT NULL,
                                      rate REAL NOT NULL DEFAULT 0.0,
                                      quantity REAL DEFAULT 0,
                                      price REAL NOT NULL DEFAULT 45

                                  ); """
    c.execute(sql_create_resource_table)

    info_file = open("production_info.json", "r")
    buildings = json.loads(info_file.read())
    print(buildings)

    cursor = conn.cursor()

    for b in buildings:
        carbon_gen = 0
        if "carbon_gen" in b:
            carbon_gen = b["carbon_gen"]

        power_gen = 0
        if "power_gen" in b:
            power_gen = b["power_gen"]

        alum_gen = 0
        if "aluminum_gen" in b:
            alum_gen = b["aluminum_gen"]

        silicon_gen = 0
        if "silicon_gen" in b:
            silicon_gen = b["silicon_gen"]

        water_gen = 0
        if "water_gen" in b:
            water_gen = b["water_gen"]

        oxygen_gen = 0
        if "oxygen_gen" in b:
            water_gen = b["oxygen_gen"]

        required_terrain = ""
        if "required_terrain" in b:
            required_terrain = b["required_terrain"]

        sql_add_building_info = """ INSERT INTO production_building_info
                                VALUES (?,?,?,?,?,?,?,?,?);"""
        cursor.execute(sql_add_building_info,(b['type'], b['category'], carbon_gen, alum_gen, power_gen,silicon_gen, water_gen, oxygen_gen, required_terrain))

    conn.commit()
    
    resource_file = open("resource_info.json", "r")
    resources = json.loads(resource_file.read())
    print(resources)
    
    for r in resources:
      rate = 0.0
      if "rate" in r:
        rate = r['rate']
      
      quantity = 0
      if "quantity" in r:
        quantity = r['quantity']
      
      price = 0
      if "price" in r:
        price = r['price']

      sql_add_resource_info = """ INSERT INTO resources
                                  VALUES(?,?,?,?,?,?);"""
      cursor.execute(sql_add_resource_info, (r['name'], r['abbreviation'], r['type'], rate, quantity, price))

    conn.commit()

@bot.command(name="makegame")
async def make_game_command(ctx, force=False):

    (guild_dir_url, channel_dir_url, gamedb_url) = create_db_urls(ctx)
    if path.exists(gamedb_url) and not force:
        result = await send_confirm_box(ctx, r'Game Exists. Restart?', bot)
        if not result:
            return

    create_game_db(guild_dir_url, channel_dir_url, gamedb_url)

    if not gamedb_url in all_game_db_urls:
        all_game_db_urls.append(gamedb_url)

    await ctx.channel.send("Map db created: " + gamedb_url)


@bot.command(name="joingame")
async def joingame_command(ctx):
    await make_user_command(ctx, ctx.author.name)


@bot.command(name="makeuser")
async def make_user_command(ctx, username):

    (guild_dir_url, channel_dir_url, gamedb_url) = create_db_urls(ctx)
    try:
        conn = sqlite3.connect(gamedb_url)
        insert_statement = """ INSERT INTO players (name)
                          VALUES (:name);"""
        c = conn.cursor()

        print("adding user: " + username)
        await ctx.channel.send("Added player: " + username)

        c.execute(insert_statement, {"name": username})
        conn.commit()
    except Error as e:
        print(e)
    except IntegrityError:
        print("error caguht")
        await ctx.channel.send(
            "User could not be added. Possible already exists in game: " +
            username)

    await players_command(ctx)


@bot.command("buildinginfo")
async def buildinginfo_command(ctx):

    (guild_dir_url, channel_dir_url, gamedb_url) = create_db_urls(ctx)
    try:
        conn = sqlite3.connect(gamedb_url)
        c = conn.cursor()

        sql_get_buildings = "SELECT * FROM production_building_info;"
        c.execute(sql_get_buildings)
        building_info = c.fetchall()

        await ctx.channel.send("type | category | carbon rate\n" +
                               str(building_info))
    except Error as e:
        print(e)


@bot.command(name="build")
async def build_command(ctx, b_type, hex_q, hex_r):

    (guild_dir_url, channel_dir_url, gamedb_url) = create_db_urls(ctx)
    try:
        conn = sqlite3.connect(gamedb_url)

        c = conn.cursor()

        sql_get_buildings = " SELECT type FROM production_building_info;"

        c.execute(sql_get_buildings)
        all_b_types = c.fetchall()

        sql_get_all_tiles = "SELECT tile_ind FROM tiles;"

        c.execute(sql_get_all_tiles)

        all_tiles = c.fetchall()
        hex_id = '{0},{1}'.format(hex_q, hex_r)

        all_b_types_flat = []
        for r in all_b_types:
            for s in r:
                all_b_types_flat.append(s)

        all_tiles_flat = []
        for r in all_tiles:
            for s in r:
                all_tiles_flat.append(s)

        print(all_tiles_flat)

        if hex_id in all_tiles_flat:
            if b_type in all_b_types_flat:
                sql_add_building = """ INSERT INTO buildings (type, owner, tile_ind)
                              VALUES (?,?,?)"""

                c.execute(sql_add_building, (b_type, ctx.author.name, hex_id))
                conn.commit()
                await ctx.channel.send(ctx.author.name + " built a " + b_type +
                                       " on tile " + hex_id)
            else:
                await ctx.channel.send("Building type does not exist: " +
                                       b_type)
        else:
            await ctx.channel.send("Tile coordinates do not exist")
    except IntegrityError:
        await ctx.channel.send("Building already exists on this tile")
    except Error as e:
        print(e)


@bot.command(name="buildings")
async def buildings_command(ctx):

    (guild_dir_url, channel_dir_url, gamedb_url) = create_db_urls(ctx)
    try:
        conn = sqlite3.connect(gamedb_url)
        c = conn.cursor()
        c.execute("SELECT * FROM buildings")
    except Error as e:
        print(e)

    await ctx.channel.send("id | type | owner | tile_ind\n" +
                           str(c.fetchall()))


@bot.command(name="skele")
async def skele_command(ctx):
  e = discord.Embed()
  file = discord.File("skele.gif")
  e.set_image(url="attachment://skele.gif")
  await ctx.channel.send(file=file, embed=e)


@bot.command(name="smallskele")
async def smallskele_command(ctx):
  size = 160, 120
  im = Image.open("skele.gif")
  frames = ImageSequence.Iterator(im)
  def thumbnails(frames):
    for frame in frames:
        thumbnail = frame.copy()
        thumbnail.thumbnail(size, Image.ANTIALIAS)
        yield thumbnail
  frames = thumbnails(frames)
  om = next(frames) # Handle first frame separately
  om.info = im.info # Copy sequence info
  om.save("out.gif", save_all=True, append_images=list(frames))
  e = discord.Embed()
  file = discord.File("out.gif")
  e.set_image(url="attachment://out.gif")
  await ctx.channel.send(file=file, embed=e)


@bot.command(name="try")
async def try_command(ctx):
  e = discord.Embed()
  file = discord.File("YodaDoOrDoNot.gif")
  e.set_image(url="attachment://YodaDoOrDoNot.gif")
  await ctx.channel.send(file=file, embed=e)

@bot.command(name="players")
async def players_command(ctx):

    (guild_dir_url, channel_dir_url, gamedb_url) = create_db_urls(ctx)
    try:
        conn = sqlite3.connect(gamedb_url)
    except Error as e:
        print(e)

    print("selecting users")
    select_statement = """ SELECT name FROM players;"""
    c = conn.cursor()
    c.execute(select_statement)
    rows = c.fetchall()

    row_str = 'players:'
    for row in rows:
        row_str = row_str + '\n\t' + row[0]

    await ctx.channel.send('`' + row_str + '`')

@bot.command(name="stockpile")
async def stockpile_command(ctx):
  print("thing")

#endregion


class TickCog(commands.Cog):
    def __init__(self):
        self.tick.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(seconds=int(os.getenv("TICK_TIME")))
    async def tick(self):
        print(all_game_db_urls)
        for db_url in all_game_db_urls:
            print("updating db: " + db_url)
            try:
                conn = sqlite3.connect(db_url)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                update_game_table(c)
                update_players_table(c, conn)
                conn.commit()
            except Error as e:
                print(e)


def update_game_table(cursor):
    sql_tick_update = """ UPDATE game SET last_tick = last_tick + 1;"""
    cursor.execute(sql_tick_update)


def update_players_table(cursor, conn):
    get_total_players = "SELECT name FROM players"
    cursor.execute(get_total_players)
    players_rows = cursor.fetchall()

    rate_dic = dict()
    for r in cursor.execute(
            "SELECT type, carbon_gen, power_gen, aluminum_gen, silicon_gen, water_gen FROM production_building_info;"
    ):
        rate_dic[r["type"]] = [
            r["carbon_gen"], r["power_gen"], r["aluminum_gen"],
            r["silicon_gen"], r["water_gen"]
        ]

    for r in players_rows:
        #get all of players buildings
        total_carbon_gen = total_alum_gen = total_power_gen = total_sil_gen = total_water_gen = 0
        new_carb_amut = new_alum_amt = new_sil_amt = new_water_amt = 0
        sql_get_buildings = "SELECT type, tile_ind FROM buildings WHERE owner=?;"

        for building_r in cursor.execute(sql_get_buildings,
                                         [r["name"]]).fetchall():
            for f in building_r:
                print(f)
            for tile_r in cursor.execute(
                    "SELECT carbon_strength,aluminum_strength,iron_strength,height_power,silicon_strength,uranium_strength,water_strength FROM tiles WHERE tile_ind=?;",
                [building_r["tile_ind"]]):

                gen_rates = rate_dic[building_r["type"]]
                #carbon update
                carbon_rate = gen_rates[0] * float(tile_r["carbon_strength"])
                total_carbon_gen += carbon_rate

                #aluminum update
                alum_rate = gen_rates[2] * float(tile_r["aluminum_strength"])
                total_alum_gen += alum_rate

                #silicon update
                sil_rate = gen_rates[3] * float(tile_r["silicon_strength"])
                total_sil_gen += sil_rate

                #water update
                water_rate = gen_rates[4] * float(tile_r["water_strength"])
                total_water_gen += water_rate
        

        #check for negative resources
        for player_row in cursor.execute("""SELECT carbon_amt, aluminum_amt,silicon_amt,water_amt FROM players"""):
          new_carb_amt = max(total_carbon_gen + player_row["carbon_amt"],0)
          print("new_carb_amt:{0}".format(new_carb_amt))
          new_alum_amt = max(total_alum_gen + player_row["aluminum_amt"],0)
          print("new_alum_amt:{0}".format(new_alum_amt))
          new_sil_amt = max(total_sil_gen + player_row["silicon_amt"],0)
          print("new_sil_amt:{0}".format(new_sil_amt))
          new_water_amt = max(total_water_gen + player_row["water_amt"],0)
          print("new_water_amt:{0}".format(new_water_amt))


        cursor.execute(
            """ UPDATE players SET carbon_amt=?, aluminum_amt=?, silicon_amt=?, water_amt=? WHERE name = ?;""",
            (new_carb_amt, new_alum_amt, new_sil_amt, new_water_amt,
             r["name"]))

        conn.commit()

        



@bot.command(name="map")
async def send_map(ctx):
    (guild_dir_url, channel_dir_url, gamedb_url) = create_db_urls(ctx)
    try:
        conn = sqlite3.connect(gamedb_url)
    except Error as e:
        print(e)

    player_map_url = await create_requested_map_image(conn, guild_dir_url,
                                                      channel_dir_url,
                                                      gamedb_url)

    file = discord.File(player_map_url)
    e = discord.Embed()
    e.set_image(url="attachment://" + player_map_url)
    await ctx.channel.send(file=file, embed=e)


for root, subFolders, files in os.walk("."):
    for filename in files:
        if filename == "game.db":
            full_name = path.join(root, filename)
            all_game_db_urls.append(full_name)
            print(full_name)

bot.add_cog(TickCog())
bot.run(os.getenv('TOKEN'))
