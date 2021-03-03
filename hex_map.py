import math
import discord
import discord.ext
import os
from os import path
from sqlite3 import Error
import sqlite3
from utils import create_db_urls

from PIL import Image, ImageDraw, ImageFont

hex_size = 60
map_image_size = 5000

def tile_index_to_list_xy_qr(tileIndex, image_height, image_width):
  split_str = tileIndex.split(',')
  q = split_str[0]
  r = split_str[1]
  x,y = hex_to_pixel(int(q), int(r), hex_size, image_height, image_width)
  return ((x,y),(q,r))

def tile_index_to_list_xy(tileIndex, image_height, image_width):
  split_str = tileIndex.split(',')
  x,y = hex_to_pixel(int(split_str[0]), int(split_str[1]), hex_size, image_height, image_width)
  return (x,y)

def tile_index_to_list_qr(tileIndex):
  split_str = tileIndex.split(',')
  return (split_str[0],split_str[1])

def cube_to_axial(x, y, z):
  return (x,y)

def corner_coord(x, y, size, i):
  angle = math.radians(60 * i - 30)
  return ( (x + size * math.cos(angle)), (y + size * math.sin(angle)) )
  
def hex_to_pixel(q,r,size,image_width,image_height):
  x = size * (math.sqrt(3) * q + math.sqrt(3)/2 * r)
  y = size * (3./2 * r)
  return (x + image_width/2, y + image_width/2)


async def create_requested_map_image(conn, guild_dir_url, channel_dir_url, gamedb_url):
  
  if not conn:
    try:
      conn = sqlite3.connect(gamedb_url)
    except Error as e:
      print(e)
  if not path.exists(guild_dir_url):
    os.mkdir(guild_dir_url)
  if not path.exists(channel_dir_url):
    os.mkdir(channel_dir_url)

  select_statement = """ SELECT tile_ind FROM tiles;"""
  c = conn.cursor()
  c.execute(select_statement)
  rows = c.fetchall()
  coord = []

  for row in rows:
    coord.append(tile_index_to_list_xy_qr(row[0],map_image_size,map_image_size))

  map_url = channel_dir_url + "/game_map.jpg"
  image = Image.open(map_url)

  hq_icon = Image.open("hq_icon.jpg")
  for cur_coord in coord:
    center = cur_coord[0]
    image.paste(hq_icon,(int(center[0] - hq_icon.width/2),int(center[1])))

  
  player_map_url = channel_dir_url + "/player_map.jpg"
  image.save(player_map_url, quality=40)

  print("done saving")

  return player_map_url


def create_map(maxX, maxY, maxZ, conn, guild_dir_url, channel_dir_url, gamedb_url):

  if not conn:
    try:
      conn = sqlite3.connect(gamedb_url)
    except Error as e:
      print(e)

  if not path.exists(guild_dir_url):
    os.mkdir(guild_dir_url)
  if not path.exists(channel_dir_url):
    os.mkdir(channel_dir_url)

  c = conn.cursor()
  for x in range(-maxX,maxX+1):
      for y in range(-maxY,maxY+1):
        z = -(x + y)
        if z <= maxZ and z >= -maxZ:
          print("{0},{1}".format(x,z))
          insert_statement = r""" INSERT INTO tiles 
                            VALUES ('{0},{1}',4,0,0,0,0,0,4,"");""".format(x,z)
        
          c.execute(insert_statement)

  conn.commit()

  select_statement = """ SELECT tile_ind FROM tiles;"""
  c = conn.cursor()
  c.execute(select_statement)
  rows = c.fetchall()
  coord = []

  for row in rows:
    coord.append(tile_index_to_list_xy_qr(row[0],map_image_size,map_image_size))

  image = Image.new("RGB",(map_image_size,map_image_size),color="white")
  draw = ImageDraw.Draw(image)

  print("tile coord:" + str(coord))

  text_font = ImageFont.truetype("DejaVuSans.ttf", 12)
  print(text_font.getname()[0])
  print("drawing image")

  for cur_coord in coord:
    corner_xys = []
    center = cur_coord[0]
    qr = cur_coord[1]
    for i in range(0,6):
      corner_xys.append(corner_coord(center[0],center[1],hex_size,i))
    corner_xys.append(corner_xys[0])
    draw.line(corner_xys,fill=0,width=5)
    draw.text((center[0],center[1]-10),"{0},{1}".format(qr[0],qr[1]),(0,0,0),
    font=text_font,anchor="ms")

  print("down drawing")

  map_url = channel_dir_url + "/game_map.jpg"
  image.save(map_url, quality=40)

  return map_url
