import os
import falcon
import uuid as _uuid
import json
import sys

import multiprocessing
import subprocess
import shlex
from multiprocessing.pool import ThreadPool
pool = ThreadPool(processes=int(os.getenv('PROCESSES', multiprocessing.cpu_count())))

def archive(url, quality, params={}):
    cmd = f"'{sys.executable}' ./ytarchive.py"
    for k, v in params.items():
        if type(v) == bool:
            cmd += f" {k}"
        else:
            cmd += f" {k} '{v}'"
    cmd += f" {url} {quality}"
    p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    
    if type(out) == bytes:
        out = out.decode(sys.stdout.encoding)
    if type(err) == bytes:
        err = err.decode(sys.stdout.encoding)
        
    return (out, err)

statuses = {}

def get_id():
    return _uuid.uuid4().hex

def add_task(uid, task):
    global statuses
    statuses[uid] = task

class Status:
    def on_get(self, req, resp):
        global statuses

        resp.media = {}

        for uid in statuses:
            t = statuses[uid]
            if t.ready():
                try:
                    out, err = t.get()
                    resp.media[uid] = {
                        "status": 1 if not len(err) else 2,
                        "output": {"out": out, "err": err}
                    }
                except Exception as err:
                    resp.media[uid] = {
                        "status": 2,
                        "output": {"out": None, "err": str(err)}
                    }
            else:
                resp.media[uid] = False

        resp.status = falcon.HTTP_200
    def on_delete(self, req, resp):
        global statuses

        uid = req.media.get('id')
        statuses.pop(uid, None)

        resp.status = falcon.HTTP_200

class Record:
    def on_post(self, req, resp):
        global statuses
        global pool

        url = req.media.get('url')
        quality = req.media.get('quality')
        params = req.media.get('params')

        uid = f"{url} - {get_id()}"
        t = pool.apply_async(archive, (url, quality, params))
        add_task(uid, t)

        resp.media = {'id': uid}
        resp.status = falcon.HTTP_200

class Website:
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = "text/html"
        with open("./index.html", "rb") as f:
            resp.body = f.read()

class CookieAvailable:
    def on_get(self, req, resp):
        if os.path.isfile("./cookie.txt"):
            resp.status = falcon.HTTP_302
        else:
            resp.status = falcon.HTTP_404

api = falcon.API()
api.add_route('/status', Status())
api.add_route('/record', Record())
api.add_route('/', Website())
api.add_route('/cookie', CookieAvailable())
