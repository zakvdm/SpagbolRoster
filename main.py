import os
import cgi
import datetime
import urllib
import logging
import wsgiref.handlers

from django.utils import simplejson

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

class Schedule(db.Model):
    json = db.StringProperty()

class MainPage(webapp.RequestHandler):
    def get(self):
        #cooks_query = Cook.all().ancestor(cook_key('househusbands'))
        #cooks = cooks_query.fetch(4)
        #template_values = {
                    #'cooks': cooks
                #}

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        #self.response.out.write(template.render(path, template_values))
        self.response.out.write(template.render(path, None))

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

        #if func[0] == '_':
            #self.error(403) # access denied
            #return

        #func = getattr(self.methods, func, None)
        #if not func:
            #self.error(404) # file not found
            #return

        self.response.headers.add_header("Content-Type", "application/json") 
        self.response.out.write("Success!")


application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/loadSchedule', LoadSchedule),
                                      ('/saveSchedule', SaveSchedule)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

