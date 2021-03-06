import os
import cgi
from datetime import date
from datetime import timedelta
import urllib
import logging
import wsgiref.handlers

import json

from google.appengine.api import mail
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from constants import *
from models import *
from roster import *
from tasks import *

TOTAL_SKIPS = 3;

# REQUEST HANDLERS:
class MainPage(webapp.RequestHandler):
    def get(self):
   
        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_text = "logout"
            user_status = "in"
        else:
            url = users.create_login_url(self.request.uri)
            url_text = "login"
            user_status = "out"

        agnes_turn, agnes_progress, next_agnes_turn = self.agnesTurn()

        template_values = {
                 'url': url,
                 'url_text': url_text,
                 'user_status': user_status,
                 'agnes_turn': agnes_turn,
                 'agnes_progress': agnes_progress,
                 'next_agnes_turn': next_agnes_turn,
             }

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

    def agnesTurn(self):
        perk_count = Perk.all().count(1)
        if perk_count == 0:
            for i in range(0, 15):
                initialPerk = Perk(start=date(2001, 1, 1), type=AGNES_PERK, owner=NOBODY)
                initialPerk.put()

        today = date.today()
        perks = Perk.all().filter('start <=', today).order('-start').fetch(1)

        agnes_turn = "nobody"
        for perk in perks:
            current_perk = perk
            agnes_turn = namesDictionary[perk.owner]
            break

        coming_perks = Perk.all().filter('start >', today).order('start').fetch(1)

        progress = 0
        next_agnes_turn = "nobody"
        for coming_perk in coming_perks:
            next_agnes_turn = namesDictionary[coming_perk.owner]
            # Percent complete:
            total_duration = (coming_perk.start - current_perk.start).days
            time_so_far = (today - current_perk.start).days
            progress = int((float(time_so_far) / total_duration) * 100)
            logging.info("Calculated Agnes progress: [total_duration = " + str(total_duration) + "][ time_so_far = " + str(time_so_far) + "][ progress = " + str(progress) + "]")
            break

        return agnes_turn, progress, next_agnes_turn
        

