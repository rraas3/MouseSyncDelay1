
import sys, time, threading
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDoubleSpinBox, QMessageBox
)
from PySide6.QtCore import Qt

if sys.platform != "win32":
    raise SystemExit("Windows 10/11 only")

import win32gui
import win32api
import win32con

class MouseSync(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mouse Sync Delay")
        self.resize(620, 600)
        self.running = False
        self.paused = False
        self.leader = None
        self.targets = []
        self.build_ui()
        self.refresh_windows()

    def build_ui(self):
        l = QVBoxLayout(self)
        l.addWidget(QLabel("<h2>Mouse Sync Delay</h2>"))

        top = QHBoxLayout()
        b = QPushButton("Odśwież okna")
        b.clicked.connect(self.refresh_windows)
        top.addWidget(b)
        self.leader_label = QLabel("Lider: —")
        top.addWidget(self.leader_label)
        l.addLayout(top)

        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.MultiSelection)
        l.addWidget(self.list)

        r = QHBoxLayout()
        r.addWidget(QLabel("Delay między kliknięciami:"))
        self.delay = QDoubleSpinBox()
        self.delay.setRange(0, 60000)
        self.delay.setDecimals(0)
        self.delay.setValue(1000)
        self.delay.setSingleStep(100)
        self.delay.setSuffix(" ms")
        r.addWidget(self.delay)
        l.addLayout(r)

        r = QHBoxLayout()
        b = QPushButton("Ustaw zaznaczone jako lidera")
        b.clicked.connect(self.choose_leader)
        r.addWidget(b)
        b = QPushButton("Ustaw zaznaczone jako cele")
        b.clicked.connect(self.choose_targets)
        r.addWidget(b)
        l.addLayout(r)

        r = QHBoxLayout()
        b = QPushButton("RÓWNO ROZŁÓŻ OKNA")
        b.clicked.connect(self.arrange_windows)
        r.addWidget(b)
        l.addLayout(r)

        r = QHBoxLayout()
        for text, fn in [("START", self.start_sync), ("PAUZA", self.toggle_pause), ("STOP", self.stop_sync)]:
            b = QPushButton(text)
            b.clicked.connect(fn)
            r.addWidget(b)
        l.addLayout(r)

        self.status = QLabel("Status: zatrzymany")
        l.addWidget(self.status)
        l.addWidget(QLabel(
            "Zaznacz okna docelowe i kliknij „RÓWNO ROZŁÓŻ OKNA”. "
            "Program ułoży je automatycznie w równym układzie na ekranie. "
            "Następnie wybierz lidera, cele i START."
        ))

    def refresh_windows(self):
        self.list.clear()
        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title:
                    it = QListWidgetItem(title)
                    it.setData(Qt.UserRole, hwnd)
                    self.list.addItem(it)
        win32gui.EnumWindows(cb, None)

    def selected_hwnds(self):
        return [i.data(Qt.UserRole) for i in self.list.selectedItems()]

    def choose_leader(self):
        hs = self.selected_hwnds()
        if len(hs) != 1:
            QMessageBox.warning(self, "Wybór", "Zaznacz dokładnie jedno okno.")
            return
        self.leader = hs[0]
        self.leader_label.setText("Lider: " + win32gui.GetWindowText(self.leader))

    def choose_targets(self):
        self.targets = [h for h in self.selected_hwnds() if h != self.leader]
        self.status.setText(f"Ustawiono celów: {len(self.targets)}")

    def arrange_windows(self):
        hs = self.selected_hwnds()
        if not hs:
            QMessageBox.warning(self, "Brak okien", "Zaznacz okna, które chcesz rozmieścić.")
            return

        screen = QApplication.primaryScreen().availableGeometry()
        n = len(hs)

        # Choose a near-square grid, then fit all selected windows evenly.
        cols = 1
        while cols * cols < n:
            cols += 1
        rows = (n + cols - 1) // cols

        cell_w = screen.width() // cols
        cell_h = screen.height() // rows

        for i, hwnd in enumerate(hs):
            row, col = divmod(i, cols)
            x = screen.left() + col * cell_w
            y = screen.top() + row * cell_h
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetWindowPos(
                    hwnd, win32con.HWND_TOP, x, y, cell_w, cell_h,
                    win32con.SWP_NOACTIVATE
                )
            except Exception:
                pass

        self.status.setText(f"Rozmieszczono {n} okien w równym układzie.")

    def start_sync(self):
        if not self.leader or not self.targets:
            QMessageBox.warning(self, "Brak konfiguracji",
                                "Ustaw lidera oraz przynajmniej jedno okno docelowe.")
            return
        self.running = True
        self.paused = False
        self.status.setText("Status: DZIAŁA")
        threading.Thread(target=self.loop, daemon=True).start()

    def toggle_pause(self):
        if self.running:
            self.paused = not self.paused
            self.status.setText("Status: PAUZA" if self.paused else "Status: DZIAŁA")

    def stop_sync(self):
        self.running = False
        self.paused = False
        self.status.setText("Status: zatrzymany")

    def loop(self):
        previous = False
        while self.running:
            if self.paused:
                time.sleep(0.02)
                continue

            pressed = bool(win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000)
            if pressed and not previous and self.leader:
                x, y = win32gui.GetCursorPos()
                left, top, right, bottom = win32gui.GetWindowRect(self.leader)
                relx, rely = x - left, y - top

                for hwnd in list(self.targets):
                    if not self.running:
                        break
                    try:
                        wl, wt, wr, wb = win32gui.GetWindowRect(hwnd)
                        # Keep the same relative point, scaled to target size.
                        lw, lh = max(1, right-left), max(1, bottom-top)
                        tw, th = max(1, wr-wl), max(1, wb-wt)
                        tx = wl + int(relx * tw / lw)
                        ty = wt + int(rely * th / lh)
                        win32api.SetCursorPos((tx, ty))
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    except Exception:
                        pass
                    time.sleep(self.delay.value() / 1000.0)

            previous = pressed
            time.sleep(0.008)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MouseSync()
    w.show()
    sys.exit(app.exec())
