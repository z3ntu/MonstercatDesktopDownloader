# -*- coding: utf-8 -*-
import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


# very testable class (hint: you can use mock.Mock for the signals)
class Worker(QObject):
    finished = pyqtSignal()

    @pyqtSlot()
    def processA(self):
        print("Worker.processA()")
        self.finished.emit()

app = QApplication(sys.argv)

thread = QThread()
obj = Worker()

obj.moveToThread(thread)

obj.finished.connect(thread.quit)

thread.started.connect(obj.processA)
thread.finished.connect(app.exit)

thread.start()

app.exec()
