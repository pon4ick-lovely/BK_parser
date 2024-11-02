import os
import re
import json
import requests as req
from tabulate import tabulate
from datetime import datetime
from functools import reduce
from base import *

classes = {}
ignored = []
insub = []
info = {"OVInPlay_1_9": classes}
INFO = {
    'S3': 'Attacks',
    'S7': 'Possession',
    'S1': 'On Target',
    'S2': 'Off Target',
    'S4': 'Dangerous Attacks'}
EVINFO = {
    '3': 'Substitution',
    '0': 'Stat',
    '1': 'Stats',
    '7': 'Corners',
    '4': 'Yellow cards',
    '5': 'Red cards',
    '2': 'Goals'}
surl = 'https://api.telegram.org/bot327683027:349378110:AAEazcXcH9MpnjxPV_cEVFOxxnJAIFYfUm0/sendMessage'


def nd(text):
    return {'chat_id': "@bettest",
                       'text': text,
                       'disable_web_page_preview': 1,
                       'disable_notification': 0}


def search(id, _):
    if _.get("IT") == id:
        return _
    for v in _.values():
        if isinstance(v, list):
            for vv in [x for x in v if isinstance(x, dict)]:
                res = search(id, _=vv)
                if res:
                    return res
        if isinstance(v, dict):
            res = search(id, _=v)
            if res:
                return res


def to_min(u):
    return (datetime.now() -
            datetime.strptime(u[:14], "%Y%m%d%H%M%S")).seconds // 60 if u else u


def fetch_games():
    global info, classes
    if not info['OVInPlay_1_9'].get('OV_1_1_9'):
        return
    for key, value in info['OVInPlay_1_9']['OV_1_1_9'].items():
        if re.match(r'OV[A-Z]', key):
            for game, gv in value.items():
                if re.match(r'OV', game):
                    yield gv


def fetch_params(g, param):
    for k, v in g.items():
        if re.match(param, k):
            return v


def fetch_events(ev):
    for v in ev.values():
        if isinstance(v, dict):
            if "ST" in v.keys():
                vv = v["ST"]
            else:
                vv = v
            yield vv["IC"], vv["SZ"], vv["LA"]


def fetch_sg(lv):
    return lv if isinstance(lv, dict) else fetch_sg(lv[0])


def to_table(obj):
    l = [_ for _ in obj.values() if isinstance(_, dict)]
    n1, n2 = l[0].pop('Team'), l[1].pop('Team')
    headers = [obj["League"], n1, n2]
    table = list(map(dict.values, l))
    return tabulate(list(zip(l[0].keys(), table[0], table[1])), headers)


def format_game(g):
    if not g.get('CC'):
        return
    try:
        teams = {_['NA']: {'OD': _['OD']} for _ in fetch_params(
            g, r'.*1777_1_9').values() if isinstance(_, dict) and _['OR'] in '02'}
    except Exception as e:
        return
    teams.update({'Match': g['NA'], 'League': g['CT'], 'Min': to_min(g['TU'])})
    live_ = fetch_params(g, r'.*M1_1_9')
    if not live_ or not live_.get("SG"):
        return
    for v in [_ for _ in live_['TG'].values() if isinstance(_, dict)]:
        if v['NA'] in teams.keys():
            teams[v['NA']].update({val: v[key] for key, val in INFO.items()})
        else:
            teams[v['NA']] = {val: v[key] for key, val in INFO.items()}
    sg_ = fetch_sg(live_["SG"])
    n0, n2 = list(map(str.strip, g['NA'].split(' v ')))
    try:
        events = list(fetch_events(sg_))
    except:
        return
    for _ in EVINFO.values():
        if _ != 'Stats':
            teams[n0][_] = 0
            teams[n2][_] = 0
    for e in events:
        if not e[0] in '01' and e[0]:
            teams[eval('n' + e[1])][EVINFO[e[0]]] += 1
    teams[n0]['Team'] = n0
    teams[n2]['Team'] = n2
    return teams


