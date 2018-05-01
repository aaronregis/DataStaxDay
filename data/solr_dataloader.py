from __future__ import print_function
import csv
import locale
import multiprocessing
import os
import random
import sys
import signal
import time
import uuid
import gzip
import traceback
from itertools import chain
from datetime import date, timedelta, datetime

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

KEYSPACE = sys.argv[1]
META_COLUMN_FAMILY = "metadata"
RANK_COLUMN_FAMILY = "rank"
GEO_COLUMN_FAMILY = "clicks"

"""
{'asin': '0007148089',
 'title': "Blood and Roses: One Family's Struggle and Triumph During the Tumultuous Wars of the Roses",
 'price': 5.98,
 'imUrl': 'http://ecx.images-amazon.com/images/I/518p8d64F8L.jpg',
 'related': {
      'also_bought': ['0061430765', '0061430773', 'B00A4E8E78'],
      'buy_after_viewing': ['0061430773', '0345404335', 'B00A4E8E78', '0975126407']
 },
 'salesRank': {'Books': 326205},
 'categories': [['Books']]
}
"""

IP_LOCATIONS = [
    [608,"US","CA","San Francisco","94124",37.7312,-122.3826,807,415],
    [757,"US","CA","San Francisco","94105",37.7898,-122.3942,807,415],
    [1090,"US","CA","San Francisco","94104",37.7909,-122.4017,807,415],
    [1131,"US","CA","South San Francisco","94080",37.6547,-122.4077,807,650],
    [1258,"US","CA","San Francisco","94111",37.7989,-122.3984,807,415],
    [2023,"US","CA","San Francisco","94102",37.7794,-122.4170,807,415],
    [2155,"US","CA","San Francisco","94107",37.7697,-122.3933,807,415],
    [2156,"US","CA","San Francisco","94109",37.7957,-122.4209,807,415],
    [3337,"US","CA","San Francisco","94108",37.7915,-122.4089,807,415],
    [5143,"US","CA","San Francisco","94110",37.7484,-122.4156,807,415],
    [4122,"US","CA","San Francisco","94128",37.6198,-122.3802,807,650],
    [180967,"US","CA","San Francisco","94172",37.7749,-122.4194,807,530],
    [180971,"US","CA","San Francisco","94161",37.7848,-122.7278,807,415],
    [181238,"US","CA","San Francisco","94171",37.7848,-122.7278,807,415],
    [181591,"US","CA","San Francisco","94165",37.7749,-122.4194,807,415],
    [186935,"US","CA","San Francisco","94137",37.7848,-122.7278,807,990],
    [187521,"US","CA","San Francisco","94145",37.7848,-122.7278,807,415],
    [376821,"US","CA","South San Francisco","94099",37.3811,-122.3348,807,650],
    [399988,"US","CA","San Francisco","66666",37.7749,-122.4194,807,666]]

IP_BLOCKS = [
    [1249426944,1249427199],
    [3423530752,3423530764],
    [3423530766,3423531007],
    [3431071744,3431071999],
    [3639573549,3639573759]]

ASINS = [
    "0028330692","0007393571","0028615115","0001381245","0007189923","0007278675",
    "0020287011","0025178717","0004539869","0007425201","0020187106","0007122772",
    "0026155907","0002159643","0007158505","0010004653","0007256728","0007205503",
    "0002166453","0002554771","0030353734","0020299605","0007141750","0006196454",
    "0002008572","0006382479","0005834252","0006481744","0020094000","0030435927",
    "0028610083","0007178301","0002006758","0006479529","0028608364","0022801510",
    "0021938997","0007278799","0020519001","0007537956","0028642112","0029146402",
    "0007126522","0028629450","0028603664","0002005387","0030210917","0029076102",
    "0028648463","0030466512","0027744116","0025210505","0007101910","0020007507",
    "0022784950","0030438853","0028637879","0028609328","0021812233","0002558793",
    "0022860231","0026406012","0006460763","0007281951","0005658640","0026301407",
    "0007199074","0007114893","0001485423","0028614321","0020298900","0021847312",
    "0007102305","0005997496","0029190908","0028050231","0002557592","0007786786",
    "0028639367","0007105665","0007166699"]


KS_CREATION_STATEMENT = """
CREATE KEYSPACE IF NOT EXISTS %s WITH replication = { 'class' : 'SimpleStrategy', 'replication_factor' : 3 };
"""  % (KEYSPACE)

META_CF_CREATION_STATEMENT = """
CREATE TABLE IF NOT EXISTS %s.%s (
    asin text,
    title text,
    imurl text,
    price double,
    categories set<text>,
    also_bought set<text>,
    buy_after_viewing set<text>,
    PRIMARY KEY(asin));
"""  % (KEYSPACE, META_COLUMN_FAMILY)

RANK_CF_CREATION_STATEMENT = """
CREATE TABLE IF NOT EXISTS %s.%s (
    asin text,
    category text,
    rank int,
    PRIMARY KEY(asin, category));
"""  % (KEYSPACE, RANK_COLUMN_FAMILY)

