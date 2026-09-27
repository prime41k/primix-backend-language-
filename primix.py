#!/usr/bin/env python3
"""
Primix v1.0 — Monolithic Async Backend Runtime
Zero dependencies. Pure Python 3.8+.
"""

import sys
import json
import asyncio
import hashlib
import random
import string
import time
import sqlite3
from datetime import datetime
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional

KANJI = ['暮', 'ら', 'し', '対', '話', '霧', '雨', '桜', '言', '葉', '夢', '見', 'る', '静', 'け', 'さ', '星', '空', '海', '風', '山', '川', '花', '火', '月', '日', '時', '人', '心', '手']
OLD_WORDS = ['whither', 'goeth', 'thy', 'darkness', 'whence', 'cometh', 'light', 'shadow', 'throne', 'mist', 'falcon', 'sword', 'ancient', 'keeper', 'forge', 'behold', 'wrath', 'dawn']

class T8T:
    @staticmethod
    def _seed(key_seed: str): random.seed(key_seed)

    @staticmethod
    def mixed_encrypt(data: str, key_seed: str) -> str:
        T8T._seed(key_seed)
        raw = data.encode() if isinstance(data, str) else str(data).encode()
        result = []
        for i, _ in enumerate(raw):
            if i % 3 == 0: result.append(random.choice(KANJI))
            elif i % 3 == 1: result.append(random.choice(OLD_WORDS))
            else: result.append(''.join(random.choices(string.ascii_letters + string.digits, k=5)))
        return ''.join(result)

    @staticmethod
    def jp_encrypt(data: str, key_seed: str) -> str:
        T8T._seed(key_seed)
        return ''.join(random.choice(KANJI) for _ in str(data))

    @staticmethod
    def en_encrypt(data: str, key_seed: str) -> str:
        T8T._seed(key_seed)
        return ' '.join(random.choice(OLD_WORDS) for _ in str(data).split())

    @staticmethod
    def rnd_encrypt(data: str, key_seed: str) -> str:
        T8T._seed(key_seed)
        return ''.join(random.choices(string.ascii_letters + string.digits, k=len(str(data)) * 3))

class Storage:
    def __init__(self): self.data: Dict[str, Any] = {}
    def set(self, k: str, v: Any): self.data[k] = v
    def get(self, k: str) -> Any: return self.data.get(k)
    def delete(self, k: str): self.data.pop(k, None)
    def keys(self) -> List[str]: return list(self.data.keys())

class Cache:
    def __init__(self, max_size: int = 10000):
        self.data: Dict[str, Any] = {}
        self.max_size = max_size
        self.hits = self.misses = 0
    def get(self, k: str) -> Any:
        if k in self.data:
            self.hits += 1
            return self.data[k]
        self.misses += 1
        return None
    def set(self, k: str, v: Any):
        if len(self.data) >= self.max_size: self.data.pop(next(iter(self.data)))
        self.data[k] = v
    def clear(self): self.data.clear()

class TaskQueue:
    def __init__(self): self.q: deque = deque()
    def push(self, task: Any): self.q.append(task)
    def pop(self) -> Any: return self.q.popleft() if self.q else None
    def size(self) -> int: return len(self.q)

