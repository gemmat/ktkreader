#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gzip
from StringIO import StringIO
import cgi
import wsgiref.handlers
import codecs
import urllib
import logging

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.runtime import apiproxy_errors

class Subject(db.Model):
  board = db.LinkProperty()
  etag = db.StringProperty()
  lastmodified = db.StringProperty()
  content = db.TextProperty()

class Dat2ch(db.Model):
  board = db.LinkProperty()
  thread = db.StringProperty()
  etag = db.StringProperty()
  lastmodified = db.StringProperty()
  content = db.TextProperty()
  content_length = db.IntegerProperty()

def get_subject(board):
  headers={'Content-Type': 'application/x-www-form-urlencoded',
           'Accept-Encoding': 'gzip'}

  q = Subject.all().filter("board =", board).get()
  if q:
    headers['If-None-Match'] = q.etag
    headers['If-Modified-Since'] = q.lastmodified
  else:
    q = Subject()

  result = urlfetch.fetch(url="%s/subject.txt" % board,headers=headers)
  
  if result.status_code == 200:
    if result.headers.has_key('content-encoding') and result.headers['content-encoding'] == 'gzip':
      # data came back gzip-compressed, decompress it          
      result.content = gzip.GzipFile(fileobj=StringIO(result.content)).read()
    q.board = board
    # save ETag, if the server sent one
    if result.headers.has_key('ETag'):
      q.etag = result.headers['ETag']
    # save Last-Modified header, if the server sent one          
    if result.headers.has_key('Last-Modified'):
      q.lastmodified = result.headers['Last-Modified']
    q.content = db.Text(result.content.decode('shift_jis','replace').encode('shift_jis','replace'),encoding='shift_jis')
    try:
      q.put()
    except apiproxy_errors.OverQuotaError, message:
      # Record the error in your logs
      logging.error(message)
      delete_data()
    return result.content.decode('shift_jis','replace').encode('utf-8','replace')
  elif result.status_code == 304:
    return q.content
  else:
    logging.warning('error get_subject')
    logging.warning(result.status_code)
    logging.warning(headers)
    return None

def get_dat_diff(q,board,thread):
  headers={'Content-Type': 'application/x-www-form-urlencoded'}
  headers['If-None-Match'] = q.etag
  headers['If-Modified-Since'] = q.lastmodified
  headers['Range'] = 'bytes=%d-' % q.content_length

  result = urlfetch.fetch(url="%s/dat/%s.dat" % (board,thread),headers=headers)

  if result.status_code == 206:
    q.content_length += len(result.content)
    content = q.content + result.content.decode('shift_jis','replace')
    content = content.encode('shift_jis','replace')
    # save ETag, if the server sent one
    if result.headers.has_key('ETag'):
      q.etag = result.headers['ETag']
    # save Last-Modified header, if the server sent one          
    if result.headers.has_key('Last-Modified'):
      q.lastmodified = result.headers['Last-Modified']
    q.content = db.Text(content.decode('shift_jis','replace').encode('shift_jis','replace'),encoding='shift_jis')
    q.put()
    return content.decode('shift_jis','replace').encode('utf-8','replace')
  elif result.status_code == 200:
    if result.headers.has_key('content-encoding') and result.headers['content-encoding'] == 'gzip':
      # data came back gzip-compressed, decompress it          
      content = gzip.GzipFile(fileobj=StringIO(result.content)).read()
    else:
      content = result.content
    # save ETag, if the server sent one
    if result.headers.has_key('ETag'):
      q.etag = result.headers['ETag']
    # save Last-Modified header, if the server sent one          
    if result.headers.has_key('Last-Modified'):
      q.lastmodified = result.headers['Last-Modified']
    q.content = db.Text(content.decode('shift_jis','replace').encode('shift_jis','replace'),encoding='shift_jis')
    q.content_length = len(content)
    try:
      q.put()
    except apiproxy_errors.OverQuotaError, message:
      # Record the error in your logs
      logging.error(message)
      delete_data()
    return content.decode('shift_jis','replace').encode('utf-8','replace')
  elif result.status_code == 304:
    return q.content
  elif result.status_code == 416:
    #adhoc fix.
    str = q.content
    q.content_length = 0
    q.content = db.Text('')
    q.put()    
    return str
  else:
    logging.warning('error get_dat_diff')
    logging.warning(result.status_code)
    logging.warning(headers)
    return None

def get_dat(board,thread):
  headers={'Content-Type': 'application/x-www-form-urlencoded',
           'Accept-Encoding': 'gzip'}
  q = Dat2ch()

  result = urlfetch.fetch(url="%s/dat/%s.dat" % (board,thread),headers=headers)
  
  if result.status_code == 200:
    if result.headers.has_key('content-encoding') and result.headers['content-encoding'] == 'gzip':
      # data came back gzip-compressed, decompress it          
      content = gzip.GzipFile(fileobj=StringIO(result.content)).read()
    else:
      content = result.content
    q.board = board
    q.thread = thread
    # save ETag, if the server sent one
    if result.headers.has_key('ETag'):
      q.etag = result.headers['ETag']
    # save Last-Modified header, if the server sent one          
    if result.headers.has_key('Last-Modified'):
      q.lastmodified = result.headers['Last-Modified']
    q.content = db.Text(content.decode('shift_jis','replace').encode('shift_jis','replace'),encoding='shift_jis')
    q.content_length = len(content)
    try:
      q.put()
    except apiproxy_errors.OverQuotaError, message:
      # Record the error in your logs
      logging.error(message)
      delete_data()
    return content.decode('shift_jis','replace').encode('utf-8','replace')
  else:
    logging.warning('error get_dat')
    logging.warning(result.status_code)
    logging.warning(headers)
    return None

class KtkrHandler(webapp.RequestHandler):
  def post(self):
    board = urllib.unquote(self.request.get('board'));
    thread = self.request.get('thread')
    head = self.request.get('head')
    if head.isdigit():
      head = int(head)
      if head < 0:
        head = 0
    else:
      head = 0

    if board and board_dict.has_key(board) and thread and thread.isdigit():
      q = Dat2ch.all().filter("board =", board).filter("thread =", thread).get()
      if q:
        content = get_dat_diff(q,board,thread)
      else:
        content = get_dat(board,thread)
      if content:
        content = '\n'.join(content.split('\n')[head:])
    elif board and board_dict.has_key(board):
      content = get_subject(board)
    else:
      content = 'error %s %s %s %s' % (board,board_dict.has_key(board),thread,thread.isdigit())

    self.response.headers['Content-Type'] = 'text/plain'
    if content:
      self.response.out.write(content)

  def get(self):
    self.post()