def evaltotal(t1, t2):
    return True if t2['Red cards'] == 0 and\
                    t1['Dangerous Attacks'] > 2 and\
                    t2['Dangerous Attacks']/2 > t2['Dangerous Attacks'] and\
                    t1['Attacks'] < t2['Attacks'] and\
                    t1['Corners'] and\
                    t1['On Target'] == 0 and\
                    t1['Off Target'] and\
                    t1['Possession'] <= 45 and\
                    t1['Goals'] in [0, 1] and\
                    t2['Goals'] == 0\
            else False


def is_total(g):
    if g['Min'] < 15:
        return None
    l = [_ for _ in g.values() if isinstance(_, dict)]
    for _ in l:
        for i in INFO.values():
            _[i] = int(_[i]) if _[i] else 0
    if evaltotal(l[0], l[1]):
        return '#total\n{m} минута\nЛига: {l}\nФаворит: {f}\n{t}'.format(g['Min'], g['League'], l[0]['Team'], to_table(g))
    if evaltotal(l[1], l[0]):
        return '#total\n{m} минута\nЛига: {l}\nФаворит: {f}\n{t}'.format(g['Min'], g['League'], l[1]['Team'], to_table(g))


def evalfora(t1, t2):
    check = lambda i: t2[i]/(sum(map(lambda _: _[i], [t1, t2]))+0.01)*100
    return True\
        if sum(map(check, ['Dangerous Attacks', 'Attacks', 'Possession']))/3 >= 90 and\
            t1['In Target'] <= t2['In Target'] and\
            t1['Off Target'] <= t2['Off target'] and\
            t2['Red cards'] == 0 and\
            t1['Corners']/t2['Corners'] < 2\
    else None

def is_fora(g):
    if g['Min'] < 20:
        return None
    l = [_ for _ in g.values() if isinstance(_, dict)]
    for _ in l:
        for i in INFO.values():
            _[i] = int(_[i]) if _[i] else 0
    if evalfora(l[0], l[1]):
        return '#fora\n{m} минута\nЛига: {l}\nФаворит: {f}\n{t}'.format(g['Min'], g['League'], l[0]['Team'], to_table(g))
    if evalfora(l[1], l[0]):
        return '#fora\n{m} минута\nЛига: {l}\nФаворит: {f}\n{t}'.format(g['Min'], g['League'], l[1]['Team'], to_table(g))
    return None


def get_games():
    global ignored, info, classes
    for _ in fetch_games():
        if _ is None:
            continue
        try:
            g = format_game(_)
        except:
            continue
        if g is None:
            continue
        if g['Min'] >= 25: ignored.append(g['Match'])
        if g['Match'] in ignored:
            continue
        res = is_total(g)
        if res:
            print(res)
            yield nd(res)
            ignored.append(g['Match'])
        res = is_fora(g)
        if res:
            print(res)
            yield nd(res)
            ignored.append(g['Match'])
        