class ScheduleHandler(webapp.RequestHandler):
    #GET
    def get(self):
        result = self.loadScheduleFromDb()

        logging.debug(result)

        self.response.headers.add_header("Content-Type", "application/json")
        self.response.out.write(result)

    # PUT 
    def put(self):
        # Check that the request was made by a house husbands
        if not users.is_current_user_admin():
            self.error(403) # access denied
            return

        logging.info("Received save request: " + self.request.body);

        new_schedule = json.loads(self.request.body)
        self.persistSchedule(new_schedule)

        self.notify(new_schedule["thisweek"], new_schedule["reason"])

        self.response.headers.add_header("Content-Type", "application/json") 
        self.response.out.write(self.loadScheduleFromDb())

    def persistSchedule(self, new_schedule):
        this_week_start_date, next_week_start_date = Roster.getWeekStarts()

        this_week = Roster.getOrInsertWeekByStartDate(this_week_start_date, new_schedule["thisweek"])
        next_week = Roster.getOrInsertWeekByStartDate(next_week_start_date, new_schedule["nextweek"])


        this_week.chris = new_schedule["thisweek"][CHRIS]
        this_week.nick = new_schedule["thisweek"][NICK]
        this_week.steve = new_schedule["thisweek"][STEVE]
        this_week.zak = new_schedule["thisweek"][ZAK]

        next_week.chris = new_schedule["nextweek"][CHRIS]
        next_week.nick = new_schedule["nextweek"][NICK]
        next_week.steve = new_schedule["nextweek"][STEVE]
        next_week.zak = new_schedule["nextweek"][ZAK]

        this_week.put()
        next_week.put()

        logging.info("updated schedule");
  

    def loadScheduleFromDb(self):
        best_guess_schedule = {CHRIS:NODAY, NICK:NODAY, STEVE:NODAY, ZAK:NODAY}
        last_schedule = Week.all().order('-start').fetch(1)
        logging.debug("Getting best guess of schedule in case we're on a new week")
        for schedule in last_schedule:
            logging.debug("Found a previous schedule to base the new ones on")
            best_guess_schedule = {CHRIS:schedule.chris, NICK:schedule.nick, STEVE:schedule.steve, ZAK:schedule.zak}

        this_week_start_date, next_week_start_date = Roster.getWeekStarts()

        this_week = Roster.getOrInsertWeekByStartDate(this_week_start_date, best_guess_schedule)
        next_week = Roster.getOrInsertWeekByStartDate(next_week_start_date, best_guess_schedule)

        this_week_schedule = { "start":this_week_start_date, CHRIS:this_week.chris, NICK:this_week.nick, STEVE:this_week.steve, ZAK:this_week.zak }
        next_week_schedule = { "start":next_week_start_date, CHRIS:next_week.chris, NICK:next_week.nick, STEVE:next_week.steve, ZAK:next_week.zak }

        skips = self.getSkips()

        logging.info("This week's schedule: " + str(this_week_schedule))
        logging.info("Next week's schedule: " + str(next_week_schedule))
        logging.info("Skips: " + str(skips))

        dthandler = lambda obj: obj.isoformat() if isinstance(obj, date) else None
        return json.dumps({"thisweek":this_week_schedule, "nextweek":next_week_schedule, "skips":skips}, default=dthandler)
        

    def getSkips(self):
        chrisSkips = Week.all().filter(CHRIS + ' = ', SKIPPING).count()
        nickSkips = Week.all().filter(NICK + ' = ', SKIPPING).count()
        steveSkips = Week.all().filter(STEVE + ' = ', SKIPPING).count()
        zakSkips = Week.all().filter(ZAK + ' = ', SKIPPING).count()
        totalSkips = 3
        return { CHRIS:totalSkips - chrisSkips, NICK:totalSkips - nickSkips, STEVE:totalSkips - steveSkips, ZAK:totalSkips - zakSkips }
    
    def notify(self, schedule, reason):
        chrisSchedule = namesDictionary[CHRIS] + " - " + dayDictionary[schedule[CHRIS]]
        nickSchedule = namesDictionary[NICK] + " - " + dayDictionary[schedule[NICK]]
        steveSchedule = namesDictionary[STEVE] + " - " + dayDictionary[schedule[STEVE]]
        zakSchedule = namesDictionary[ZAK] + " - " + dayDictionary[schedule[ZAK]]

        body = "The new shedule is:" + "\n  " + chrisSchedule + "\n  " + nickSchedule + "\n  " + steveSchedule + "\n  " + zakSchedule + "\n\n  " + reason + "\n\n~ http://spagbolroster.appspot.com"

        logging.debug("Standard email message body: " + body);

        message = mail.EmailMessage()

        message.sender = users.get_current_user().email()
        message.to = notificationRecipients
        message.subject = "I've updated Spagbol Roster"
        message.body = body


        template_values = {
                 'reason': reason,
                 'schedule': self.sortByDay(schedule),
             }

        path = os.path.join(os.path.dirname(__file__), 'email.html')
        message.html = template.render(path, template_values)

        logging.debug("HTML email message body: " + message.html)

        message.send()

        logging.info("Sent email notifications to: " + notificationRecipients);

    def sortByDay(self, schedule):
        daySchedule = {}

        chrisDay = schedule[CHRIS]
        nickDay = schedule[NICK]
        steveDay = schedule[STEVE]
        zakDay = schedule[ZAK]

        daySchedule[chrisDay] = namesDictionary[CHRIS]
        if daySchedule.has_key(nickDay):
            daySchedule[nickDay] = daySchedule[nickDay] + "|" + namesDictionary[NICK]
        else:
            daySchedule[nickDay] = namesDictionary[NICK]
        if daySchedule.has_key(steveDay):
            daySchedule[steveDay] = daySchedule[steveDay] + "|" + namesDictionary[STEVE]
        else:
            daySchedule[steveDay] = namesDictionary[STEVE]
        if daySchedule.has_key(zakDay):
            daySchedule[zakDay] = daySchedule[zakDay] + "|" + namesDictionary[ZAK]
        else:
            daySchedule[zakDay] = namesDictionary[ZAK]

        return daySchedule


application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/schedule', ScheduleHandler)],
                                     debug=True)

