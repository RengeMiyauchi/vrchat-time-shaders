#!/usr/bin/env python3

import io
import requests

from pendulum import timezone
from datetime import datetime
from timezonefinder import TimezoneFinder

from PIL import Image, ImageDraw
from flask_caching import Cache
from werkzeug.wsgi import FileWrapper
from flask import Flask, Response, request, redirect

config = {
    'CACHE_TYPE': 'simple',
    "CACHE_DEFAULT_TIMEOUT": 60*60*24*7
}

tf = TimezoneFinder()
app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)

@app.route('/')
def index():
    return ""

@app.route('/vrctime_test')
def vrc_time_test():
    ip = request.headers['x-appengine-user-ip']
    #ip = request.headers['X-Real-IP']
    ctime = get_current_time(ip)
    readable = ctime.strftime("%m/%d/%Y, %H:%M:%S")

    return "ip: {0}, time: {1}".format(ip, readable)

@app.route('/vrctime')
def vrc_time():
    ip = request.headers['x-appengine-user-ip']
    #ip = request.headers['X-Real-IP']
    ctime = get_current_time(ip)
    img = generate_image(ctime)

    f = FileWrapper(img)
    return Response(f, mimetype="image/PNG", direct_passthrough=True)

@cache.memoize(timeout=60*60*24*7)
def get_geo_info(ip):
    URL = "http://ip-api.com/json/{0}?fields=lat,lon".format(ip)
    result = requests.get(url = URL).json()
    if "lat" not in result:
        raise Exception("don't cache")
    return result

def get_current_time(ip):
    try:
        location = get_geo_info(ip)
    except:
        ctime = datetime.now().astimezone(timezone("Asia/Tokyo"))
    else:
        timezone_str = tf.timezone_at(lng=location["lon"], lat=location["lat"])
        tz = timezone(timezone_str)
        now = datetime.now()
        ctime = now.astimezone(tz)
    return ctime

def generate_image(now):

    CELL = 8

    im = Image.new("RGB", (CELL*8, CELL*8), (0,0,0))
    dr = ImageDraw.Draw(im)

    def drawCell(x, y, v):
        x0 = x*CELL
        y0 = y*CELL
        x1 = (x+1)*CELL
        y1 = (y+1)*CELL
        r = 255 if ((v&(1<<0)) != 0) else 0
        g = 255 if ((v&(1<<1)) != 0) else 0
        b = 255 if ((v&(1<<2)) != 0) else 0
        dr.rectangle([x0, y0, x1, y1], fill=(r, g, b))

    year   = now.year-1900
    month  = now.month-1
    day    = now.day
    hour   = now.hour
    minute = now.minute
    second = now.second
    ms     = int(now.microsecond/1000*64/1000)
    weekday = now.isoweekday()%7
    moonAge = (((now.year-2009)%19)*11+(now.month+1)+(now.day+1)) % 30

    drawCell(0, 0, hour&0b111)
    drawCell(1, 0, hour>>3)
    drawCell(2, 0, minute&0b111)
    drawCell(3, 0, minute>>3)
    drawCell(4, 0, second&0b111)
    drawCell(5, 0, second>>3)
    drawCell(6, 0, ms&0b111)
    drawCell(7, 0, ms>>3)

    drawCell(0, 1, year&0b111)
    drawCell(1, 1, (year>>3)&0b111)
    drawCell(2, 1, (year>>6)&0b111)
    drawCell(3, 1, month&0b111)
    drawCell(4, 1, month>>3)
    drawCell(5, 1, day&0b111)
    drawCell(6, 1, day>>3)
    drawCell(7, 1, weekday)

    drawCell(0, 2, moonAge&0b111)
    drawCell(1, 2, moonAge>>3)

    file_object = io.BytesIO()
    im.save(file_object, "PNG")
    file_object.seek(0)

    return file_object

if __name__ == "__main__":

    app.run(host='127.0.0.1', port=8080, debug=True)
