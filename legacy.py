

class Downloader(QWidget):
    combobox = None
    grid = None
    selected_file = None
    session = None
    loggedIn = False
    openbutton = None
    save_dir = None
    choose_folder_button = None

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.cookies = http.cookiejar.MozillaCookieJar()
        self.init_ui()

    def init_ui(self):
        self.grid = QGridLayout()
        self.setLayout(self.grid)

        self.combobox = QComboBox()
        download_qualities = [
            ("WAV", "?format=wav"),
            ("MP3 320", "?format=mp3&bitRate=320"),
            ("MP3 V0", "?format=mp3&quality=0"),
            ("MP3 V2", "?format=mp3&quality=2"),
            ("MP3 128", "?format=mp3&bitRate=128"),
            ("FLAC", "?format=flac")
        ]
        for i in range(len(download_qualities)):
            self.combobox.addItem(download_qualities[i][0], download_qualities[i][1])

        self.openbutton = QPushButton("Select file")
        self.openbutton.clicked.connect(self.show_open_file_dialog)

        download_button = QPushButton("Download")
        download_button.clicked.connect(self.download)

        self.choose_folder_button = QPushButton("Select folder")
        self.choose_folder_button.clicked.connect(self.show_select_folder_dialog)

        # ADD WIDGETS
        self.grid.addWidget(QLabel("Select your quality: "), *(1, 1))
        self.grid.addWidget(self.combobox, *(1, 2))
        self.grid.addWidget(QLabel("Please select your JSON file: "), *(2, 1))
        self.grid.addWidget(self.openbutton, *(2, 2))
        self.grid.addWidget(QLabel("Destination folder:"), *(3, 1))
        self.grid.addWidget(self.choose_folder_button, *(3, 2))
        self.grid.addWidget(QLabel(""), *(4, 1))
        self.grid.addWidget(download_button, *(5, 2))

        # MOVE TO CENTER OF SCREEN
        self.move(QDesktopWidget().availableGeometry().center() - self.frameGeometry().center())
        self.setWindowTitle('MonstercatConnectDownloader')
        self.show()

    def show_open_file_dialog(self):
        filepicker = QFileDialog.getOpenFileName(self, 'Open file', os.path.expanduser("~"), "JSON file (*.json)")
        if filepicker[0]:
            self.selected_file = filepicker[0]
            self.openbutton.setText("File selected")
            return True
        else:
            return False

    def show_select_folder_dialog(self):
        # DIALOG WHERE TO SAVE
        self.save_dir = QFileDialog.getExistingDirectory(self, "Select folder to download", os.path.expanduser("~"))
        if not self.save_dir:
            show_popup("Error", "No folder selected.")
            return False
        self.choose_folder_button.setText("Folder selected")
        return True

    def show_sign_in_dialog(self):
        dialog = SignInDialog(self)
        dialog.exec_()

    def download(self):
        # GET FILE
        if not self.selected_file:
            show_popup("Error", "Please select a file first.")
            return False
        if not self.save_dir:
            show_popup("Error", "Please select a destination folder first.")
            return False
        with open(self.selected_file) as f:
            album_ids = json.loads(f.read())

        # GET SELECTED QUALITY
        quality = self.combobox.currentData()

        # LOAD COOKIES IF EXIST
        cj, successful = load_cookies(COOKIE_FILE)
        if successful:
            self.session.cookies = cj
            self.loggedIn = True
            show_popup("Logged in", "Automatically logged in.")

        # GET SESSION
        if not self.loggedIn:
            self.show_sign_in_dialog()

        # CHECK IF LOGIN SUCESSFUL
        if not self.loggedIn:
            show_popup("Error", "Login failed.")
            return
        length = str(len(album_ids))
        bar = QProgressDialog("Downloading songs (1/" + length + ")", "Cancel", 0, int(length))
        bar.setWindowTitle("Downloading songs")
        bar.setValue(0)
        count = 1
        downloadsuccess = True
        # DOWNLOAD
        for album_id in album_ids:
            download_link = DOWNLOAD_BASE + album_id + "/download" + quality
            success = download_file(download_link, self.save_dir, self.session)
            if not success:
                show_popup("Cancelled", "Download was cancelled.")
                downloadsuccess = False
                break

            bar.setValue(count)
            bar.setLabelText("Downloading songs (" + str(count) + "/" + length + ")")
            count += 1
            if bar.wasCanceled():
                show_popup("Cancelled", "Download was cancelled.")
                downloadsuccess = False
                break
            QApplication.processEvents()
            # break     # activate for testing

        if downloadsuccess:
            show_popup("Success!", "Download finished!")
        else:
            show_popup("Finished.", "Finished with errors. Probably cancelled.")


# class MyTableModel(QAbstractTableModel):
#     def __init__(self, datain, parent=None, *args):
#         QAbstractTableModel.__init__(self, parent, *args)
#         self.arraydata = datain
#
#     def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
#         return len(self.arraydata)
#
#     def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
#         return len(self.arraydata[0])
#
#     def data(self, index, int_role=None):
#         if not index.isValid():
#             return QVariant()
#         elif int_role != Qt.DisplayRole:
#             return QVariant()
#         return QVariant(self.arraydata[index.row()][index.column()])
#
#     def data(self, index, role=PyQt5.QtCore.DisplayRole):
#         if role == PyQt5.QtCore.DisplayRole:
#             i = index.row()
#             j = index.column()
#             return '{0}'.format(self.datatable.iget_value(i, j))
#         else:
#             return PyQt5.QtCore.QVariant()
#
#     def flags(self, index):
#         return PyQt5.QtCore.Qt.ItemIsEnabled
