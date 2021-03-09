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

if os.path.isfile("./callbacks.py"):
    from callbacks import callbacks
else:
    callbacks = None

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
def archive(url, quality, params={}, callback_id=None, on_callback=None):
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

    if callbacks:
        if len(err):
            err += f"\n\n [INFO] Queued callback id: {callback_id}"
            yield (out, err)
            err = ''

        if on_callback:
            on_callback()

        filepath = out.split("Final file: ")[-1].rstrip()
        filepath = os.path.abspath(filepath)
        
        tmp = callbacks[callback_id](filepath)

        for key in tmp:
            _out = tmp[key]["out"]
            _err = tmp[key]["err"]

            out += f"\n{key}:\n{_out}" 
            if len(tmp[key]["err"]):
                err += f"\n{key}:\n{_err}" 
        
    yield (out, err)

statuses = {}

def get_id():
    return _uuid.uuid4().hex

def add_task(uid, task, callback=False):
    global statuses
    if uid in statuses:
        statuses[uid]["task"] = task
    else:
        if not callback:
            statuses[uid] = {"task": task}
        else:
            statuses[uid] = {"task": task, "callback": False}

class Status:
    def on_get(self, req, resp):
        global statuses

        resp.media = {}

        for uid in statuses:
            t = statuses[uid]["task"]
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
            elif ("callback" in statuses[uid]) and statuses[uid]["callback"]:
                resp.media[uid] = {
                    "status": 3
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
        global pool

        url = req.media.get('url')
        quality = req.media.get('quality')
        params = req.media.get('params')

        callback_id = req.media.get('callback') if callbacks else None
        if not len(callback_id):
            callback_id = None

        if callback_id:
            def on_callback():
                statuses[uid]["callback"] = True
        else:
            on_callback = None

        if callback_id not in callbacks:
            callback_id = None
            on_callback = None

        uid = f"{url} - {get_id()}"
        archive_gen = archive(url, quality, params, callback_id, on_callback)
        t = pool.apply_async(lambda: next(archive_gen))
        add_task(uid, t, callback=True)
        statuses[uid]["generator"] = archive_gen

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

class Reboot:
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        sys.exit(0)

class Callbacks:
    def on_get(self, req, resp):
        if callbacks:
            resp.media = [x for x in callbacks]
            resp.status = falcon.HTTP_200
        else:
            resp.status = falcon.HTTP_404

class Callback:
    def on_get(self, req, resp):
        uid = req.get_param('id')
        t = pool.apply_async(lambda: next(statuses[uid]["generator"]))
        add_task(uid, t)

        resp.status = falcon.HTTP_200
    
api = falcon.API()
api.add_route('/status', Status())
api.add_route('/record', Record())
api.add_route('/cookie', CookieAvailable())
api.add_route('/callbacks', Callbacks())
api.add_route('/callback', Callback())
api.add_route('/reboot', Reboot())
api.add_route('/', Website())