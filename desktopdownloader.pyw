#!/usr/bin/python3
import http.cookiejar
import json
import os
import pickle
import re
import sys
import requests
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import signal

RELEASE_API_URL = "https://connect.monstercat.com/api/catalog/release"
# RELEASE_API_URL = "http://localhost/release"
SESSION_CHECK_URL = "https://connect.monstercat.com/api/self/session"
SIGNIN_URL = "https://connect.monstercat.com/signin"
DOWNLOAD_BASE = "https://connect.monstercat.com/api/release/"

DOWNLOAD_FORMATS = dict(
        WAV="?format=wav",
        MP3_320="?format=mp3&bitRate=320",
        MP3_V0="?format=mp3&quality=0",
        MP3_V2="?format=mp3&quality=2",
        MP3_128="?format=mp3&bitRate=128",
        FLAC="?format=flac"
)

DATA_PATH = os.path.expanduser("~") + "/.monstercatconnect/"
SAVE_FILE = DATA_PATH + "connect.db"
DOWNLOAD_PATH = DATA_PATH + "downloads/"
CHECK_INTERVAL = 300000  # = 5 Minutes in milliseconds
# CHECK_INTERVAL = 20000  # = 20 Seconds in milliseconds
COOKIE_FILE = DATA_PATH + "connect.cookies"


class SignInDialog(QDialog):
    username = None
    password = None
    session = None
    checkbox = None

    def __init__(self, session):
        super().__init__()
        self.init_ui()
        self.session = session

    def init_ui(self):
        grid = QGridLayout()
        self.setLayout(grid)
        self.setWindowTitle("Login to Monstercat Connect")

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        login_button = QPushButton("Login")
        login_button.pressed.connect(self.login)

        self.checkbox = QCheckBox("Stay signed in?")

        grid.addWidget(QLabel("E-Mail: "), *(1, 1))
        grid.addWidget(self.username, *(1, 2))
        grid.addWidget(QLabel("Password: "), *(2, 1))
        grid.addWidget(self.password, *(2, 2))
        grid.addWidget(self.checkbox, *(3, 1))
        grid.addWidget(login_button, *(4, 2))

    def login(self):
        print("Signing in...")
        payload = {"email": self.username.text(), "password": self.password.text()}
        response_raw = self.session.post(SIGNIN_URL, data=payload)
        response = json.loads(response_raw.text)
        if len(response) > 0:
            show_popup("Sign-In failed!", "Sign-In Error: " + response.get("message", "Unknown error"))
            return False
        if self.checkbox.isChecked():
            save_cookies(self.session.cookies, COOKIE_FILE)
        self.close()
        show_popup("Sign-In successful!", "You are successfully logged in!")
        return True


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super(SystemTrayIcon, self).__init__(icon, parent)
        menu = QMenu(parent)

        check_new_releases_action = menu.addAction("Check new releases")
        check_new_releases_action.triggered.connect(lambda: check_new_release(self, session))

        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(sys.exit)

        self.setContextMenu(menu)


def create_directories():
    os.makedirs(DATA_PATH, exist_ok=True)
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)


def show_popup(title, text):
    msgbox = QMessageBox()
    msgbox.setWindowTitle(title)
    msgbox.setText(text)
    msgbox.exec_()


def download_file(url, path, session):
    count = 0
    chunksize = 8192
    lastvalue = 0

    r = session.get(url, stream=True)
    filename = str.replace(re.findall("filename=(.+)", r.headers['content-disposition'])[0], "\"", "")
    fullpath = path + "/" + filename
    print(fullpath)
    diff = (100 / int(r.headers['Content-Length']))

    # PROGRESS BAR
    bar = QProgressDialog("Downloading <i>" + filename + "</i>", "Cancel", 0, 100)
    bar.setWindowTitle("Downloading")
    bar.setValue(0)

    with open(fullpath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=chunksize):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                percentvalue = round(count * chunksize * diff, 0)
                # print(percentvalue)
                if percentvalue != lastvalue:
                    bar.setValue(percentvalue)
                    lastvalue = percentvalue
                count += 1
                if bar.wasCanceled():
                    os.remove(fullpath)
                    return False
                QApplication.processEvents()
    bar.close()
    return True


def save_cookies(cj, filename):
    print("Saving cookies")
    cj.save(filename=filename)


def load_cookies(filename):
    print("Loading cookies...")
    cj = http.cookiejar.MozillaCookieJar()
    if not os.path.isfile(filename):
        return cj, False
    cj.load(filename=filename)
    print("Cookies loaded.")
    return cj, True


def check_logged_in(session):
    response_raw = session.get(SESSION_CHECK_URL)
    response = json.loads(response_raw.text)
    if not response.get("user"):
        return False
    if response.get("user").get("subscriber", False) == True:
        return True
    print(response.text)
    return False


def load_track_list(session):
    # GET TRACK LIST
    print("Loading track list...")
    tracks_raw = session.get(RELEASE_API_URL)

    # PARSE RESPONSE INTO JSON
    tracks = json.loads(tracks_raw.text)
    return tracks


def write_to_file(filename, list_to_save):
    print("Saving data to file...")
    with open(filename, 'wb') as f:
        pickle.dump(list_to_save, f)


def load_from_file(filename):
    print("Loading data from file...")
    if not os.path.isfile(filename):
        return []
    with open(filename, 'rb') as f:
        return pickle.load(f)


def check_new_release(tray_icon, session):
    # tray_icon.showMessage("Checking", "Checking for new releases...")
    new = load_album_list()
    new_ids = get_album_ids(new)
    old_ids = load_from_file(SAVE_FILE)
    new_items = list(set(new_ids) - set(old_ids))

    if len(new_items) and not len(new_items) > 20:
        print("New items!")
        for album in new.get("results"):
            if album.get("_id") in new_items:
                message = "\"" + album.get("title", "NO TITLE") + "\" by \"" + \
                          album.get("renderedArtists", "NO ARTIST") + "\" [" + album.get("catalogId", "NO ID") + "]"
                print(message)
                tray_icon.showMessage("New release!", message)
                download_file(DOWNLOAD_BASE + album.get("_id") + "/download" + DOWNLOAD_FORMATS['MP3_320'], DOWNLOAD_PATH, session)
    else:
        tray_icon.showMessage("Finished.", "No new release found!")
    write_to_file(SAVE_FILE, new_ids)
    print("Finished.")


def load_album_list():
    print("Loading album list...")
    albums_raw = requests.get(RELEASE_API_URL)

    # PARSE RESPONSE INTO JSON
    albums = json.loads(albums_raw.text)
    return albums


def get_album_ids(albums):
    album_ids = []
    for album in albums.get("results"):
        album_ids.append(album.get("_id"))

    return album_ids

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    print(PYQT_VERSION_STR)
    create_directories()
    app = QApplication(sys.argv)
    app.setApplicationName("MonstercatDesktopDownloader")
    parent = QWidget()
    tray_icon = SystemTrayIcon(QIcon('Monstercat.png'), parent)
    tray_icon.setToolTip("MonstercatDesktopDownloader")
    timer = QTimer()
    timer.timeout.connect(lambda: check_new_release(tray_icon, session))
    timer.setInterval(CHECK_INTERVAL)
    timer.start()

    tray_icon.show()

    # INTIALIZE SESSION
    session = requests.Session()
    cj, success = load_cookies(COOKIE_FILE)
    session.cookies = cj
    if not success:
        SignInDialog(session).exec()
    if not check_logged_in(session):
        os.remove(COOKIE_FILE)
        show_popup("ERROR!", "Sign-In Error! Please restart!")
        sys.exit(1)
    sys.exit(app.exec())
