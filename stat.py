import requests
import threading
import queue
import itertools
import time
import os

API = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
WEBHOOK = os.getenv("WEBHOOK_URL")

THREADS = 1
COOLDOWN = 1.5
MAX_RETRIES = 5

# load usernames
with open("names.txt", "r", encoding="utf8") as f:
    names = [x.strip() for x in f if x.strip()]

# load proxies
try:
    with open("proxies.txt", "r") as f:
        proxies = [p.strip() for p in f if p.strip()]
except:
    proxies = []

proxy_cycle = itertools.cycle(proxies) if proxies else None

use_proxies = False
current_proxy = None

request_lock = threading.Lock()
cooldown_lock = threading.Lock()

q = queue.Queue()
for name in names:
    q.put(name)


def send_webhook(name):
    if not WEBHOOK:
        return

    try:
        data = {
            "content": "@everyone",
            "allowed_mentions": {"parse": ["everyone"]},
            "embeds": [{
                "title": "Username Available",
                "description": f"**{name}** is available",
                "color": 5763719
            }]
        }

        requests.post(WEBHOOK, json=data, timeout=5)

    except:
        pass


def get_proxy():
    global current_proxy

    if not use_proxies or not proxy_cycle:
        return None

    current_proxy = next(proxy_cycle)

    return {
        "http": f"http://{current_proxy}",
        "https": f"http://{current_proxy}"
    }


def wait_global():
    with cooldown_lock:
        time.sleep(COOLDOWN)


def check(name):
    global use_proxies

    retries = 0

    while retries < MAX_RETRIES:

        wait_global()
        proxy = get_proxy()

        try:
            r = requests.post(
                API,
                json={"username": name},
                proxies=proxy,
                timeout=10
            )

            if r.status_code == 200:
                data = r.json()

                if data["taken"]:
                    print(f"TAKEN : {name}")
                else:
                    print(f"OPEN  : {name}")

                    with open("hits.txt", "a") as f:
                        f.write(name + "\n")

                    send_webhook(name)

                return

            elif r.status_code == 429:

                with request_lock:
                    if not use_proxies:
                        print("RATE LIMIT → switching to proxies")
                        use_proxies = True
                    else:
                        print("RATE LIMIT → rotating proxy")

                retries += 1
                time.sleep(1)
                continue

            else:
                print(f"ERROR {r.status_code} : {name}")
                return

        except Exception:
            print(f"REQUEST ERROR : {name}")
            retries += 1
            time.sleep(1)

    print(f"GAVE UP : {name}")


def worker():
    while not q.empty():
        name = q.get()
        check(name)
        q.task_done()


for _ in range(THREADS):
    threading.Thread(target=worker, daemon=True).start()

q.join()

print("Done")