def delete_data():
  q = Dat2ch.all().fetch(limit=50)
  for e in q:
    e.delete()
  q = Subject.all().fetch(limit=50)
  for e in q:
    e.delete()

class Dell(webapp.RequestHandler):
  def post(self):
    delete_data()
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write('ok')
  def get(self):
    self.post()


def main():
  application = webapp.WSGIApplication([('/ktkr.cgi', KtkrHandler),
                                        ('/deleter.cgi',Dell)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)


board_dict = {
 "http://headline.2ch.net/bbynamazu/":True,
 "http://news24.2ch.net/namazuplus/":True,
 "http://live24.2ch.net/eq/":True,
 "http://live23.2ch.net/eqplus/":True,
 "http://money6.2ch.net/ftax/":True,
 "http://news24.2ch.net/bizplus/":True,
 "http://etc7.2ch.net/infection/":True,
 "http://hobby11.2ch.net/point/":True,
 "http://epg.2ch.net/tv2chwiki/":True,
 "http://changi.2ch.net/be/":True,
 "http://etc7.2ch.net/nandemo/":True,
 "http://etc7.2ch.net/argue/":True,
 "http://headline.2ch.net/bbynews/":True,
 "http://news24.2ch.net/bizplus/":True,
 "http://mamono.2ch.net/newsplus/":True,
 "http://news24.2ch.net/wildplus/":True,
 "http://news24.2ch.net/moeplus/":True,
 "http://news24.2ch.net/mnewsplus/":True,
 "http://news24.2ch.net/femnewsplus/":True,
 "http://news24.2ch.net/dqnplus/":True,
 "http://news24.2ch.net/scienceplus/":True,
 "http://news24.2ch.net/owabiplus/":True,
 "http://news24.2ch.net/liveplus/":True,
 "http://namidame.2ch.net/news/":True,
 "http://news24.2ch.net/trafficinfo/":True,
 "http://music8.2ch.net/musicnews/":True,
 "http://anime3.2ch.net/comicnews/":True,
 "http://news24.2ch.net/gamenews/":True,
 "http://pc11.2ch.net/pcnews/":True,
 "http://news24.2ch.net/news7/":True,
 "http://bubble6.2ch.net/archives/":True,
 "http://news24.2ch.net/news2/":True,
 "http://tmp7.2ch.net/asia/":True,
 "http://tmp7.2ch.net/bakanews/":True,
 "http://money6.2ch.net/editorial/":True,
 "http://society6.2ch.net/kokusai/":True,
 "http://news24.2ch.net/news4plus/":True,
 "http://news24.2ch.net/news5/":True,
 "http://sports2.2ch.net/iraq/":True,
 "http://news24.2ch.net/news5plus/":True,
 "http://bubble6.2ch.net/dejima/":True,
 "http://qb5.2ch.net/operate/":True,
 "http://sports2.2ch.net/operatex/":True,
 "http://qb5.2ch.net/sec2ch/":True,
 "http://qb5.2ch.net/sec2chd/":True,
 "http://qb5.2ch.net/saku2ch/":True,
 "http://qb5.2ch.net/saku/":True,
 "http://qb5.2ch.net/sakud/":True,
 "http://qb5.2ch.net/sakukb/":True,
 "http://changi.2ch.net/intro/":True,
 "http://human7.2ch.net/honobono/":True,
 "http://changi.2ch.net/yume/":True,
 "http://sports11.2ch.net/offmatrix/":True,
 "http://sports11.2ch.net/offreg/":True,
 "http://sports11.2ch.net/offevent/":True,
 "http://love6.2ch.net/aasaloon/":True,
 "http://love6.2ch.net/mona/":True,
 "http://love6.2ch.net/nida/":True,
 "http://love6.2ch.net/aastory/":True,
 "http://love6.2ch.net/kao/":True,
 "http://society6.2ch.net/mass/":True,
 "http://tmp7.2ch.net/youth/":True,
 "http://science6.2ch.net/disaster/":True,
 "http://love6.2ch.net/gender/":True,
 "http://society6.2ch.net/giin/":True,
 "http://news24.2ch.net/manifesto/":True,
 "http://society6.2ch.net/police/":True,
 "http://society6.2ch.net/court/":True,
 "http://society6.2ch.net/soc/":True,
 "http://society6.2ch.net/atom/":True,
 "http://society6.2ch.net/river/":True,
 "http://society6.2ch.net/traf/":True,
 "http://money6.2ch.net/recruit/":True,
 "http://changi.2ch.net/job/":True,
 "http://society6.2ch.net/volunteer/":True,
 "http://society6.2ch.net/welfare/":True,
 "http://society6.2ch.net/mayor/":True,
 "http://money6.2ch.net/ftax/":True,
 "http://society6.2ch.net/jsdf/":True,
 "http://money6.2ch.net/nenga/":True,
 "http://school7.2ch.net/lifework/":True,
 "http://society6.2ch.net/regulate/":True,
 "http://money6.2ch.net/venture/":True,
 "http://money6.2ch.net/manage/":True,
 "http://money6.2ch.net/management/":True,
 "http://money6.2ch.net/estate/":True,
 "http://society6.2ch.net/koumu/":True,
 "http://school7.2ch.net/shikaku/":True,
 "http://school7.2ch.net/lic/":True,
 "http://money6.2ch.net/haken/":True,
 "http://society6.2ch.net/hoken/":True,
 "http://money6.2ch.net/tax/":True,
 "http://school7.2ch.net/exam/":True,
 "http://society6.2ch.net/hosp/":True,
 "http://society6.2ch.net/bio/":True,
 "http://society6.2ch.net/hikari/":True,
 "http://money6.2ch.net/dtp/":True,
 "http://changi.2ch.net/part/":True,
 "http://society6.2ch.net/koukoku/":True,
 "http://society6.2ch.net/agri/":True,
 "http://money6.2ch.net/build/":True,
 "http://etc7.2ch.net/peko/":True,
 "http://tmp7.2ch.net/company/":True,
 "http://life9.2ch.net/bouhan/":True,
 "http://pc11.2ch.net/antispam/":True,
 "http://tmp7.2ch.net/ihou/":True,
 "http://tmp7.2ch.net/ihan/":True,
 "http://love6.2ch.net/expo/":True,
 "http://human7.2ch.net/subcal/":True,
 "http://love6.2ch.net/bun/":True,
 "http://love6.2ch.net/poem/":True,
 "http://tv11.2ch.net/movie/":True,
 "http://tv11.2ch.net/cinema/":True,
 "http://bubble6.2ch.net/rmovie/":True,
 "http://bubble6.2ch.net/kinema/":True,
 "http://hobby11.2ch.net/occult/":True,
 "http://etc7.2ch.net/esp/":True,
 "http://tv11.2ch.net/sfx/":True,
 "http://bubble6.2ch.net/rsfx/":True,
 "http://hobby11.2ch.net/drama/":True,
 "http://hobby11.2ch.net/siki/":True,
 "http://hobby11.2ch.net/fortune/":True,
 "http://hobby11.2ch.net/uranai/":True,
 "http://love6.2ch.net/kyoto/":True,
 "http://academy6.2ch.net/gallery/":True,
 "http://hobby11.2ch.net/rakugo/":True,
 "http://society6.2ch.net/ruins/":True,
 "http://science6.2ch.net/rikei/":True,
 "http://science6.2ch.net/sci/":True,
 "http://science6.2ch.net/life/":True,
 "http://science6.2ch.net/bake/":True,
 "http://science6.2ch.net/kikai/":True,
 "http://science6.2ch.net/denki/":True,
 "http://science6.2ch.net/robot/":True,
 "http://science6.2ch.net/infosys/":True,
 "http://science6.2ch.net/informatics/":True,
 "http://science6.2ch.net/sim/":True,
 "http://science6.2ch.net/nougaku/":True,
 "http://science6.2ch.net/sky/":True,
 "http://school7.2ch.net/doctor/":True,
 "http://science6.2ch.net/kampo/":True,
 "http://science6.2ch.net/math/":True,
 "http://science6.2ch.net/doboku/":True,
 "http://science6.2ch.net/material/":True,
 "http://love6.2ch.net/space/":True,
 "http://science6.2ch.net/future/":True,
 "http://science6.2ch.net/wild/":True,
 "http://science6.2ch.net/earth/":True,
 "http://academy6.2ch.net/psycho/":True,
 "http://academy6.2ch.net/gengo/":True,
 "http://academy6.2ch.net/pedagogy/":True,
 "http://academy6.2ch.net/sociology/":True,
 "http://academy6.2ch.net/economics/":True,
 "http://love6.2ch.net/book/":True,
 "http://love6.2ch.net/poetics/":True,
 "http://academy6.2ch.net/history/":True,
 "http://academy6.2ch.net/history2/":True,
 "http://academy6.2ch.net/whis/":True,
 "http://academy6.2ch.net/archeology/":True,
 "http://academy6.2ch.net/min/":True,
 "http://academy6.2ch.net/kobun/":True,
 "http://academy6.2ch.net/english/":True,
 "http://society6.2ch.net/korea/":True,
 "http://academy6.2ch.net/china/":True,
 "http://academy6.2ch.net/taiwan/":True,
 "http://academy6.2ch.net/geo/":True,
 "http://love6.2ch.net/chiri/":True,
 "http://academy6.2ch.net/gogaku/":True,
 "http://academy6.2ch.net/art/":True,
 "http://academy6.2ch.net/philo/":True,
 "http://academy6.2ch.net/jurisp/":True,
 "http://changi.2ch.net/shihou/":True,
 "http://hobby11.2ch.net/kaden/":True,
 "http://bubble6.2ch.net/wm/":True,
 "http://bubble6.2ch.net/vcamera/":True,
 "http://bubble6.2ch.net/bakery/":True,
 "http://bubble6.2ch.net/toilet/":True,
 "http://hobby11.2ch.net/sony/":True,
 "http://hobby11.2ch.net/phs/":True,
 "http://hobby11.2ch.net/keitai/":True,
 "http://hobby11.2ch.net/chakumelo/":True,
 "http://hobby11.2ch.net/appli/":True,
 "http://hobby11.2ch.net/dgoods/":True,
 "http://hobby11.2ch.net/camera/":True,
 "http://hobby11.2ch.net/dcamera/":True,
 "http://hobby11.2ch.net/av/":True,
 "http://hobby11.2ch.net/pav/":True,
 "http://money6.2ch.net/seiji/":True,
 "http://society6.2ch.net/diplomacy/":True,
 "http://society6.2ch.net/trafficpolicy/":True,
 "http://money6.2ch.net/eco/":True,
 "http://changi.2ch.net/stock/":True,
 "http://live27.2ch.net/stockb/":True,
 "http://changi.2ch.net/market/":True,
 "http://mamono.2ch.net/livemarket1/":True,
 "http://changi.2ch.net/livemarket2/":True,
 "http://money6.2ch.net/deal/":True,
 "http://society6.2ch.net/koumei/":True,
 "http://money6.2ch.net/kyousan/":True,
 "http://tmp7.2ch.net/sisou/":True,
 "http://tmp7.2ch.net/kova/":True,
 "http://money6.2ch.net/money/":True,
 "http://food8.2ch.net/food/":True,
 "http://food8.2ch.net/candy/":True,
 "http://food8.2ch.net/juice/":True,
 "http://food8.2ch.net/pot/":True,
 "http://food8.2ch.net/cook/":True,
 "http://food8.2ch.net/salt/":True,
 "http://food8.2ch.net/ramen/":True,
 "http://food8.2ch.net/nissin/":True,
 "http://food8.2ch.net/jnoodle/":True,
 "http://food8.2ch.net/sushi/":True,
 "http://food8.2ch.net/don/":True,
 "http://food8.2ch.net/curry/":True,
 "http://food8.2ch.net/bread/":True,
 "http://food8.2ch.net/pasta/":True,
 "http://food8.2ch.net/kbbq/":True,
 "http://food8.2ch.net/konamono/":True,
 "http://food8.2ch.net/toba/":True,
 "http://food8.2ch.net/gurume/":True,
 "http://food8.2ch.net/famires/":True,
 "http://food8.2ch.net/jfoods/":True,
 "http://food8.2ch.net/bento/":True,
 "http://food8.2ch.net/sake/":True,
 "http://food8.2ch.net/wine/":True,
 "http://food8.2ch.net/drunk/":True,
 "http://food8.2ch.net/recipe/":True,
 "http://food8.2ch.net/patissier/":True,
 "http://food8.2ch.net/supplement/":True,
 "http://life9.2ch.net/lifesaloon/":True,
 "http://changi.2ch.net/kankon/":True,
 "http://life9.2ch.net/okiraku/":True,
 "http://life9.2ch.net/homealone/":True,
 "http://life9.2ch.net/countrylife/":True,
 "http://life9.2ch.net/debt/":True,
 "http://life9.2ch.net/inpatient/":True,
 "http://life9.2ch.net/sportsclub/":True,
 "http://hobby11.2ch.net/bath/":True,
 "http://life9.2ch.net/anniversary/":True,
 "http://life9.2ch.net/sousai/":True,
 "http://life9.2ch.net/baby/":True,
 "http://life9.2ch.net/kagu/":True,
 "http://hobby11.2ch.net/diy/":True,
 "http://money6.2ch.net/shop/":True,
 "http://life9.2ch.net/trend/":True,
 "http://etc7.2ch.net/ticketplus/":True,
 "http://life9.2ch.net/model/":True,
 "http://mamono.2ch.net/fashion/":True,
 "http://life9.2ch.net/shoes/":True,
 "http://life9.2ch.net/female/":True,
 "http://changi.2ch.net/diet/":True,
 "http://life9.2ch.net/seikei/":True,
 "http://life9.2ch.net/shapeup/":True,
 "http://life9.2ch.net/world/":True,
 "http://life9.2ch.net/northa/":True,
 "http://life9.2ch.net/credit/":True,
 "http://hobby11.2ch.net/point/":True,
 "http://bubble6.2ch.net/cafe30/":True,
 "http://bubble6.2ch.net/cafe40/":True,
 "http://bubble6.2ch.net/cafe50/":True,
 "http://life9.2ch.net/live/":True,
 "http://life9.2ch.net/souji/":True,
 "http://life9.2ch.net/goki/":True,
 "http://money6.2ch.net/kechi2/":True,
 "http://life9.2ch.net/chance/":True,
 "http://life9.2ch.net/cigaret/":True,
 "http://life9.2ch.net/megane/":True,
 "http://life9.2ch.net/yuusen/":True,
 "http://life9.2ch.net/conv/":True,
 "http://life9.2ch.net/sale/":True,
 "http://hobby11.2ch.net/stationery/":True,
 "http://life9.2ch.net/class/":True,
 "http://mamono.2ch.net/shar/":True,
 "http://anime3.2ch.net/x3/":True,
 "http://etc7.2ch.net/denpa/":True,
 "http://hobby11.2ch.net/owarai/":True,
 "http://anime3.2ch.net/2chbook/":True,
 "http://changi.2ch.net/uwasa/":True,
 "http://etc7.2ch.net/charaneta/":True,
 "http://etc7.2ch.net/charaneta2/":True,
 "http://etc7.2ch.net/mascot/":True,
 "http://bubble6.2ch.net/senji/":True,
 "http://changi.2ch.net/lovesaloon/":True,
 "http://love6.2ch.net/ex/":True,
 "http://life9.2ch.net/x1/":True,
 "http://changi.2ch.net/gaysaloon/":True,
 "http://human7.2ch.net/nohodame/":True,
 "http://human7.2ch.net/dame/":True,
 "http://life9.2ch.net/loser/":True,
 "http://mamono.2ch.net/hikky/":True,
 "http://changi.2ch.net/mental/":True,
 "http://bubble6.2ch.net/single/":True,
 "http://human7.2ch.net/wom/":True,
 "http://human7.2ch.net/sfe/":True,
 "http://human7.2ch.net/wmotenai/":True,
 "http://changi.2ch.net/ms/":True,
 "http://changi.2ch.net/male/":True,
 "http://bubble6.2ch.net/motetai/":True,
 "http://changi.2ch.net/motenai/":True,
 "http://life9.2ch.net/alone/":True,
 "http://human7.2ch.net/tomorrow/":True,
 "http://money6.2ch.net/employee/":True,
 "http://ex24.2ch.net/campus/":True,
 "http://changi.2ch.net/student/":True,
 "http://anime3.2ch.net/otaku/":True,
 "http://bubble6.2ch.net/nendai/":True,
 "http://bubble6.2ch.net/sepia/":True,
 "http://game14.2ch.net/gag/":True,
 "http://game14.2ch.net/575/":True,
 "http://game14.2ch.net/tanka/":True,
 "http://changi.2ch.net/4649/":True,
 "http://headline.2ch.net/bbylive/":True,
 "http://epg.2ch.net/tv2chwiki/":True,
 "http://live24.2ch.net/livesaturn/":True,
 "http://live24.2ch.net/livevenus/":True,
 "http://live23.2ch.net/livejupiter/":True,
 "http://live27.2ch.net/liveuranus/":True,
 "http://live24.2ch.net/endless/":True,
 "http://live24.2ch.net/weekly/":True,
 "http://live24.2ch.net/livewkwest/":True,
 "http://live23.2ch.net/livenhk/":True,
 "http://live23.2ch.net/liveetv/":True,
 "http://live23.2ch.net/liventv/":True,
 "http://live23.2ch.net/livetbs/":True,
 "http://live23.2ch.net/livecx/":True,
 "http://live23.2ch.net/liveanb/":True,
 "http://live23.2ch.net/livetx/":True,
 "http://live24.2ch.net/livebs/":True,
 "http://live24.2ch.net/livewowow/":True,
 "http://live24.2ch.net/liveskyp/":True,
 "http://live24.2ch.net/liveradio/":True,
 "http://live24.2ch.net/dome/":True,
 "http://live24.2ch.net/livebase/":True,
 "http://live24.2ch.net/livefoot/":True,
 "http://live24.2ch.net/oonna/":True,
 "http://live24.2ch.net/ootoko/":True,
 "http://live24.2ch.net/dancesite/":True,
 "http://live24.2ch.net/festival/":True,
 "http://news24.2ch.net/liveplus/":True,
 "http://mamono.2ch.net/livemarket1/":True,
 "http://changi.2ch.net/livemarket2/":True,
 "http://school7.2ch.net/edu/":True,
 "http://changi.2ch.net/jsaloon/":True,
 "http://namidame.2ch.net/kouri/":True,
 "http://school7.2ch.net/juku/":True,
 "http://school7.2ch.net/ojyuken/":True,
 "http://school7.2ch.net/senmon/":True,
 "http://school7.2ch.net/design/":True,
 "http://school7.2ch.net/musicology/":True,
 "http://school7.2ch.net/govexam/":True,
 "http://hobby11.2ch.net/hobby/":True,
 "http://hobby11.2ch.net/magic/":True,
 "http://hobby11.2ch.net/card/":True,
 "http://hobby11.2ch.net/puzzle/":True,
 "http://hobby11.2ch.net/craft/":True,
 "http://hobby11.2ch.net/toy/":True,
 "http://hobby11.2ch.net/zoid/":True,
 "http://hobby11.2ch.net/watch/":True,
 "http://hobby11.2ch.net/smoking/":True,
 "http://hobby11.2ch.net/knife/":True,
 "http://hobby11.2ch.net/doll/":True,
 "http://hobby11.2ch.net/engei/":True,
 "http://hobby11.2ch.net/dog/":True,
 "http://hobby11.2ch.net/pet/":True,
 "http://hobby11.2ch.net/aquarium/":True,
 "http://hobby11.2ch.net/goldenfish/":True,
 "http://hobby11.2ch.net/insect/":True,
 "http://tmp7.2ch.net/cat/":True,
 "http://hobby11.2ch.net/bike/":True,
 "http://hobby11.2ch.net/car/":True,
 "http://hobby11.2ch.net/kcar/":True,
 "http://hobby11.2ch.net/auto/":True,
 "http://hobby11.2ch.net/usedcar/":True,
 "http://hobby11.2ch.net/truck/":True,
 "http://hobby11.2ch.net/army/":True,
 "http://hobby11.2ch.net/radio/":True,
 "http://hobby11.2ch.net/train/":True,
 "http://hobby11.2ch.net/rail/":True,
 "http://hobby11.2ch.net/ice/":True,
 "http://hobby11.2ch.net/gage/":True,
 "http://hobby11.2ch.net/bus/":True,
 "http://hobby11.2ch.net/airline/":True,
 "http://hobby11.2ch.net/mokei/":True,
 "http://hobby11.2ch.net/radiocontrol/":True,
 "http://hobby11.2ch.net/gun/":True,
 "http://hobby11.2ch.net/fireworks/":True,
 "http://ex24.2ch.net/warhis/":True,
 "http://hobby11.2ch.net/chinahero/":True,
 "http://hobby11.2ch.net/sengoku/":True,
 "http://etc7.2ch.net/nanminhis/":True,
 "http://hobby11.2ch.net/dance/":True,
 "http://hobby11.2ch.net/bird/":True,
 "http://hobby11.2ch.net/collect/":True,
 "http://hobby11.2ch.net/photo/":True,
 "http://sports11.2ch.net/sposaloon/":True,
 "http://sports11.2ch.net/sports/":True,
 "http://sports11.2ch.net/rsports/":True,
 "http://sports11.2ch.net/stadium/":True,
 "http://sports11.2ch.net/athletics/":True,
 "http://sports11.2ch.net/gymnastics/":True,
 "http://sports11.2ch.net/muscle/":True,
 "http://sports11.2ch.net/noroma/":True,
 "http://sports11.2ch.net/wsports/":True,
 "http://sports11.2ch.net/ski/":True,
 "http://yutori.2ch.net/skate/":True,
 "http://sports11.2ch.net/swim/":True,
 "http://sports11.2ch.net/msports/":True,
 "http://sports11.2ch.net/boat/":True,
 "http://sports11.2ch.net/birdman/":True,
 "http://sports11.2ch.net/fish/":True,
 "http://sports11.2ch.net/bass/":True,
 "http://sports11.2ch.net/bicycle/":True,
 "http://sports11.2ch.net/equestrian/":True,
 "http://ex24.2ch.net/f1/":True,
 "http://sports11.2ch.net/olympic/":True,
 "http://sports11.2ch.net/bullseye/":True,
 "http://sports11.2ch.net/parksports/":True,
 "http://sports11.2ch.net/amespo/":True,
 "http://sports11.2ch.net/cheerleading/":True,
 "http://sports11.2ch.net/xsports/":True,
 "http://ex24.2ch.net/base/":True,
 "http://sports11.2ch.net/npb/":True,
 "http://bubble6.2ch.net/meikyu/":True,
 "http://sports11.2ch.net/mlb/":True,
 "http://sports11.2ch.net/hsb/":True,
 "http://sports11.2ch.net/kyozin/":True,
 "http://ex24.2ch.net/soccer/":True,
 "http://sports11.2ch.net/eleven/":True,
 "http://sports2.2ch.net/wc/":True,
 "http://sports11.2ch.net/football/":True,
 "http://sports11.2ch.net/basket/":True,
 "http://sports11.2ch.net/tennis/":True,
 "http://sports11.2ch.net/volley/":True,
 "http://sports11.2ch.net/ovalball/":True,
 "http://sports11.2ch.net/pingpong/":True,
 "http://sports11.2ch.net/gutter/":True,
 "http://sports11.2ch.net/golf/":True,
 "http://sports11.2ch.net/billiards/":True,
 "http://ex24.2ch.net/k1/":True,
 "http://sports11.2ch.net/wres/":True,
 "http://sports11.2ch.net/budou/":True,
 "http://sports11.2ch.net/boxing/":True,
 "http://sports11.2ch.net/sumou/":True,
 "http://sports11.2ch.net/jyudo/":True,
 "http://love6.2ch.net/oversea/":True,
 "http://society6.2ch.net/21oversea/":True,
 "http://love6.2ch.net/travel/":True,
 "http://love6.2ch.net/hotel/":True,
 "http://food8.2ch.net/localfoods/":True,
 "http://love6.2ch.net/tropical/":True,
 "http://love6.2ch.net/onsen/":True,
 "http://love6.2ch.net/park/":True,
 "http://love6.2ch.net/zoo/":True,
 "http://love6.2ch.net/museum/":True,
 "http://love6.2ch.net/out/":True,
 "http://tv11.2ch.net/tvsaloon/":True,
 "http://sports2.2ch.net/kouhaku/":True,
 "http://mamono.2ch.net/tv/":True,
 "http://bubble6.2ch.net/natsutv/":True,
 "http://mamono.2ch.net/tvd/":True,
 "http://live27.2ch.net/nhkdrama/":True,
 "http://bubble6.2ch.net/natsudora/":True,
 "http://tv11.2ch.net/kin/":True,
 "http://tv11.2ch.net/am/":True,
 "http://bubble6.2ch.net/rradio/":True,
 "http://tv11.2ch.net/tv2/":True,
 "http://tv11.2ch.net/cs/":True,
 "http://tv11.2ch.net/skyp/":True,
 "http://tv11.2ch.net/bs/":True,
 "http://tv11.2ch.net/nhk/":True,
 "http://tv11.2ch.net/cm/":True,
 "http://tv11.2ch.net/geino/":True,
 "http://tv11.2ch.net/celebrity/":True,
 "http://tv11.2ch.net/kyon2/":True,
 "http://tv11.2ch.net/actor/":True,
 "http://tv11.2ch.net/actress/":True,
 "http://tv11.2ch.net/geinoj/":True,
 "http://changi.2ch.net/geinin/":True,
 "http://ex24.2ch.net/ana/":True,
 "http://tv11.2ch.net/ami/":True,
 "http://tv11.2ch.net/apple/":True,
 "http://tv11.2ch.net/ainotane/":True,
 "http://tv11.2ch.net/zurui/":True,
 "http://music8.2ch.net/mendol/":True,
 "http://changi.2ch.net/idol/":True,
 "http://changi.2ch.net/akb/":True,
 "http://tv11.2ch.net/jan/":True,
 "http://tv11.2ch.net/smap/":True,
 "http://tv11.2ch.net/jr/":True,
 "http://tv11.2ch.net/jr2/":True,
 "http://money6.2ch.net/mj/":True,
 "http://money6.2ch.net/pachi/":True,
 "http://money6.2ch.net/pachij/":True,
 "http://money6.2ch.net/pachik/":True,
 "http://money6.2ch.net/slot/":True,
 "http://money6.2ch.net/slotj/":True,
 "http://money6.2ch.net/slotk/":True,
 "http://mamono.2ch.net/keiba/":True,
 "http://hobby11.2ch.net/uma/":True,
 "http://money6.2ch.net/keirin/":True,
 "http://money6.2ch.net/kyotei/":True,
 "http://money6.2ch.net/autorace/":True,
 "http://money6.2ch.net/gamble/":True,
 "http://money6.2ch.net/loto/":True,
 "http://game13.2ch.net/gsaloon/":True,
 "http://news24.2ch.net/gamenews/":True,
 "http://game13.2ch.net/gameover/":True,
 "http://game13.2ch.net/goveract/":True,
 "http://game13.2ch.net/goverrpg/":True,
 "http://game14.2ch.net/gamerpg/":True,
 "http://game13.2ch.net/ff/":True,
 "http://game14.2ch.net/gamesrpg/":True,
 "http://game13.2ch.net/gamerobo/":True,
 "http://game14.2ch.net/gal/":True,
 "http://game14.2ch.net/gboy/":True,
 "http://game14.2ch.net/ggirl/":True,
 "http://game13.2ch.net/gamespo/":True,
 "http://game13.2ch.net/gamehis/":True,
 "http://game13.2ch.net/otoge/":True,
 "http://game13.2ch.net/gamefight/":True,
 "http://game13.2ch.net/gamestg/":True,
 "http://game14.2ch.net/gamef/":True,
 "http://game14.2ch.net/fly/":True,
 "http://game13.2ch.net/famicom/":True,
 "http://game14.2ch.net/retro/":True,
 "http://game14.2ch.net/retro2/":True,
 "http://game14.2ch.net/game90/":True,
 "http://game13.2ch.net/arc/":True,
 "http://game13.2ch.net/amusement/":True,
 "http://game13.2ch.net/gecen/":True,
 "http://game13.2ch.net/game/":True,
 "http://game13.2ch.net/gameama/":True,
 "http://game14.2ch.net/gameswf/":True,
 "http://game14.2ch.net/cgame/":True,
 "http://game14.2ch.net/tcg/":True,
 "http://game14.2ch.net/bgame/":True,
 "http://game14.2ch.net/gamestones/":True,
 "http://game14.2ch.net/quiz/":True,
 "http://namidame.2ch.net/ghard/":True,
 "http://game14.2ch.net/gameurawaza/":True,
 "http://game13.2ch.net/gamechara/":True,
 "http://game14.2ch.net/gamemusic/":True,
 "http://game13.2ch.net/handygame/":True,
 "http://game14.2ch.net/handygover/":True,
 "http://game14.2ch.net/handygrpg/":True,
 "http://game13.2ch.net/poke/":True,
 "http://game13.2ch.net/wifi/":True,
 "http://game14.2ch.net/rhandyg/":True,
 "http://game13.2ch.net/pokechara/":True,
 "http://live27.2ch.net/mmonews/":True,
 "http://live27.2ch.net/mmoqa/":True,
 "http://changi.2ch.net/ogame/":True,
 "http://ex24.2ch.net/ogame2/":True,
 "http://changi.2ch.net/ogame3/":True,
 "http://game13.2ch.net/mmosaloon/":True,
 "http://game13.2ch.net/netgame/":True,
 "http://game13.2ch.net/mmo/":True,
 "http://game13.2ch.net/mmominor/":True,
 "http://anime3.2ch.net/comicnews/":True,
 "http://changi.2ch.net/asaloon/":True,
 "http://changi.2ch.net/anime4vip/":True,
 "http://changi.2ch.net/anime/":True,
 "http://changi.2ch.net/anime2/":True,
 "http://anime3.2ch.net/anime3/":True,
 "http://anime3.2ch.net/ranime/":True,
 "http://anime3.2ch.net/ranimeh/":True,
 "http://anime3.2ch.net/animovie/":True,
 "http://anime3.2ch.net/anichara/":True,
 "http://changi.2ch.net/anichara2/":True,
 "http://anime3.2ch.net/cosp/":True,
 "http://anime3.2ch.net/voice/":True,
 "http://ex24.2ch.net/voiceactor/":True,
 "http://anime3.2ch.net/doujin/":True,
 "http://sports2.2ch.net/comiket/":True,
 "http://changi.2ch.net/csaloon/":True,
 "http://changi.2ch.net/comic/":True,
 "http://anime3.2ch.net/rcomic/":True,
 "http://anime3.2ch.net/ymag/":True,
 "http://ex24.2ch.net/wcomic/":True,
 "http://anime3.2ch.net/gcomic/":True,
 "http://anime3.2ch.net/4koma/":True,
 "http://anime3.2ch.net/cchara/":True,
 "http://anime3.2ch.net/sakura/":True,
 "http://anime3.2ch.net/eva/":True,
 "http://anime3.2ch.net/cartoon/":True,
 "http://anime3.2ch.net/iga/":True,
 "http://love6.2ch.net/bookall/":True,
 "http://love6.2ch.net/magazin/":True,
 "http://love6.2ch.net/mystery/":True,
 "http://love6.2ch.net/sf/":True,
 "http://love6.2ch.net/zassi/":True,
 "http://love6.2ch.net/books/":True,
 "http://love6.2ch.net/ehon/":True,
 "http://love6.2ch.net/juvenile/":True,
 "http://love6.2ch.net/illustrator/":True,
 "http://music8.2ch.net/musicnews/":True,
 "http://music8.2ch.net/msaloon/":True,
 "http://music8.2ch.net/mjsaloon/":True,
 "http://music8.2ch.net/musicj/":True,
 "http://music8.2ch.net/musicjm/":True,
 "http://music8.2ch.net/musicjf/":True,
 "http://music8.2ch.net/musicjg/":True,
 "http://bubble6.2ch.net/natsumeloj/":True,
 "http://music8.2ch.net/enka/":True,
 "http://music8.2ch.net/mesaloon/":True,
 "http://music8.2ch.net/musice/":True,
 "http://bubble6.2ch.net/natsumeloe/":True,
 "http://music8.2ch.net/music/":True,
 "http://bubble6.2ch.net/beatles/":True,
 "http://music8.2ch.net/visual/":True,
 "http://music8.2ch.net/visualb/":True,
 "http://music8.2ch.net/dj/":True,
 "http://music8.2ch.net/disco/":True,
 "http://music8.2ch.net/randb/":True,
 "http://music8.2ch.net/punk/":True,
 "http://music8.2ch.net/hrhm/":True,
 "http://music8.2ch.net/hiphop/":True,
 "http://music8.2ch.net/techno/":True,
 "http://music8.2ch.net/progre/":True,
 "http://bubble6.2ch.net/healmusic/":True,
 "http://music8.2ch.net/wmusic/":True,
 "http://music8.2ch.net/classic/":True,
 "http://bubble6.2ch.net/fusion/":True,
 "http://music8.2ch.net/classical/":True,
 "http://music8.2ch.net/contemporary/":True,
 "http://music8.2ch.net/nika/":True,
 "http://music8.2ch.net/suisou/":True,
 "http://bubble6.2ch.net/chorus/":True,
 "http://music8.2ch.net/doyo/":True,
 "http://anime3.2ch.net/asong/":True,
 "http://bubble6.2ch.net/soundtrack/":True,
 "http://music8.2ch.net/karaok/":True,
 "http://music8.2ch.net/legend/":True,
 "http://music8.2ch.net/minor/":True,
 "http://bubble6.2ch.net/band/":True,
 "http://music8.2ch.net/compose/":True,
 "http://bubble6.2ch.net/piano/":True,
 "http://life9.2ch.net/healing/":True,
 "http://life9.2ch.net/jinsei/":True,
 "http://life9.2ch.net/psy/":True,
 "http://life9.2ch.net/body/":True,
 "http://human7.2ch.net/handicap/":True,
 "http://etc7.2ch.net/infection/":True,
 "http://love6.2ch.net/hiv/":True,
 "http://life9.2ch.net/atopi/":True,
 "http://life9.2ch.net/allergy/":True,
 "http://life9.2ch.net/hage/":True,
 "http://love6.2ch.net/pure/":True,
 "http://love6.2ch.net/furin/":True,
 "http://love6.2ch.net/gay/":True,
 "http://life9.2ch.net/utu/":True,
 "http://love6.2ch.net/break/":True,
 "http://ex24.2ch.net/pc2nanmin/":True,
 "http://pc11.2ch.net/pcnews/":True,
 "http://pc11.2ch.net/win/":True,
 "http://pc11.2ch.net/jobs/":True,
 "http://pc11.2ch.net/mac/":True,
 "http://pc11.2ch.net/os/":True,
 "http://pc11.2ch.net/desktop/":True,
 "http://pc11.2ch.net/pc/":True,
 "http://pc11.2ch.net/notepc/":True,
 "http://pc11.2ch.net/jisaku/":True,
 "http://pc11.2ch.net/printer/":True,
 "http://pc11.2ch.net/hard/":True,
 "http://pc11.2ch.net/cdr/":True,
 "http://pc11.2ch.net/software/":True,
 "http://pc11.2ch.net/mobile/":True,
 "http://pc11.2ch.net/bsoft/":True,
 "http://pc11.2ch.net/unix/":True,
 "http://pc11.2ch.net/db/":True,
 "http://pc11.2ch.net/linux/":True,
 "http://pc11.2ch.net/prog/":True,
 "http://pc11.2ch.net/tech/":True,
 "http://pc11.2ch.net/cg/":True,
 "http://pc11.2ch.net/dtm/":True,
 "http://pc11.2ch.net/avi/":True,
 "http://pc11.2ch.net/swf/":True,
 "http://pc11.2ch.net/gamedev/":True,
 "http://bubble6.2ch.net/i4004/":True,
 "http://pc11.2ch.net/internet/":True,
 "http://changi.2ch.net/download/":True,
 "http://pc11.2ch.net/hp/":True,
 "http://pc11.2ch.net/affiliate/":True,
 "http://pc11.2ch.net/hosting/":True,
 "http://pc11.2ch.net/mysv/":True,
 "http://pc11.2ch.net/php/":True,
 "http://pc11.2ch.net/hack/":True,
 "http://pc11.2ch.net/sec/":True,
 "http://pc11.2ch.net/network/":True,
 "http://pc11.2ch.net/friend/":True,
 "http://pc11.2ch.net/isp/":True,
 "http://pc11.2ch.net/netspot/":True,
 "http://pc11.2ch.net/nifty/":True,
 "http://pc11.2ch.net/mmag/":True,
 "http://changi.2ch.net/nanmin/":True,
 "http://ex24.2ch.net/ad/":True,
 "http://pc11.2ch.net/esite/":True,
 "http://pc11.2ch.net/streaming/":True,
 "http://pc11.2ch.net/mstreaming/":True,
 "http://music8.2ch.net/mdis/":True,
 "http://pc11.2ch.net/blog/":True,
 "http://pc11.2ch.net/sns/":True,
 "http://pc11.2ch.net/net/":True,
 "http://pc11.2ch.net/yahoo/":True,
 "http://pc11.2ch.net/nntp/":True,
 "http://etc7.2ch.net/bobby/":True,
 "http://tmp7.2ch.net/lobby/":True,
 "http://etc7.2ch.net/maru/":True,
 "http://changi.2ch.net/mog2/":True,
 "http://bubble6.2ch.net/mukashi/":True,
 "http://tmp7.2ch.net/kitchen/":True,
 "http://tmp7.2ch.net/tubo/":True,
 "http://tmp7.2ch.net/joke/":True,
 "http://society6.2ch.net/shugi/":True,
 "http://tmp7.2ch.net/rights/":True,
 "http://ex24.2ch.net/accuse/":True,
 "http://changi.2ch.net/morningcoffee/":True,
 "http://ex24.2ch.net/ranking/":True,
 "http://etc7.2ch.net/siberia/":True,
 "http://yutori.2ch.net/news4vip/":True,
 "http://yutori.2ch.net/news4viptasu/":True,
 "http://namidame.2ch.net/poverty/":True,
 "http://yutori.2ch.net/heaven4vip/":True,
 "http://yutori.2ch.net/neet4vip/":True,
 "http://qb5.2ch.net/saku/":True,
 "http://ex24.2ch.net/accuse/":True,
 "http://headline.bbspink.com/bbypink/":True,
 "http://babiru.bbspink.com/hnews/":True,
 "http://babiru.bbspink.com/pinkqa/":True,
 "http://yomi.bbspink.com/sureh/":True,
 "http://babiru.bbspink.com/erolive/":True,
 "http://venus.bbspink.com/hneta/":True,
 "http://yomi.bbspink.com/pinkcafe/":True,
 "http://set.bbspink.com/eromog2/":True,
 "http://set.bbspink.com/ogefin/":True,
 "http://babiru.bbspink.com/pinknanmin/":True,
 "http://set.bbspink.com/erobbs/":True,
 "http://babiru.bbspink.com/housekeeping/":True,
 "http://venus.bbspink.com/ccc/":True,
 "http://babiru.bbspink.com/21oversea2/":True,
 "http://qiufen.bbspink.com/hgame/":True,
 "http://qiufen.bbspink.com/hgame2/":True,
 "http://set.bbspink.com/erog/":True,
 "http://set.bbspink.com/leaf/":True,
 "http://set.bbspink.com/adultsite/":True,
 "http://yomi.bbspink.com/webmaster/":True,
 "http://set.bbspink.com/avideo/":True,
 "http://set.bbspink.com/avideo2/":True,
 "http://babiru.bbspink.com/nude/":True,
 "http://yomi.bbspink.com/eroanime/":True,
 "http://set.bbspink.com/erocomic/":True,
 "http://yomi.bbspink.com/erodoujin/":True,
 "http://set.bbspink.com/natuero/":True,
 "http://yomi.bbspink.com/kgirls/":True,
 "http://set.bbspink.com/erocosp/":True,
 "http://set.bbspink.com/eroacademy/":True,
 "http://set.bbspink.com/mcheck/":True,
 "http://babiru.bbspink.com/couple/":True,
 "http://yomi.bbspink.com/kageki/":True,
 "http://babiru.bbspink.com/kageki2/":True,
 "http://babiru.bbspink.com/onatech/":True,
 "http://babiru.bbspink.com/loveho/":True,
 "http://babiru.bbspink.com/adultgoods/":True,
 "http://babiru.bbspink.com/adultaccessory/":True,
 "http://set.bbspink.com/sm/":True,
 "http://set.bbspink.com/feti/":True,
 "http://babiru.bbspink.com/mature/":True,
 "http://yomi.bbspink.com/okama/":True,
 "http://babiru.bbspink.com/gaypink/":True,
 "http://babiru.bbspink.com/lesbian/":True,
 "http://babiru.bbspink.com/eroaa/":True,
 "http://babiru.bbspink.com/erochara/":True,
 "http://yomi.bbspink.com/erochara2/":True,
 "http://yomi.bbspink.com/801/":True,
 "http://set.bbspink.com/erocg/":True,
 "http://yomi.bbspink.com/eroparo/":True,
 "http://venus.bbspink.com/ascii/":True,
 "http://yomi.bbspink.com/ascii2d/":True,
 "http://qiufen.bbspink.com/ascii2kana/":True,
 "http://set.bbspink.com/girls/":True,
 "http://set.bbspink.com/sportgirls/":True,
 "http://qiufen.bbspink.com/club/":True,
 "http://qiufen.bbspink.com/pub/":True,
 "http://babiru.bbspink.com/host/":True,
 "http://qiufen.bbspink.com/nuki/":True,
 "http://qiufen.bbspink.com/soap/":True,
 "http://yomi.bbspink.com/neet4pink/":True,
 "http://venus.bbspink.com/cherryboy/":True,
 "http://venus.bbspink.com/megami/":True
  }

if __name__ == '__main__':
  main()
