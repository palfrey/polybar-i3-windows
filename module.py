#!/usr/bin/python3

import os
import asyncio
import getpass
from typing import Callable, Optional
import i3ipc
import platform
from functools import partial
import sys

from icon_resolver import IconResolver

#: Max length of single window title
MAX_LENGTH = 50
#: Base 1 index of the font that should be used for icons
ICON_FONT = 3

HOSTNAME = platform.node()
USER = getpass.getuser()

ICONS = [
    ('class=*.slack.com', '\uf3ef'),

    ('class=Chromium', '\ue743'),
    ('class=Firefox', '\uf738'),
    ('class=URxvt', '\ue795'),
    ('class=Code', '\ue70c'),
    ('class=code-oss-dev', '\ue70c'),

    ('name=mutt', '\uf199'),

    ('*', '\ufaae'),
]

FORMATTERS: dict[str, Callable[[str], str]] = {
    'Chromium': lambda title: title.replace(' - Chromium', ''),
    'Firefox': lambda title: title.replace(' - Mozilla Firefox', ''),
    'URxvt': lambda title: title.replace('%s@%s: ' % (USER, HOSTNAME), ''),
    'Code': lambda title: title.replace(' - Visual Studio Code', ''),
}

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
COMMAND_PATH = os.path.join(SCRIPT_DIR, 'command.py')

icon_resolver = IconResolver(ICONS)


def main(ws: Optional[int]=None):
    i3 = i3ipc.Connection()

    on_change_ws = partial(on_change, ws)
    i3.on('workspace::focus', on_change_ws)
    i3.on('window::focus', on_change_ws)
    i3.on('window', on_change_ws)

    loop = asyncio.get_event_loop()

    loop.run_in_executor(None, i3.main)

    render_apps(i3, ws)

    loop.run_forever()


def on_change(ws: Optional[int], i3: i3ipc.Connection, _event: i3ipc.events.IpcBaseEvent):
    render_apps(i3, ws)


def render_apps(i3: i3ipc.Connection, ws: Optional[int]):
    tree = i3.get_tree()
    wss = i3.get_workspaces()
    visible_ws = [ws.name for ws in wss if ws.visible]
    
    apps = tree.leaves()
    apps = [app for app in apps if app.workspace().name in visible_ws]
    if ws is not None:
        apps = [app for app in apps if (int(app.workspace().name)-1) % 3 == ws]
    apps.sort(key=lambda app: app.workspace().name)

    out = '%{O12}'.join(format_entry(app) for app in apps)

    print(out, flush=True)


def format_entry(app: i3ipc.Con):
    title = make_title(app)
    u_color = '#b4619a' if app.focused else\
        '#e84f4f' if app.urgent else\
        '#404040'

    return '%%{u%s} %s %%{u-}' % (u_color, title)


def make_title(app: i3ipc.Con):
    #out = get_prefix(app) + format_title(app)
    out = format_title(app)

    if app.focused:
        out = '%{F#fff}' + out + '%{F-}'

    return '%%{A1:%s %s:}%s%%{A-}' % (COMMAND_PATH, app.id, out)


def get_prefix(app: i3ipc.Con):
    icon = icon_resolver.resolve({
        'class': app.window_class,
        'name': app.name,
    })

    return ('%%{T%s}%s%%{T-}' % (ICON_FONT, icon))


def format_title(app: i3ipc.Con):
    klass = app.window_class
    name: Optional[str] = app.name

    title = FORMATTERS[klass](name) if klass in FORMATTERS else name

    if title is None:
        title = ""
    elif len(title) > MAX_LENGTH:
        title = title[:MAX_LENGTH - 3] + '...'

    return title

if len(sys.argv) == 2:
    main(int(sys.argv[1]))
else:
    main()
