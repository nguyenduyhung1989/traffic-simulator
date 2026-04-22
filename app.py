import atexit
import json
import os
import signal
import subprocess
import sys
import threading
from flask import Flask, render_template, request, Response, stream_with_context

app = Flask(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
MAIN_PATH   = os.path.join(os.path.dirname(__file__), 'main.py')

_proc_lock = threading.Lock()
_current_proc: subprocess.Popen | None = None


def _terminate_current():
    global _current_proc
    with _proc_lock:
        if _current_proc and _current_proc.poll() is None:
            _current_proc.terminate()
            try:
                _current_proc.wait(timeout=5)
            except Exception:
                _current_proc.kill()


def _sigterm_handler(signum, frame):
    _terminate_current()
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


atexit.register(_terminate_current)
signal.signal(signal.SIGTERM, _sigterm_handler)


def load_config() -> dict:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(updates: dict) -> None:
    cfg = load_config()

    # url_entries: [{url, views|null}, ...]
    entries = updates.get('url_entries')
    if entries is not None:
        cfg['urls'] = [e['url'] for e in entries if e.get('url', '').strip()]
        cfg['url_view_counts'] = {
            e['url']: int(e['views'])
            for e in entries
            if e.get('url', '').strip() and e.get('views') not in (None, '', 0)
        }
    elif 'urls' in updates:
        cfg['urls'] = updates['urls']

    if 'viewMin' in updates and 'viewMax' in updates:
        cfg['url_views_range'] = [updates['viewMin'], updates['viewMax']]
    if 'workers' in updates:
        cfg.setdefault('concurrency', {})['num_workers'] = updates['workers']
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)


@app.route('/')
def index():
    cfg = load_config()
    return render_template('index.html', urls=cfg.get('urls', []), config=cfg)


@app.route('/config', methods=['POST'])
def update_config():
    data = request.json or {}
    save_config(data)
    return {'ok': True}


@app.route('/stream')
def stream():
    global _current_proc

    with _proc_lock:
        if _current_proc and _current_proc.poll() is None:
            return Response("data: \"__BUSY__\"\n\n", mimetype='text/event-stream')

    def generate():
        global _current_proc
        proc = subprocess.Popen(
            [sys.executable, '-u', MAIN_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            cwd=os.path.dirname(__file__),
        )
        with _proc_lock:
            _current_proc = proc

        try:
            for line in proc.stdout:
                yield f"data: {json.dumps(line.rstrip())}\n\n"
            proc.wait()
            yield f"data: {json.dumps(f'__EXIT__{proc.returncode}')}\n\n"
        finally:
            proc.stdout.close()

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


@app.route('/stop', methods=['POST'])
def stop():
    global _current_proc
    with _proc_lock:
        if _current_proc and _current_proc.poll() is None:
            _current_proc.terminate()
            return {'ok': True}
    return {'ok': False}


if __name__ == '__main__':
    app.run(debug=True, port=7878, threaded=True)
