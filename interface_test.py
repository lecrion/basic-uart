import PyQt5.QtWidgets

app = PyQt5.QtWidgets.QApplication([])
window = PyQt5.QtWidgets.QMainWindow()
window.setWindowTitle("test")
window.setGeometry(100, 100, 400, 300)
window.show()

app.exec_()