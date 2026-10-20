"""
Native file dialogs on Linux.

Tk draws its own dated file dialog on Linux, while Windows and macOS already get
the native one. On Linux we call the desktop's chooser (kdialog or zenity) and
fall back to Tk when neither is available. The functions mirror
tkinter.filedialog so they can be used as drop-in replacements.
"""

import os
import shutil
import subprocess
import sys
from tkinter import filedialog

# Directory of the last chosen file, used as the starting point of the next dialog
_last_directory = os.path.expanduser('~')


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
    """Return the chosen path, '' when cancelled, or None when no native dialog could run"""
    if not sys.platform.startswith('linux'):
        return None

    tools = ['zenity', 'kdialog']
    if 'KDE' in os.environ.get('XDG_CURRENT_DESKTOP', '').upper():
        tools.reverse()

    start = os.path.join(_last_directory, initialfile) if initialfile else _last_directory + os.sep
    for tool in tools:
        if not shutil.which(tool):
            continue
        if tool == 'kdialog':
            command = _kdialog_command(save, title, filetypes, parent, start)
        else:
            command = _zenity_command(save, title, filetypes, parent, start)
        try:
            result = subprocess.run(command, capture_output=True, text=True, env=_host_environment())
        except OSError:
            continue
        if result.returncode == 0:
            return result.stdout.strip()
        if result.returncode == 1:
            return ''
    return None


def _zenity_command(save, title, filetypes, parent, start):
    command = ['zenity', '--file-selection', f'--title={title}', f'--filename={start}']
    if save:
        command.append('--save')
    for name, pattern in filetypes:
        command.append(f'--file-filter={name} | {_pattern(pattern)}')
    if parent is not None:
        command.append(f'--attach={_window_id(parent)}')
    return command


def _kdialog_command(save, title, filetypes, parent, start):
    filters = '\n'.join(f'{name} ({_pattern(pattern)})' for name, pattern in filetypes)
    command = ['kdialog', '--title', title,
               '--getsavefilename' if save else '--getopenfilename', start, filters]
    if parent is not None:
        command[1:1] = ['--attach', str(_window_id(parent))]
    return command


def _pattern(pattern):
    # Tk uses *.* for "any file", desktop dialogs use *
    return '*' if pattern == '*.*' else pattern


def _window_id(widget):
    return int(widget.winfo_toplevel().wm_frame(), 16)


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
