from datetime import date
from datetime import timedelta
import logging

from models import *
from constants import *

class Roster:
    @staticmethod
    def getKey(week_start):
        # Prefix key:
        return 'week:' + str(week_start.year) + "-" + str(week_start.month) + "-" + str(week_start.day)


    @staticmethod
    def getWeekStarts():
        today = date.today()
        days_since_monday = timedelta(days=today.weekday())
        this_week = today - days_since_monday
        next_week = this_week + timedelta(days=7)
        logging.debug("Start of week is: " + str(this_week))
        return this_week, next_week

    @staticmethod
    def getOrInsertWeekByStartDate(week_start, new_values): 
        key = Roster.getKey(week_start)

        return Week.get_or_insert(key, start=week_start, chris=new_values["chris"], nick=new_values["nick"], steve=new_values["steve"], zak=new_values["zak"])

    @staticmethod
    def getWeek(start_date):
        key_name = Roster.getKey(start_date)
        logging.debug("Key is: " + key_name)
        return Week.get_by_key_name(key_name)


    @staticmethod
    def getTodaysChef():
        today = DAYS_OF_THE_WEEK[date.today().weekday()] # get the string name for today
        this_week_start_date, _ = Roster.getWeekStarts()
        schedule = Roster.getWeek(this_week_start_date)

        chef = None

        if schedule != None:
            if schedule.chris == today:
                chef = CHRIS
            if schedule.nick == today:
                chef = NICK
            if schedule.steve == today:
                chef = STEVE
            if schedule.zak == today:
                chef = ZAK

        return chef
       

