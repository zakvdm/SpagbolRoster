import os
import logging

from google.appengine.api import users
from google.appengine.api import xmpp
from google.appengine.ext import webapp

from roster import *

class NotificationsHandler(webapp.RequestHandler):
    def get(self):
        # Check that the request was made by a house husband
        if not users.is_current_user_admin():
            logging.error("Non-admin user trying to run notifications task")
            return

        logging.info("Running notifications task")

        chef = Roster.getTodaysChef()

        if chef != None:
            user_address = ADDRESSES[chef]
            chat_message_sent = False
            chat_msg = "Remember: It's your turn to cook!"
            status_code = xmpp.send_message(user_address, chat_msg)
            chat_message_sent = (status_code == xmpp.NO_ERROR)

            logging.debug("Tried to send a chat message to " + chef)

            if not chat_message_sent:
                logging.info("Could not send chat message to " + str(user_address))

                message = mail.EmailMessage()

                message.sender = "spagbolroster@appspot.com"
                message.to = user_address
                message.subject = chat_msg
                message.body = "If you prefer, you can receive gtalk notifications by adding spagbolroster@appspot.com to your list of chat contacts."

                message.send()
                logging.info("Sent an email notification to " + str(user_address))


class InvitesHandler(webapp.RequestHandler):
    def get(self):
        # Check that the request was made by a house husband
        if not users.is_current_user_admin():
            logging.error("Non-admin user trying to run invites task")
            return

        logging.info("Inviting House Husbands to chat")

        xmpp.send_invite(ADDRESSES[CHRIS])
        xmpp.send_invite(ADDRESSES[NICK])
        xmpp.send_invite(ADDRESSES[STEVE])
        xmpp.send_invite(ADDRESSES[ZAK])

        logging.debug("Invites sent!")


