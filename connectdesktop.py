#!/usr/bin/python3
import http.cookiejar
import json
import operator
import os
import re
import sys
import requests
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from waitingspinnerwidget import QtWaitingSpinner

DOWNLOAD_FORMATS = dict(
        WAV="?format=wav",
        MP3_320="?format=mp3&bitRate=320",
        MP3_V0="?format=mp3&quality=0",
        MP3_V2="?format=mp3&quality=2",
        MP3_128="?format=mp3&bitRate=128",
        FLAC="?format=flac"
)
SIGNIN_URL = "https://connect.monstercat.com/signin"
DOWNLOAD_BASE = "https://connect.monstercat.com/album/"
HOME_PATH = os.path.expanduser("~") + "/.monstercatconnect/"
COOKIE_FILE = HOME_PATH + "connect.cookies"
TABLE_HEADER_DATA = ['Track', 'Artists', 'Release', '#', 'Length', 'BPM', 'Genres', 'Release Date']

class SignInDialog(QDialog):
    username = None
    password = None
    initiator = None
    checkbox = None

    def __init__(self, initiator):
        super().__init__()
        self.init_ui()
        self.initiator = initiator

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
        response_raw = self.initiator.session.post(SIGNIN_URL, data=payload)
        response = json.loads(response_raw.text)
        if len(response) > 0:
            show_popup("Sign-In failed!", "Sign-In Error: " + response.get("message", "Unknown error"))
            return False
        if self.checkbox.isChecked():
            save_cookies(self.initiator.session.cookies, COOKIE_FILE)
        self.close()
        show_popup("Sign-In successful!", "You are successfully logged in!")
        self.initiator.loggedIn = True
        return True


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
    print("Loading cookies")
    cj = http.cookiejar.MozillaCookieJar()
    if not os.path.isfile(filename):
        return cj, False
    cj.load(filename=filename)
    return cj, True


class MyTableModel(QAbstractTableModel):
    def __init__(self, datain, headerdata, parent=None):
        """ datain: a list of lists
            headerdata: a list of strings
        """
        QAbstractTableModel.__init__(self, parent)
        self.arraydata = datain
        self.headerdata = headerdata

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self.arraydata)

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self.arraydata[0])

    def data(self, index, role=None):
        if not index.isValid():
            return QVariant()
        elif role != Qt.DisplayRole:
            return QVariant()
        return QVariant(self.arraydata[index.row()][index.column()])

    def headerData(self, col, orientation, role=None):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.headerdata[col])
        return QVariant()

    def sort(self, ncol, order=None):
        self.arraydata = sorted(self.arraydata, key=operator.itemgetter(ncol))
        if order == Qt.DescendingOrder:
            self.arraydata.reverse()


def check_logged_in(session):
    response = session.get("https://connect.monstercat.com/session")
    if response.text != "{}":
        return True
    print(response.text)
    return False


class Desktop(QWidget):
    grid = None
    session = None
    loggedIn = False
    table = None
    spinner = None
    thread = None
    obj = None

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.grid = QGridLayout()
        self.setLayout(self.grid)

        # SPINNER
        self.spinner = QtWaitingSpinner(self)
        self.spinner.setMinimumTrailOpacity(15.00)
        self.spinner.setTrailFadePercentage(70.00)
        self.spinner.setRoundness(70.00)
        self.spinner.setNumberOfLines(12)
        self.spinner.setLineLength(10)
        self.spinner.setLineWidth(5)
        self.spinner.setInnerRadius(10)
        self.spinner.setRevolutionsPerSecond(1)
        self.spinner.start()
        self.grid.addWidget(self.spinner, *(1, 1))

        # MOVE TO CENTER OF SCREEN
        self.move(QDesktopWidget().availableGeometry().center() - self.frameGeometry().center())
        self.setWindowTitle('MonstercatConnectDownloader')
        self.setMinimumSize(300, 300)
        self.showMaximized()
        # self.show()

        self.table = QTableView()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(self.play_song)
        # CREATE THREAD
        self.thread = QThread()
        self.obj = Worker()
        self.obj.set_desktop(self)
        self.obj.dataReady.connect(self.tableready)
        self.obj.finished.connect(self.thread.quit)
        self.obj.debugTrackList.connect(self.debugTrackList)
        self.obj.moveToThread(self.thread)
        self.thread.started.connect(self.obj.init_table_and_session)

        # INTIALIZE SESSION
        self.session = requests.Session()
        cj, success = load_cookies(COOKIE_FILE)
        self.session.cookies = cj
        if not success:
            SignInDialog(self).exec()
            # print("signin dialog removed")
            # sys.exit(1)
        if not check_logged_in(self.session):
            show_popup("ERROR!", "Sign-In Error! Please restart")
            sys.exit(1)
        print("starting thread")
        self.thread.start()
        print("started thread")

    def play_song(self, index):
        print(index.row())
        # qmodelindex = self.table.selectedIndexes()
        # print(str(qmodelindex.row()))

    def debugTrackList(self, tracklist):
        print("break-point here")
        # for track in tracklist:
        #     row = [track.get("title", "unknown title"), track.get("artistsTitle", "unknown artists"), "release!!", "tracknr", track.get("duration", "unknown duration"), track.get("bpm", "unknown bpm"), ', '.join(track.get("genres", ["unknown genre"])), track.get("releaseDate", "unknown releaseDate")]
        #     print(row)

    def tableready(self, tracks):
        print("creating model")
        model = MyTableModel(tracks, TABLE_HEADER_DATA)
        print("setting tablemodel")
        self.table.setModel(model)
        print("stopping spinner")
        self.spinner.stop()
        self.table.resizeColumnsToContents()
        print("replacing widget")
        self.grid.replaceWidget(self.spinner, self.table)
        print("replacing finished")
        # self.grid.addWidget(self.table, *(1, 1))


class Worker(QObject):
    finished = pyqtSignal()
    dataReady = pyqtSignal(list)
    debugTrackList = pyqtSignal(list)
    main = None

    def set_desktop(self, param):
        self.main = param

    @pyqtSlot()
    def init_table_and_session(self):
        print("Initializing table")

        tracklist = load_track_list(self.main.session)
        self.debugTrackList.emit(tracklist)
        # INITIALIZE TABLE
        tracks = []
        for track in tracklist:
            row = [track.get("title", "unknown title"), track.get("artistsTitle", "unknown artists"), "release!!", "tracknr", track.get("duration", "unknown duration"), track.get("bpm", "unknown bpm"), ', '.join(track.get("genres", ["unknown genre"])), track.get("releaseDate", "unknown releaseDate")]
            tracks.append(row)

        self.dataReady.emit(tracks)
        print("emitting 'finished'")
        self.finished.emit()


def load_track_list(session):
    # GET TRACK LIST
    print("Loading track list...")
    tracks_raw = session.get("https://connect.monstercat.com/tracks")
    # tracks_raw = session.get("http://localhost/tracks")

    # PARSE RESPONSE INTO JSON
    tracks = json.loads(tracks_raw.text)
    return tracks


if __name__ == '__main__':
    print(PYQT_VERSION_STR)
    app = QApplication(sys.argv)
    main = Desktop()
    sys.exit(app.exec())
