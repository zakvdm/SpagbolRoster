import os
import cgi
from datetime import date
import urllib
import logging
import wsgiref.handlers

from django.utils import simplejson

from google.appengine.api import mail
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

CHRIS, NICK, STEVE, ZAK, NOBODY = "chris", "nick", "steve", "zak", "nobody"

namesDictionary = {CHRIS:"Chris", NICK:"Nick", STEVE:"Steve", ZAK:"Zak", NOBODY:"Nobody"}
dayDictionary = {"monday":"Monday", "tuesday":"Tuesday", "wednesday":"Wednesday", "thursday":"Thursday", "friday":"Friday", "saturday":"Saturday", "sunday":"Sunday", "noday":"Not Cooking"}
notificationRecipients = "'Chris <chrisdk@gmail.com>', 'Nicholas <nicholas.savage@gmail.com>', 'Stephen <sasherson@gmail.com>', 'Zak <zakvdm@gmail.com>'"

AGNES_PERK = "AGNES"

# DATASTORE ENTITIES:
class Schedule(db.Model):
    json = db.StringProperty()

class Perk(db.Model):
    start = db.DateProperty(required=True)
    type = db.StringProperty(required=True, choices=set([AGNES_PERK]))
    owner = db.StringProperty(required=True, choices=set([CHRIS, NICK, STEVE, ZAK, NOBODY]))

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
            total_duration = (coming_perk.start - current_perk.start).total_seconds()
            time_so_far = (today - current_perk.start).total_seconds()
            progress = int((time_so_far / total_duration) * 100)
            logging.info("Calculated Agnes progress: [total_duration = " + str(total_duration) + "][ time_so_far = " + str(time_so_far) + "][ progress = " + str(progress) + "]")
            break

        return agnes_turn, progress, next_agnes_turn
        

class LoadSchedule(webapp.RequestHandler):
    def get(self):
        schedule_query = Schedule.all() #.ancestor(cook_key('househusbands'))
        schedules = schedule_query.fetch(1)

        if len(schedules) == 0:
            scheduleJson = "{ \"chris\":\"monday\",\"nick\":\"thursday\",\"steve\":\"tuesday\",\"zak\":\"wednesday\"}"
            logging.info("Loading default schedule: " + scheduleJson);
        else:
            scheduleJson = simplejson.loads(schedules[0].json)
            logging.info("Loading persisted schedule: " + scheduleJson);
        
        self.response.headers.add_header("Content-Type", "application/json") 
        self.response.out.write(scheduleJson)

class SaveSchedule(webapp.RequestHandler):

    def put(self):
        # Check that the request was made by a house husbands
        if not users.is_current_user_admin():
            self.error(403) # access denied
            return

        logging.info("Received save request: " + self.request.body);

        schedule_query = Schedule.all() #.ancestor(cook_key('househusbands'))
        schedules = schedule_query.fetch(1)

        if len(schedules) == 0:
            #key = cook_key('househusbands')
            schedule = Schedule()
            schedule.json = simplejson.dumps(self.request.body)
            schedule.put()
            logging.info("Persisted schedule for the first time");
        else:
            schedule = schedules[0]
            schedule.json = simplejson.dumps(self.request.body)
            schedule.put()
            logging.info("Updated schedule");


        self.notify(simplejson.loads(self.request.body))

        self.response.headers.add_header("Content-Type", "application/json") 
        self.response.out.write("{}")

    def notify(self, schedule):
        chrisSchedule = namesDictionary[CHRIS] + " - " + dayDictionary[schedule[CHRIS]]
        nickSchedule = namesDictionary[NICK] + " - " + dayDictionary[schedule[NICK]]
        steveSchedule = namesDictionary[STEVE] + " - " + dayDictionary[schedule[STEVE]]
        zakSchedule = namesDictionary[ZAK] + " - " + dayDictionary[schedule[ZAK]]
        
        body = "The new shedule is:" + "\n  " + chrisSchedule + "\n  " + nickSchedule + "\n  " + steveSchedule + "\n  " + zakSchedule + "\n\n ~ http://spagbolroster.appspot.com"

        logging.debug("Sending email message with body: " + body);

        mail.send_mail(sender="Spagbol Roster <update@spagbolroster.appspotmail.com>",
                       to=notificationRecipients,
                       subject="Spagbol Roster has been updated",
                       body=body)

        logging.info("Sent email notifications to: " + notificationRecipients);


application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/loadSchedule', LoadSchedule),
                                      ('/saveSchedule', SaveSchedule)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

