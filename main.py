import os
import cgi
import datetime
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

namesDictionary = {"chris":"Chris", "nick":"Nick", "steve":"Steve", "zak":"Zak"}
dayDictionary = {"monday":"Monday", "tuesday":"Tuesday", "wednesday":"Wednesday", "thursday":"Thursday", "friday":"Friday", "saturday":"Saturday", "sunday":"Sunday", "noday":"Not Cooking"}
notificationRecipients = "'Chris <chrisdk@gmail.com>', 'Nicholas <nicholas.savage@gmail.com>', 'Stephen <sasherson@gmail.com>', 'Zak <zakvdm@gmail.com>'"

class Schedule(db.Model):
    json = db.StringProperty()

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

        template_values = {
                 'url': url,
                 'url_text': url_text,
                 'user_status': user_status,
             }

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

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
        chrisSchedule = namesDictionary["chris"] + " - " + dayDictionary[schedule["chris"]]
        nickSchedule = namesDictionary["nick"] + " - " + dayDictionary[schedule["nick"]]
        steveSchedule = namesDictionary["steve"] + " - " + dayDictionary[schedule["steve"]]
        zakSchedule = namesDictionary["zak"] + " - " + dayDictionary[schedule["zak"]]
        
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

