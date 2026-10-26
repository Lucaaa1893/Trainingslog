#!/usr/bin/env python3
"""Fügt Health-Export-Werte verschlüsselt in health.enc.json ein.

Aufruf:  python3 tools/health_sync.py <SCHLÜSSEL> <textdatei> [<textdatei> ...]
Jede Textdatei enthält den Inhalt einer „Health Export“-Mail (Zeilen „Name: Wert“).
Verschlüsselung: PBKDF2-SHA256 (200.000 Runden) + AES-256-GCM, kompatibel mit WebCrypto in der App.
"""
import base64, json, os, re, sys
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'health.enc.json')
ITER = 200_000
KEYS = [('weight', r'gewicht'), ('fat', r'k[öo]rperfett'), ('muscle', r'muskel'), ('bmi', r'bmi'),
        ('sleep', r'schlaf'), ('steps', r'schritte'), ('kcal', r'kalorien'), ('rhr', r'ruhepuls'), ('hrv', r'hrv')]

def derive(pw, salt):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(pw.encode())

def parse(txt):
    out, date = {}, None
    for line in txt.splitlines():
        m = re.match(r'\s*([^:]+):\s*(.*)$', line)
        if not m: continue
        key, raw = m.group(1).strip(), m.group(2).strip()
        if re.search('datum', key, re.I):
            d = re.search(r'\d{4}-\d{2}-\d{2}', raw)
            if d: date = d.group(0)
            continue
        k = next((k for k, rx in KEYS if re.search(rx, key, re.I)), None)
        if not k or not raw: continue
        try: v = float(raw.split()[0].replace(',', '.'))
        except ValueError: continue
        if k == 'sleep' and v > 48: v = v / 3600
        if k == 'weight' and v > 400: continue
        out[k] = round(v, 2)
    return date, out

def load(pw):
    if not os.path.exists(FILE): return {}
    o = json.load(open(FILE))
    key = derive(pw, base64.b64decode(o['salt']))
    pt = AESGCM(key).decrypt(base64.b64decode(o['iv']), base64.b64decode(o['ct']), None)
    return json.loads(pt)

def save(pw, data):
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(derive(pw, salt)).encrypt(iv, json.dumps(data, separators=(',', ':')).encode(), None)
    b = lambda x: base64.b64encode(x).decode()
    json.dump({'v': 1, 'iter': ITER, 'salt': b(salt), 'iv': b(iv), 'ct': b(ct)}, open(FILE, 'w'))

if __name__ == '__main__':
    pw, files = sys.argv[1], sys.argv[2:]
    data = load(pw)
    for f in files:
        date, vals = parse(open(f, encoding='utf-8').read())
        if date and vals:
            data[date] = {**data.get(date, {}), **vals}
            print('ok', date, vals)
        else:
            print('übersprungen', f)
    save(pw, data)
    print('Tage gespeichert:', len(data))