class PrimixRuntime:
    def __init__(self, code: str, filepath: str = ""):
        self.code = code
        self.filepath = filepath
        self.key = hashlib.sha256(hashlib.sha256(code.encode()).hexdigest().encode()).hexdigest()[:32]
        self.port = 5000 + (hash(self.key) % 5000)
        self.routes: Dict[tuple, List[str]] = {}
        self.disabled_routes: set = set()
        self.variables: Dict[str, Any] = {}
        self.storage = Storage()
        self.cache = Cache()
        self.queue = TaskQueue()
        self.start_time = datetime.now()
        self.t8t_mode = 'mixed'
        self.log_enabled = True
        self.debug_enabled = False
        self.ghost_mode = False
        self.physical_only = False
        self.blackhole_mode = False
        self.intruder_alert = False
        self.sos_targets: List[str] = []
        self.view_targets: List[str] = []
        self.blocked_keys: set = set()
        self.whitelist: set = set()
        self.balancer_enabled = False
        self.request_count = 0
        self.running = True

    def log(self, msg: str, level: str = "INFO"):
        if self.log_enabled: print(f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {msg}")

    def encrypt(self, data: str) -> str:
        modes = {'jp': T8T.jp_encrypt, 'en': T8T.en_encrypt, 'rnd': T8T.rnd_encrypt}
        return modes.get(self.t8t_mode, T8T.mixed_encrypt)(data, self.key)

    def eval_expr(self, expr: str, request_data: Optional[Dict] = None) -> Any:
        expr = str(expr).strip()
        if expr == '$key': return self.key
        if expr.startswith('"') and expr.endswith('"'): return expr[1:-1]
        if expr in ('true', 'false'): return expr == 'true'
        if expr.startswith('get to/ '): return self.storage.get(expr.split('get to/ ', 1)[1].strip())
        if expr in self.variables: return self.variables[expr]
        if request_data and expr in request_data: return request_data[expr]
        try: return int(expr)
        except ValueError:
            try: return float(expr)
            except ValueError: return expr

    def execute_line(self, line: str, request_data: Optional[Dict] = None) -> Optional[str]:
        line = line.strip()
        if not line or line.startswith('#'): return None

        keywords = ['respond', 'print', 'go', 'if', 'else', 'repeat', 'every', 'store', 'throw', 'db', 'file', 'env', 'ping', 'bind', 'block', 'whitelist', 'delete', 'save', 'load', 'key', 'intruder', 'blackhole', 'physical', 'lock', 'cache', 'queue', 'balance', 'burn', 'reload', 'list', 'timeout', 'add', 'view', 'clear', 'debug', 'log', 'status']
        
        if ' = ' in line and not any(line.startswith(kw) for kw in keywords):
            name, val = [p.strip() for p in line.split(' = ', 1)]
            self.variables[name] = ''.join(str(self.eval_expr(p.strip(), request_data)) for p in val.split('+')) if '+' in val else self.eval_expr(val, request_data)
            return None

        if line.startswith('print '):
            self.log(str(self.eval_expr(line[6:].strip(), request_data)))
            return None

        if line.startswith('respond '):
            rest = line[8:].strip()
            if rest.startswith('json '): return json.dumps(json.loads(rest[5:]))
            if rest.startswith('msgpack '): return rest[8:]
            if '+' in rest: return ''.join(str(self.eval_expr(p.strip(), request_data)) for p in rest.split('+'))
            return str(self.eval_expr(rest, request_data))

        if line.startswith('store on/ '):
            key = line.split('store on/ ', 1)[1].strip()
            self.storage.set(key, request_data.get(key, request_data) if request_data else None)
            return None

        if line.startswith('throw to/'):
            parts = line.split(' ', 2)
            self.log(f"THROW → {parts[1] if len(parts)>1 else ''}: {parts[2] if len(parts)>2 else ''}")
            return None

        if line.startswith('db query '):
            try:
                conn = sqlite3.connect(':memory:')
                c = conn.cursor()
                c.execute(line[9:].strip().strip('"'))
                res = str(c.fetchall())
                conn.close()
                return res
            except Exception as e: return f"DB Error: {e}"

        if line.startswith('file read '):
            try: return Path(line[10:].strip().strip('"')).read_text(encoding='utf-8')
            except Exception as e: return f"File Error: {e}"

        if line.startswith('file write '):
            parts = line[11:].strip().split(' ', 1)
            try: Path(parts[0].strip('"')).write_text(parts[1].strip('"') if len(parts)>1 else '', encoding='utf-8')
            except: pass
            return None

        if line == 'status':
            return (f"Key: {self.key[:8]}... | Port: {self.port} | Uptime: {datetime.now()-self.start_time}\n"
                    f"Requests: {self.request_count} | Routes: {len(self.routes)} | Cache: {len(self.cache.data)}\n"
                    f"T8T: {self.t8t_mode} | Ghost: {self.ghost_mode} | Physical: {self.physical_only}")

        if line == 'log on': self.log_enabled = True
        elif line == 'log off': self.log_enabled = False
        elif line == 'debug on': self.debug_enabled = True
        elif line == 'clear cache': self.cache.clear()
        elif line == 'balance on': self.balancer_enabled = True
        elif line.startswith('env '):
            k, v = [p.strip() for p in line[4:].strip().split('=', 1)]
            self.variables[k] = v.strip('"')
        elif line.startswith('ping '):
            self.log(f"PING {line[5:].strip()} — alive")
            return "pong"
        elif line == 'list servers': return f"Servers: {self.sos_targets}"
        elif line == 'key rotate':
            old = self.key
            self.key = hashlib.sha256((self.code + str(time.time())).encode()).hexdigest()[:32]
            self.log(f"KEY ROTATED: {old[:8]}... → {self.key[:8]}...")
        elif line == 'save state':
            try:
                Path('.primix_state.json').write_text(json.dumps({'variables': self.variables, 'storage': {k: self.storage.get(k) for k in self.storage.keys()}}))
                self.log("STATE SAVED")
            except Exception as e: self.log(f"Save state failed: {e}", "ERROR")
        elif line == 'load state':
            try:
                state = json.loads(Path('.primix_state.json').read_text())
                self.variables = state.get('variables', {})
                for k, v in state.get('storage', {}).items(): self.storage.set(k, v)
                self.log("STATE LOADED")
            except: pass
        elif line.startswith('/add t8t '):
            mode = line.split('/add t8t ')[1].strip()
            if mode in ('mixed', 'jp', 'en', 'rnd'):
                self.t8t_mode = mode
                self.log(f"T8T: {mode}")
        elif line.startswith('/add sos mod!'):
            self.sos_targets = line.split('/add sos mod!')[1].strip().split()
            self.log(f"SOS: {self.sos_targets}")
        elif line.startswith('/view in its entirety '):
            self.view_targets = line.split('/view in its entirety ')[1].strip().split()
            self.log(f"VIEW: {self.view_targets}")
            asyncio.create_task(self._health_report())
        elif line == 'burn server':
            self.log("BURN!", "CRITICAL")
            self.running = False
        elif line == 'reload server':
            self.parse_code()
        elif line.startswith('block key '):
            self.blocked_keys.add(line.split('block key ')[1].strip())
        elif line == 'lock down':
            self.physical_only = self.ghost_mode = self.blackhole_mode = True
            self.log("LOCKED DOWN")
        elif line == 'intruder alert': self.intruder_alert = True
        elif line == 'blackhole': self.blackhole_mode = True
        elif line == 'physical only': self.physical_only = True
        elif line.startswith('whitelist '): self.whitelist.add(line[10:].strip())
        return None

    async def _health_report(self):
        while self.running:
            await asyncio.sleep(3600)
            self.log(f"HEALTH REPORT → {self.view_targets}")

    def parse_code(self):
        self.routes = {}
        self.disabled_routes = set()
        lines = self.code.strip().split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('#'):
                i += 1
                continue

            if line.startswith('go request ') or line.startswith('go fields '):
                parts = line.split()
                method = 'GET' if parts[1] == 'request' else 'POST'
                path = parts[2].strip()
                body = []
                i += 1
                while i < len(lines) and lines[i].startswith('    '):
                    body.append(lines[i].strip())
                    i += 1
                self.routes[(method, path)] = body
            elif line.startswith('if '):
                condition = line[3:].split(' then')[0].strip()
                then_body, else_body = [], []
                i += 1
                while i < len(lines) and lines[i].startswith('    '):
                    then_body.append(lines[i].strip())
                    i += 1
                if i < len(lines) and lines[i].strip() == 'else':
                    i += 1
                    while i < len(lines) and lines[i].startswith('    '):
                        else_body.append(lines[i].strip())
                        i += 1
                self.routes[('IF', condition)] = {'then': then_body, 'else': else_body}
            elif line.startswith('repeat '):
                count = int(self.eval_expr(line[7:].split(' times')[0].strip()))
                body = []
                i += 1
                while i < len(lines) and lines[i].startswith('    '):
                    body.append(lines[i].strip())
                    i += 1
                for _ in range(count):
                    for b in body: self.execute_line(b)
            elif line.startswith('every '):
                parts = line[6:].split(' do')
                interval = parts[0].strip()
                body = []
                i += 1
                while i < len(lines) and lines[i].startswith('    '):
                    body.append(lines[i].strip())
                    i += 1
                seconds = 60
                if 'min' in interval: seconds = int(interval.replace('min','').strip()) * 60
                elif 'sec' in interval: seconds = int(interval.replace('sec','').strip())
                elif 'hour' in interval: seconds = int(interval.replace('hour','').strip()) * 3600
                asyncio.create_task(self._periodic(seconds, body))
            else:
                self.execute_line(line)
                i += 1

    async def _periodic(self, seconds: int, body: List[str]):
        while self.running:
            await asyncio.sleep(seconds)
            for b in body: self.execute_line(b)

    def execute_route(self, route_body: List[str], request_data: Optional[Dict] = None) -> str:
        result = None
        for line in route_body:
            res = self.execute_line(line, request_data)
            if res is not None: result = res
        return result if result else 'OK'

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.request_count += 1
        if self.blackhole_mode:
            writer.close()
            return

        try:
            data = await asyncio.wait_for(reader.read(16384), timeout=30)
            if not data:
                writer.close()
                return

            text = data.decode(errors='ignore')
            lines = text.split('\r\n')
            if not lines or len(lines[0].split(' ')) < 2:
                writer.close()
                return

            method, path, _ = lines[0].split(' ')
            body = text.split('\r\n\r\n', 1)[1] if '\r\n\r\n' in text else ''

            request_data = {}
            if body:
                try: request_data = json.loads(body)
                except:
                    for pair in body.split('&'):
                        if '=' in pair:
                            k, v = pair.split('=', 1)
                            request_data[k] = v

            route_key = (method, path)
            if route_key in self.disabled_routes:
                writer.write(b"HTTP/1.1 503\r\nConnection: keep-alive\r\n\r\nRoute disabled")
                await writer.drain()
                writer.close()
                return

            if route_key in self.routes:
                try:
                    cache_key = f"{method}:{path}:{body}"
                    cached = self.cache.get(cache_key)
                    if cached: response_body = cached
                    else:
                        response_body = self.execute_route(self.routes[route_key], request_data)
                        self.cache.set(cache_key, response_body)

                    encrypted = self.encrypt(response_body)
                    resp = (f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: keep-alive\r\n"
                            f"Content-Length: {len(encrypted.encode())}\r\n\r\n{encrypted}")
                    writer.write(resp.encode())
                    self.log(f"OK {method} {path}")
                except Exception as e:
                    self.disabled_routes.add(route_key)
                    self.log(f"ERR {method} {path}: {e}", "ERROR")
                    writer.write(b"HTTP/1.1 500\r\nConnection: keep-alive\r\n\r\nRoute error")
            else:
                writer.write(b"HTTP/1.1 404\r\nConnection: keep-alive\r\n\r\nNot Found")

            await writer.drain()
        except asyncio.TimeoutError: pass
        except Exception as e: self.log(f"Error: {e}", "ERROR")
        finally:
            writer.close()

    async def start(self):
        self.parse_code()
        try:
            server = await asyncio.start_server(self.handle_client, '0.0.0.0', self.port, backlog=2000)
        except OSError:
            self.port = 5000 + random.randint(1, 5000)
            server = await asyncio.start_server(self.handle_client, '0.0.0.0', self.port, backlog=2000)

        self.log(f"=== Primix v1.0 Monolithic ===")
        self.log(f"Key: {self.key}")
        self.log(f"Port: {self.port}")
        self.log(f"T8T: {self.t8t_mode} | Keep-alive: ON | Cache: ON | Queue: ON")
        self.log(f"Routes: {len(self.routes)} loaded | http://localhost:{self.port}")

        async with server:
            await server.serve_forever()

def main():
    if len(sys.argv) < 2:
        print("Primix v1.0 Monolithic Runtime")
        print("Usage: python primix.py <server.pmx>")
        return

    code = Path(sys.argv[1]).read_text(encoding='utf-8')
    runtime = PrimixRuntime(code, sys.argv[1])

    try:
        asyncio.run(runtime.start())
    except KeyboardInterrupt:
        print("\nServer stopped")

if __name__ == '__main__':
    main()
