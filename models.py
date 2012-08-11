from google.appengine.ext import db

from constants import *

# DATASTORE ENTITIES:
class Schedule(db.Model):
    json = db.StringProperty()

class Week(db.Model):
    start = db.DateProperty(required=True)
    chris = db.StringProperty(required=True, choices=set(COOKING_OPTIONS))
    nick = db.StringProperty(required=True, choices=set(COOKING_OPTIONS))
    steve = db.StringProperty(required=True, choices=set(COOKING_OPTIONS))
    zak = db.StringProperty(required=True, choices=set(COOKING_OPTIONS))

class Perk(db.Model):
    start = db.DateProperty(required=True)
    type = db.StringProperty(required=True, choices=set([AGNES_PERK]))
    owner = db.StringProperty(required=True, choices=set([CHRIS, NICK, STEVE, ZAK, NOBODY]))

