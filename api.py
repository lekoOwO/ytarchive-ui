import os
import falcon
import uuid as _uuid
import json
import sys

import multiprocessing
import subprocess
import shlex
from multiprocessing.pool import ThreadPool

import urllib.request
import shutil

pool = ThreadPool(processes=int(os.getenv('PROCESSES', multiprocessing.cpu_count())))

# ----- ytarchive upgrade -----
def get_latest_ytarchive_commit():
    url = "https://api.github.com/repos/Kethsar/ytarchive/commits"
    req = urllib.request.Request(url)
    
    response = urllib.request.urlopen(req)
    encoding = response.info().get_content_charset('utf-8')
    resp_data = json.loads(response.read().decode(encoding))

    commit = resp_data[0]["sha"]

    return commit


def get_latest_ytarchive():
    url = "https://raw.githubusercontent.com/Kethsar/ytarchive/master/ytarchive.py"

    with urllib.request.urlopen(url) as response, open("./ytarchive.py", 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

    commit = get_latest_ytarchive_commit()

    with open("./ytarchive.commit", 'w') as f:
        f.write(commit)

if not os.path.isfile("./ytarchive.commit"):
    if os.path.isfile("./ytarchive.py"):
        print("[INFO] Unknown ytarchive version. Redownloading...")
        os.remove("./ytarchive.py")
    else:
        print("[INFO] ytarchive not found. Downloading...")
    get_latest_ytarchive()

else:
    if not os.path.isfile("./ytarchive.py"):
        print("[INFO] ytarchive not found. Downloading...")
        get_latest_ytarchive()
    else:
        with open("./ytarchive.commit", 'r') as f:
            print("[INFO] Checking if ytarchive is latest...")
            commit = f.read()
            if commit != get_latest_ytarchive_commit():
                print("[INFO] Upgrading ytarchive...")
                get_latest_ytarchive()
                print("[INFO] Finished.")
            else:
                print("[INFO] Using latest ytarchive!")

# ----- ytarchive upgrade END -----
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