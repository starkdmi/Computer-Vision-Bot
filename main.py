import StringIO
import json
import logging
import random
import urllib
import urllib2

# for sending images
from PIL import Image
import multipart

# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'

# Emoji
smile_standart = u'\U0001F603'
smile_laugh = u'\U0001F602'
smile_strong = u'\U0001F62F'
smile_girl = u'\U0001F64E'
smile_boy = u'\U0001F468'
smile_reading_glasses = u'\U0001F453'
smile_sun_glasses = u"\U0001F60E"
smile_swimming_glasses = u"\U0001F3CA"
smile_no_glasses = u"\U0001F636"

# Russian
_D = u'\u0414'

# Help
help_text = 'They call me ComputerVisionBot, I can find people in the photo and identify their emotions, age, sex and other.\n\nYou can control me by sending these commands:\n\n/start - enable bot\n/stop - disable bot\n/link - send your photo link to bot. For example: /link https://image.jpg'

# ================================

class EnableStatus(ndb.Model):
    # key name: str(chat_id)
    enabled = ndb.BooleanProperty(indexed=False, default=False)

# ================================

def setEnabled(chat_id, yes):
    es = EnableStatus.get_or_insert(str(chat_id))
    es.enabled = yes
    es.put()

def getEnabled(chat_id):
    es = EnableStatus.get_by_id(str(chat_id))
    if es:
        return es.enabled
    return False

# ================================

class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))

class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getUpdates'))))

class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))

class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        logging.info('request body:')
        logging.info(body)
        self.response.write(json.dumps(body))

        update_id = body['update_id']
        try:
            message = body['message']
        except:
            message = body['edited_message']
        message_id = message.get('message_id')
        date = message.get('date')
        text = message.get('text')
        fr = message.get('from')
        chat = message['chat']
        chat_id = chat['id']

        def reply(msg=None, img=None):
            if msg:
                resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                    'chat_id': str(chat_id),
                    'text': msg.encode('utf-8'),
                    'disable_web_page_preview': 'true',
                    'reply_to_message_id': str(message_id),            
                })).read()
            elif img:
                resp = multipart.post_multipart(BASE_URL + 'sendPhoto', [
                    ('chat_id', str(chat_id)),
                    ('reply_to_message_id', str(message_id)),
                ], [
                    ('photo', 'image.jpg', img),
                ])
            else:
                logging.error('no msg or img specified')
                resp = None

            logging.info('send response:')
            logging.info(resp)

        def recognize(link=None):
            url = 'https://api.projectoxford.ai/face/v1.0/detect?returnFaceId=false&returnFaceLandmarks=false&returnFaceAttributes=age,gender,smile,glasses'
            data = str(json.dumps({ 'url': link }))               
            headers = { 'Content-type': 'application/json', 'Ocp-Apim-Subscription-Key': 'YOUR_MICROSOFT_COGNITIVE_SERVICE_TOKEN' }
            request = urllib2.Request(url, data, headers)
            json_str_response = json.dumps(json.load(urllib2.urlopen(request)))
            json_data_response = json.loads(json_str_response)
                
            i = 0
            count = len(json_data_response)

            if count == 0:
                reply('Sorry, in the photo are not detected faces.')

            text_info = ''
            while i < count:
                age = float(json_data_response[i]['faceAttributes']['age'])
                smile =  int(float(json_data_response[i]['faceAttributes']['smile']) * 10) 
                gender = str(json_data_response[i]['faceAttributes']['gender'])
                glasses = str(json_data_response[i]['faceAttributes']['glasses'])
                str_age = ''
                str_smile = str(smile) + '/10 ' 

                if smile > 7:
                    str_smile += smile_laugh
                elif smile > 4:
                   str_smile += smile_standart
                elif smile < 5:
                   str_smile += smile_strong

                if gender == 'male':
                   gender = 'Man ' + smile_boy
                   str_age = str(int(age * 0.9))
                elif gender == 'female':
                   gender = 'Woman ' + smile_girl
                   str_age = str(int(age * 0.75))

                if glasses == 'noglasses':
                   glasses = 'No glasses ' + smile_no_glasses
                elif glasses == 'readingglasses':
                   glasses = 'Reading glasses ' + smile_reading_glasses
                elif glasses == 'sunglasses':
                   glasses = 'Sun glasses ' + smile_sun_glasses
                elif glasses == 'swimminggoggles':
                   glasses = 'Swimming glasses ' + smile_swimming_glasses
       
                text_info += str(i + 1) + ') Age: ' + str_age + '\n' + 'Gender: ' + gender + '\n' + 'Smile: ' + str_smile + '\n' + 'Glasses: ' + glasses + '\n\n'
                i += 1
                
            reply(text_info)

        if not text:
            logging.info('no text')
            photo = message['photo']
            if photo:
                photo1_id = photo[2].get('file_id')
                json_str= json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getfile?file_id=' + photo1_id)))
                json_data = json.loads(json_str)
                file_path = str(json_data.get('result')['file_path'])
                photo_url = 'https://api.telegram.org/file/bot' + TOKEN + '/' + file_path
                recognize(photo_url)        
            return

        if text.startswith('/'):
            if text == '/start':                      
                reply('Hello, ' + fr['first_name'])
                setEnabled(chat_id, True)
            elif text == '/stop':
                reply('Bot disabled')
                setEnabled(chat_id, False)
            elif text == '/help':
                reply(help_text)
            elif text.startswith('/link '):
                recognize(text[6:])  
            else:
                reply('What command?')

        # CUSTOMIZE FROM HERE

        elif 'who are you' in text:
            reply('ComputerVisionBot, created by starkov79 - https://github.com/starkov79/Computer-Vision-Bot')
        else:
            if getEnabled(chat_id):
                reply('I got your message! (but I do not know how to answer)')
            else:
                logging.info('not enabled for chat_id {}'.format(chat_id))


app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)
