"""
Native file dialogs on Linux.

Tk draws its own dated file dialog on Linux, while Windows and macOS already get
the native one. On Linux we call the desktop's chooser (kdialog or zenity) and
fall back to Tk whenever that does not work. The functions mirror
tkinter.filedialog so they can be used as drop-in replacements.

Set PS2MCM_FILE_DIALOG to kdialog, zenity or tk to force a specific dialog.
"""

import os
import shutil
import subprocess
import sys
import time
from tkinter import filedialog
from urllib.parse import unquote, urlparse

TOOLS = ('kdialog', 'zenity')

# A cancel faster than this is a tool that failed to start, not a person
MIN_CANCEL_SECONDS = 0.3

# Directory of the last chosen file, used as the starting point of the next dialog
_last_directory = os.path.expanduser('~')

# Tools that failed once are not tried again during this session
_broken_tools = set()


def askopenfilename(title='Open', filetypes=(), parent=None):
    path = _native_dialog(save=False, title=title, filetypes=filetypes, parent=parent)
    if path is None:
        path = filedialog.askopenfilename(title=title, filetypes=filetypes,
                                          initialdir=_last_directory, parent=parent)
    return _remember(path)


def asksaveasfilename(title='Save', initialfile='', defaultextension='', filetypes=(), parent=None):
    path = _native_dialog(save=True, title=title, filetypes=filetypes, parent=parent,
                          initialfile=initialfile)
    if path is None:
        path = filedialog.asksaveasfilename(title=title, initialfile=initialfile,
                                            defaultextension=defaultextension, filetypes=filetypes,
                                            initialdir=_last_directory, parent=parent)
    elif path and defaultextension and not os.path.splitext(path)[1]:
        # Same behavior as Tk: add the extension when the user typed none
        path += defaultextension
    return _remember(path)


def _remember(path):
    global _last_directory
    if path:
        _last_directory = os.path.dirname(path)
    return path or ''


def _native_dialog(save, title, filetypes, parent, initialfile=''):
    """Return the chosen path, '' when cancelled, or None to fall back to Tk"""
    try:
        for tool in _candidate_tools():
            path = _run_tool(tool, save, title, filetypes, parent, initialfile)
            if path is not None:
                return path
            _broken_tools.add(tool)
            print(f"native_dialogs: {tool} failed, trying the next file dialog", file=sys.stderr)
    except Exception as e:
        # Never let a native dialog problem break the action, Tk always works
        print(f"native_dialogs: falling back to Tk ({e})", file=sys.stderr)
    return None


def _candidate_tools():
    forced = os.environ.get('PS2MCM_FILE_DIALOG', '').strip().lower()
    if forced == 'tk':
        return []
    if forced in TOOLS:
        return [forced] if shutil.which(forced) else []
    if not sys.platform.startswith('linux'):
        return []

    tools = list(TOOLS)
    if 'KDE' not in os.environ.get('XDG_CURRENT_DESKTOP', '').upper():
        tools.reverse()
    return [tool for tool in tools if tool not in _broken_tools and shutil.which(tool)]


def _run_tool(tool, save, title, filetypes, parent, initialfile):
    """Return the chosen path, '' when cancelled, or None when the tool did not work"""
    start = os.path.join(_last_directory, initialfile) if initialfile else _last_directory + os.sep
    if tool == 'kdialog':
        command = _kdialog_command(save, title, filetypes, parent, start)
    else:
        command = _zenity_command(save, title, filetypes, parent, start)

    started = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8',
                                errors='surrogateescape', env=_host_environment())
    except OSError:
        return None
    elapsed = time.monotonic() - started

    if result.returncode == 1 and elapsed >= MIN_CANCEL_SECONDS:
        return ''
    if result.returncode != 0:
        return None

    path = _clean_path(result.stdout)
    if not path or not os.path.isabs(path):
        return None
    if not save and not os.path.isfile(path):
        return None
    return path


def _clean_path(output):
    """First line of the tool output, accepting file:// URLs as well as plain paths"""
    lines = output.strip().splitlines()
    path = lines[0].strip() if lines else ''
    if path.startswith('file://'):
        path = unquote(urlparse(path).path)
    return path


def _zenity_command(save, title, filetypes, parent, start):
    command = ['zenity', '--file-selection', f'--title={title}', f'--filename={start}']
    if save:
        command.append('--save')
    for name, pattern in filetypes:
        command.append(f'--file-filter={name} | {_pattern(pattern)}')
    window = _window_id(parent)
    if window is not None:
        command.append(f'--attach={window}')
    return command


def _kdialog_command(save, title, filetypes, parent, start):
    filters = '\n'.join(f'{name} ({_pattern(pattern)})' for name, pattern in filetypes)
    command = ['kdialog', '--title', title,
               '--getsavefilename' if save else '--getopenfilename', start, filters]
    window = _window_id(parent)
    if window is not None:
        command[1:1] = ['--attach', str(window)]
    return command


def _pattern(pattern):
    # Tk uses *.* for "any file", desktop dialogs use *
    return '*' if pattern == '*.*' else pattern


def _window_id(widget):
    """X11 id of the parent window so the dialog stays on top of it, when available"""
    if widget is None:
        return None
    try:
        return int(widget.winfo_toplevel().wm_frame(), 16)
    except Exception:
        return None


def _host_environment():
    """Environment for host programs, without the libraries bundled by PyInstaller"""
    env = dict(os.environ)
    if getattr(sys, 'frozen', False):
        original = env.get('LD_LIBRARY_PATH_ORIG')
        if original is not None:
            env['LD_LIBRARY_PATH'] = original
        else:
            env.pop('LD_LIBRARY_PATH', None)
    # Let GTK use the desktop portal, so zenity shows the KDE dialog on Plasma
    env.setdefault('GTK_USE_PORTAL', '1')
    return env
