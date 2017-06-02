#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ConfigParser import ConfigParser
import logging
import requests
import re


BASE_URL = "https://stackoverflow.com"
LOGIN_URL = "/users/login"
VALIDATION_URL = "/users/login-or-signup/validation/track"
BADGE_URL = "/users/activity/next-badge-popup?userId=%d&isTagBadge=false"

SESSION = requests.Session()

config = ConfigParser()
config.read("fanatic.conf")

LOG_LEVEL = {
        "CRITICAL" : logging.CRITICAL,
        "ERROR"    : logging.ERROR,
        "WARNING"  : logging.WARNING,
        "INFO"     : logging.INFO,
        "DEBUG"    : logging.DEBUG
        }

logging.basicConfig(
        filename = config.get("log", "file"),
        level = LOG_LEVEL[config.get("log", "level")],
        format = "[%(asctime)s] [%(levelname)s]: %(message)s",
        datefmt="%Y-%m-%d %I:%M:%S"
        )


def get_fkey():
    login_form = SESSION.get(BASE_URL + LOGIN_URL)
    match = re.search('<input type="hidden" name="fkey" value="([0-9a-f]+)">', login_form.text)
    return match.group(1)

def validate(fkey, email, password):
    data = {
            'isSignup': False,
            'isLogin': True,
            'isPassword': False,
            'isAddLogin': False,
            'hasCaptcha': False,
            'fkey': fkey,
            'email': email,
            'password': password,
            'submitbutton': 'Log In',
            }
    SESSION.post(
            BASE_URL + VALIDATION_URL,
            data = data,
            )

def login(fkey, email, password):
    data = {
            'fkey': fkey,
            'email': email,
            'password': password,
        }
    res = SESSION.post(
            BASE_URL + LOGIN_URL,
            data = data,
            allow_redirects=False,
            )
    if res.status_code == 302:
        return res.headers["Location"]
    elif res.status_code == 200:
        g = re.search(r"StackExchange.helpers.showMessage\(.*?\).*\n.*'(.*)'.*", res.text)
        if g != None:
            msg = g.group(1)
        else:
            msg = "Unkown Error"
        raise ValueError(msg)

def get_profile_url(url):
    first_page = SESSION.get(url)
    g = re.search(r'<a href="(.*?)" class="my-profile', first_page.text)
    if g != None:
        return g.group(1)
    else:
        raise ValueError("Can not get profile url")

def get_profile(profile_url):
    profile = {
        "id" : 0,
        "name" : "",
        "reputation" : 0,
        "badges": {
            "gold":0,
            "silver":0,
            "bronze":0,
        },
    }
    profile_page = SESSION.get(profile_url)
    
    g = re.search(r'"userId":(\d+)', profile_page.text)
    if g != None:
        profile["id"] = int(g.group(1))
    else:
        raise ValueError("Can not get user id")

    g = re.search(r'<div class="name">(.*?)</div>', profile_page.text, re.DOTALL)
    if g != None:
        profile["name"] = g.group(1).strip()
    else:
        raise ValueError("Can not get name")

    g = re.search(r'<span class="rep">(.*?)</span>', profile_page.text)
    if g != None:
        profile["reputation"] = int(g.group(1).replace(",", ""))
    else:
        raise ValueError("Can not get reputation")
    badge_matches = re.findall(r'(<span class=".*?" title="(\d+) (.*?) badges?"><span class="badge."></span><span class="badgecount">\d+</span></span>)', profile_page.text)
    for i in badge_matches:
        profile["badges"][i[2]] = int(i[1])

    return profile

def get_progress(user_id):
    badge_page = SESSION.get(BASE_URL + BADGE_URL % (user_id, ))
    g = re.search(r"""<div class="badge-progress js-badge-progress (.*?)"
            style=".*?"
            data-badge-database-name="Fanatic">""", badge_page.text)
    if g.group(1).startswith("completed "):
        return "Fanatic - Completed"
    else:
        g = re.search(r'<div class="label">(Fanatic.*?)</div>', badge_page.text)
        return g.group(1)

try:
    fkey = get_fkey()
    validate(fkey, 
        config.get('account', 'email'),
        config.get('account', 'password')
        )
    redirect_url = login(fkey, 
        config.get('account', 'email'),
        config.get('account', 'password')
        )

except Exception as e:
    logging.error("Login Fail: %s" % e)
    exit(-1)

logging.debug("Login OK! Get user info")

try:
    profile_url = get_profile_url(redirect_url)
    profile = get_profile(BASE_URL + profile_url)
    progress = get_progress(profile["id"])
    logging.info("%s : %d [Gold:%d, Silver:%d, Bronze:%d] %s" % (
        profile["name"],
        profile["reputation"],
        profile["badges"]["gold"],
        profile["badges"]["silver"],
        profile["badges"]["bronze"],
        progress
        ))
    
except Exception as e:
    logging.warn("Get user info fail: %s" % e)