GEO_CF_CREATION_STATEMENT = """
CREATE TABLE IF NOT EXISTS %s.%s (
  user uuid,
  seq timeuuid,
  asin text,
  loc_id text,
  country text,
  region text,
  city text,
  postal_code text,
  metro_code text,
  area_code text,
  ip text,
  location text,
  location_0_coordinate double,
  location_1_coordinate double,
  PRIMARY KEY (asin, seq, user)) WITH CLUSTERING ORDER BY (seq DESC)
;""" % (KEYSPACE, GEO_COLUMN_FAMILY)

META_CF_DROP_STATEMENT = """DROP TABLE IF EXISTS %s.%s;"""  % (KEYSPACE, META_COLUMN_FAMILY)
RANK_CF_DROP_STATEMENT = """DROP TABLE IF EXISTS %s.%s;"""  % (KEYSPACE, RANK_COLUMN_FAMILY)
GEO_CF_DROP_STATEMENT = """DROP TABLE IF EXISTS %s.%s;"""  % (KEYSPACE, GEO_COLUMN_FAMILY)

META_INSERT_STATEMENT = "INSERT INTO %s.%s(asin, title, imurl, price, categories, also_bought, buy_after_viewing) VALUES(?,?,?,?,?,?,?)" \
                        % (KEYSPACE, META_COLUMN_FAMILY)

RANK_INSERT_STATEMENT = "INSERT INTO %s.%s(asin, category, rank) VALUES(?, ?, ?)" \
                        % (KEYSPACE, RANK_COLUMN_FAMILY)

GEO_INSERT_STATEMENT = "INSERT INTO %s.%s(user, seq, asin, loc_id, country, region, city, postal_code, metro_code, area_code, ip, location) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)" \
                       % (KEYSPACE, GEO_COLUMN_FAMILY)

def parse(path):
    g = open(path, 'r')
    for l in g:
        yield eval(l)

def random_ip():
    (start, stop) = random.choice(IP_BLOCKS)
    ipnum = random.randrange(start, stop)
    o1 = int ( ipnum / 16777216 ) % 256
    o2 = int ( ipnum / 65536    ) % 256
    o3 = int ( ipnum / 256      ) % 256
    o4 = int ( ipnum            ) % 256
    address = '.'.join(map(str, [o1, o2, o3, o4]))
    return address


def generate_geo_data():
    writer = csv.writer(sys.stdout)

    for _ in xrange(100):
        user = uuid.uuid4()
        for _ in xrange(500):
            seq = uuid.uuid1()
            asin = random.choice(ASINS)
            ip = random_ip()
            (loc_id, country, region, city, postal_code, lat, lon, metro_code, area_code) = random.choice(IP_LOCATIONS)
            data = [user, seq, asin, loc_id, country,
                    region, city, postal_code, metro_code,
                    area_code, ip, "%s,%s" % (lat, lon)]

            writer.writerow(data)


def load_geo_data(session, geopath):
    geo_prepared = session.prepare(GEO_INSERT_STATEMENT)
    with open(geopath, 'rb') as f:
        reader = csv.reader(f)
        for row in reader:
            geo_bound = geo_prepared.bind(map(uuid.UUID, row[0:2]) +  row[2:])
            session.execute(geo_bound)




if __name__ == '__main__':
    meta_path = 'metadata.json'
    geo_path = 'geodata.csv'
    auth_provider = PlainTextAuthProvider(username='cassandra', password='Password1234')
    cluster = Cluster(['dc0vm0','dc0vm1','dc0vm2'],auth_provider=auth_provider)
    session = cluster.connect()
    session.execute(META_CF_DROP_STATEMENT)
    session.execute(RANK_CF_DROP_STATEMENT)
    session.execute(GEO_CF_DROP_STATEMENT)
    session.execute(KS_CREATION_STATEMENT)
    session.execute(GEO_CF_CREATION_STATEMENT)
    session.execute(META_CF_CREATION_STATEMENT)
    session.execute(RANK_CF_CREATION_STATEMENT)

    meta_prepared = session.prepare(META_INSERT_STATEMENT)
    rank_prepared = session.prepare(RANK_INSERT_STATEMENT)
    print ('Loading into Keyspace',sys.argv[1])
    print ('loading geo')
    load_geo_data(session, geo_path)
    print ('loading meta')
    for data in parse(meta_path):
        asin = data['asin']
        title = data.get('title', "")
        imurl = data.get('imUrl', "")
        price = data.get('price', 0.0)
        categories = list(chain.from_iterable(data.get('categories', [])))
        related = data.get('related', {})
        also_bought = related.get('also_bought', [])
        buy_after_viewing = related.get('buy_after_viewing', [])
        meta_bound = meta_prepared.bind([asin, title, imurl, price, categories, also_bought, buy_after_viewing])
        session.execute(meta_bound)

        for (category, rank) in data.get('salesRank', {}).items():
            rank_bound = rank_prepared.bind([asin, category, rank])
            session.execute(rank_bound)

    print ('Finished!')
    