def handler(msg):
    global info, classes
    bool_var = False
    head = msg[0]
    topic = msg[1:msg.index(RECORD_DELIM)].decode()
    if topic == '100' or topic == '__time' or topic == "EMPTY":
        print(msg)
        return
    msg = msg[msg.index(RECORD_DELIM) + 1:]
    msg = msg[:-1].split(b'|')
    if head == INITIAL_TOPIC_LOAD:
        if topic == 'OVInPlay_1_9/OV_1_1_9':
            if msg[0] == b'F':
                need = 1
                for m in msg[1:]:
                    m = m.split(b';')
                    it = dict(map(lambda x: x.split('='),
                                  map(bytes.decode, m[1:-1])))
                    if m[0] == b'CL':
                        cl = it['IT']
                        classes[cl] = it
                    elif m[0] == b'CT':
                        lg = it['IT']
                        classes[cl][lg] = it
                    elif m[0] == b'EV':
                        g = it['IT']
                        classes[cl][lg][g] = it
                    elif m[0] == b'MA':
                        od = it['IT']
                        classes[cl][lg][g][od] = it
                    elif m[0] == b'PA':
                        pa = it["IT"]
                        classes[cl][lg][g][od][pa] = it
                bool_var = True
        elif 'OVInPlay_1_9' in topic:
            return
        else:
            cl = info["OVInPlay_1_9"]["OV_1_1_9"]
            if msg[0] == b'F':
                if topic == "EMPTY":
                    return
                for m in msg[1:]:
                    m = m[:-1].split(b';')
                    it = dict(map(lambda x: x.split('='),
                                  map(bytes.decode, m[1:])))
                    if m[0] == b'EV':
                        for l in [_ for _ in cl.keys() if re.match(
                                r'OV.{1,}C1_1_9', _)]:
                            for v in cl[l].values():
                                if isinstance(v, dict) and (
                                        v["NA"] == it["NA"] or v["ID"] == it["ID"]):
                                    g = v
                                    g[topic] = it
                                    break
                    else:
                        try:
                            key = m[0].decode()
                            if key == "ES":
                                sg = it
                                g[topic]["ES"] = it
                            elif key == "SL" or key == "SC":
                                g[topic]["ES"].update({it["IT"]: it})
                            elif key == "TG":
                                g[topic]["TG"] = it
                            elif key == "TE":
                                g[topic]["TG"].update({it["IT"]: it})
                            elif key == "SG":
                                if g[topic].get('SG'):
                                    g[topic]['SG'] = [g[topic]['SG'], it]
                                else:
                                    g[topic]["SG"] = it
                            elif key == "ST":
                                if isinstance(g[topic]['SG'], list):
                                    g[topic]['SG'][1].update({it["IT"]: it})
                                else:
                                    g[topic]["SG"].update({it["IT"]: it})
                        except:
                            print(topic, msg)
                            raise ValueError("MSG")
    elif head == DELTA:
        print(topic, msg)
        if msg[0] == b'U':
            o = search(topic, info)
            for _ in msg[1:]:
                if _.index(b';') == 2:
                    if _[:2] == b'EV':
                        bool_var = True
                    _ = _[3:]
                o.update(dict(map(lambda x: x.split('='), _[:-1].decode().split(';'))))
        elif msg[0] == b'D':
            try:
                *_, w, v = topic.split('/')
                o = search(w, info)
                del o[v]
            except Exception as e:
                print('ERROR DELETE', msg)
        elif msg[0] == b'I':
            w, v = topic.split('/')
            o = search(w, info)
            for _ in msg[1:]:
                _ = _[:-1].decode().split(';')
                kkk = [m for m in _ if '=' not in m]
                _ = [m for m in _ if '=' in m]
                if kkk[-1] == 'EV':
                    bool_var = True
                    d = dict(map(lambda x: x.split('='), _))
                else:
                    d = {kkk[-1]: dict(map(lambda x: x.split('='), _))}
                o[v] = d
    else:
        print('ERROR', msg)
    return bool_var

def bounds(msg):
    if msg[:3] == b'100':
        return
    r = []
    for _ in msg.split(MESSAGE_DELIM):
        r.append(handler(_))
    return any(r)


def subs():
    global info, classes
    for l in [_ for _ in info['OVInPlay_1_9'][
            'OV_1_1_9'].keys() if re.match(r'OV.{1,}C1_1_9', _)]:
        for g in [_ for _ in info['OVInPlay_1_9']['OV_1_1_9']
                  [l].keys() if re.match(r'OV.{1,}C1[A]?_1_9', _)]:
            if info['OVInPlay_1_9']['OV_1_1_9'][l][g]['AU'] == '':
                insub.append(g)
            if g not in insub:               
                try:
                    yield info['OVInPlay_1_9']['OV_1_1_9'][l][g]['ID'].replace("C1_1_9", "M1_1_9")
                    insub.append(g)
                except Exception as e:
                    print(e)
                    print(json.dumps(info['OVInPlay_1_9']['OV_1_1_9'][l][g], indent=2))
                    exit()
