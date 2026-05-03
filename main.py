"""
Pomodoro Reminder - Desktop Productivity Timer
A simple black & white Pomodoro timer with system tray support.
"""

import sys
import os
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QFileDialog, QSystemTrayIcon,
    QMenu, QCheckBox, QGroupBox, QFrame, QMessageBox, QStyle
)
from PyQt6.QtCore import Qt, QTimer, QSize, QUrl
from PyQt6.QtGui import QIcon, QFont, QAction, QPixmap, QPainter, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from config import load_config, save_config, set_run_at_startup


# ─── Embedded SVG Icon (black circle with white "P") ──────────────────────────

ICON_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <circle cx="32" cy="32" r="30" fill="#111111" stroke="#ffffff" stroke-width="2"/>
  <text x="32" y="42" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="36" font-weight="bold" fill="#ffffff">P</text>
</svg>"""


def create_app_icon() -> QIcon:
    """Create a simple app icon programmatically."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Black circle
    painter.setBrush(QColor("#111111"))
    painter.setPen(QColor("#ffffff"))
    painter.drawEllipse(2, 2, 60, 60)

    # White "P" letter
    font = QFont("Arial", 32, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "P")
    painter.end()
    return QIcon(pixmap)


# ─── Stylesheet ───────────────────────────────────────────────────────────────

STYLESHEET = """
QMainWindow, QWidget {
    background-color: #fafafa;
    color: #111111;
    font-family: "Segoe UI", "Arial", sans-serif;
}

QLabel {
    color: #111111;
}

QLabel#titleLabel {
    font-size: 22px;
    font-weight: bold;
    letter-spacing: 2px;
    padding: 8px 0;
}

QLabel#timerLabel {
    font-size: 72px;
    font-weight: bold;
    font-family: "Consolas", "Courier New", monospace;
    padding: 16px 0;
    border: 2px solid #111111;
    border-radius: 12px;
    background-color: #ffffff;
    min-width: 300px;
}

QLabel#phaseLabel {
    font-size: 16px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 4px;
}

QLabel#phaseLabel[phase="work"] {
    background-color: #111111;
    color: #ffffff;
}

QLabel#phaseLabel[phase="break"] {
    background-color: #cccccc;
    color: #111111;
}

QLabel#phaseLabel[phase="idle"] {
    background-color: #eeeeee;
    color: #666666;
}

QPushButton {
    font-size: 14px;
    font-weight: 600;
    padding: 10px 28px;
    border: 2px solid #111111;
    border-radius: 8px;
    background-color: #ffffff;
    color: #111111;
    min-width: 100px;
}

QPushButton:hover {
    background-color: #111111;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #333333;
    color: #ffffff;
}

QPushButton#startBtn {
    background-color: #111111;
    color: #ffffff;
    border-color: #111111;
}

QPushButton#startBtn:hover {
    background-color: #333333;
    border-color: #333333;
}

QPushButton#stopBtn {
    background-color: #ffffff;
    color: #cc0000;
    border-color: #cc0000;
}

QPushButton#stopBtn:hover {
    background-color: #cc0000;
    color: #ffffff;
}

QGroupBox {
    font-size: 13px;
    font-weight: bold;
    border: 1.5px solid #cccccc;
    border-radius: 8px;
    margin-top: 14px;
    padding: 18px 12px 12px 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    color: #111111;
}

QSpinBox {
    font-size: 14px;
    padding: 6px 10px;
    border: 1.5px solid #cccccc;
    border-radius: 6px;
    background-color: #ffffff;
    min-width: 80px;
}

QSpinBox:focus {
    border-color: #111111;
}

QCheckBox {
    font-size: 13px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1.5px solid #999999;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #111111;
    border-color: #111111;
}

QFrame#separator {
    background-color: #dddddd;
    max-height: 1px;
}

QPushButton#soundBtn {
    font-size: 12px;
    padding: 6px 14px;
    min-width: 60px;
}

QLabel#soundPathLabel {
    font-size: 11px;
    color: #888888;
    font-style: italic;
}
"""


class PomodoroApp(QMainWindow):
    """Main Pomodoro Reminder application window."""

    def __init__(self):
        super().__init__()

        # ── Load config ────────────────────────────────────────────────
        self.config = load_config()

        # ── State ──────────────────────────────────────────────────────
        self.is_running = False
        self.is_work_phase = True
        self.remaining_seconds = 0
        self.total_work_seconds_today = 0  # Track total work time in session

        # ── Timer ──────────────────────────────────────────────────────
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(1000)
        self.tick_timer.timeout.connect(self._on_tick)

        # ── Audio ──────────────────────────────────────────────────────
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)

        # ── UI ─────────────────────────────────────────────────────────
        self._build_ui()
        self._build_tray()
        self._apply_config()

        # ── Window settings ────────────────────────────────────────────
        self.setWindowTitle("Pomodoro Reminder")
        self.setFixedSize(420, 580)
        self.setWindowIcon(create_app_icon())

    # ═══════════════════════════════════════════════════════════════════
    # UI Construction
    # ═══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        """Build the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # ── Title ──────────────────────────────────────────────────────
        title = QLabel("POMODORO")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ── Phase indicator ────────────────────────────────────────────
        self.phase_label = QLabel("IDLE")
        self.phase_label.setObjectName("phaseLabel")
        self.phase_label.setProperty("phase", "idle")
        self.phase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.phase_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── Timer display ──────────────────────────────────────────────
        self.timer_label = QLabel("30:00")
        self.timer_label.setObjectName("timerLabel")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.timer_label)

        # ── Total work time display ────────────────────────────────────
        self.total_work_label = QLabel("Session work: 00:00:00")
        self.total_work_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_work_label.setStyleSheet("font-size: 12px; color: #888888;")
        layout.addWidget(self.total_work_label)

        # ── Buttons ────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.start_btn = QPushButton("▶  START")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("■  STOP")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)

        # ── Separator ─────────────────────────────────────────────────
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # ── Settings group ────────────────────────────────────────────
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(10)

        # Work duration
        work_row = QHBoxLayout()
        work_row.addWidget(QLabel("Work (min):"))
        self.work_spin = QSpinBox()
        self.work_spin.setRange(1, 120)
        self.work_spin.setValue(30)
        self.work_spin.valueChanged.connect(self._on_settings_changed)
        work_row.addWidget(self.work_spin)
        work_row.addStretch()
        settings_layout.addLayout(work_row)

        # Break duration
        break_row = QHBoxLayout()
        break_row.addWidget(QLabel("Break (min):"))
        self.break_spin = QSpinBox()
        self.break_spin.setRange(1, 60)
        self.break_spin.setValue(5)
        self.break_spin.valueChanged.connect(self._on_settings_changed)
        break_row.addWidget(self.break_spin)
        break_row.addStretch()
        settings_layout.addLayout(break_row)

        # Alarm sound
        sound_row = QHBoxLayout()
        sound_row.addWidget(QLabel("Alarm:"))
        self.sound_path_label = QLabel("Default beep")
        self.sound_path_label.setObjectName("soundPathLabel")
        sound_row.addWidget(self.sound_path_label, 1)

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setObjectName("soundBtn")
        self.browse_btn.clicked.connect(self._on_browse_sound)
        sound_row.addWidget(self.browse_btn)

        self.clear_sound_btn = QPushButton("Reset")
        self.clear_sound_btn.setObjectName("soundBtn")
        self.clear_sound_btn.clicked.connect(self._on_clear_sound)
        sound_row.addWidget(self.clear_sound_btn)

        settings_layout.addLayout(sound_row)

        # Run at startup
        self.startup_check = QCheckBox("Run at Windows startup")
        self.startup_check.stateChanged.connect(self._on_startup_changed)
        settings_layout.addWidget(self.startup_check)

        layout.addWidget(settings_group)
        layout.addStretch()

    def _build_tray(self):
        """Build the system tray icon and menu."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(create_app_icon())
        self.tray_icon.setToolTip("Pomodoro Reminder")

        tray_menu = QMenu()

        self.tray_show_action = QAction("Show", self)
        self.tray_show_action.triggered.connect(self._show_window)
        tray_menu.addAction(self.tray_show_action)

        tray_menu.addSeparator()

        self.tray_start_action = QAction("Start", self)
        self.tray_start_action.triggered.connect(self._on_start)
        tray_menu.addAction(self.tray_start_action)

        self.tray_stop_action = QAction("Stop", self)
        self.tray_stop_action.triggered.connect(self._on_stop)
        self.tray_stop_action.setEnabled(False)
        tray_menu.addAction(self.tray_stop_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    # ═══════════════════════════════════════════════════════════════════
    # Config
    # ═══════════════════════════════════════════════════════════════════

    def _apply_config(self):
        """Apply loaded config to UI."""
        self.work_spin.setValue(self.config.get("work_minutes", 30))
        self.break_spin.setValue(self.config.get("break_minutes", 5))
        self.startup_check.setChecked(self.config.get("run_at_startup", False))

        sound_path = self.config.get("alarm_sound_path", "")
        if sound_path and os.path.exists(sound_path):
            self.sound_path_label.setText(os.path.basename(sound_path))
        else:
            self.sound_path_label.setText("Default beep")
            self.config["alarm_sound_path"] = ""

        self._update_timer_display(self.config.get("work_minutes", 30) * 60)

    def _save_current_config(self):
        """Save current settings to config file."""
        self.config["work_minutes"] = self.work_spin.value()
        self.config["break_minutes"] = self.break_spin.value()
        self.config["run_at_startup"] = self.startup_check.isChecked()
        save_config(self.config)

    # ═══════════════════════════════════════════════════════════════════
    # Timer Logic
    # ═══════════════════════════════════════════════════════════════════

    def _on_start(self):
        """Start or resume the Pomodoro timer."""
        if self.is_running:
            return

        self.is_running = True
        self.is_work_phase = True
        self.remaining_seconds = self.work_spin.value() * 60

        self._set_phase("WORK", "work")
        self._update_timer_display(self.remaining_seconds)
        self._toggle_buttons(running=True)

        self.tick_timer.start()

        # Minimize to tray when starting
        self.hide()
        self.tray_icon.showMessage(
            "Pomodoro Started",
            f"Work session: {self.work_spin.value()} minutes",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def _on_stop(self):
        """Stop the timer and reset."""
        self.is_running = False
        self.tick_timer.stop()

        self._set_phase("IDLE", "idle")
        self._update_timer_display(self.work_spin.value() * 60)
        self._toggle_buttons(running=False)

    def _on_tick(self):
        """Handle each timer tick (1 second)."""
        if not self.is_running:
            return

        # Track work time
        if self.is_work_phase:
            self.total_work_seconds_today += 1
            self._update_total_work_display()

        self.remaining_seconds -= 1

        if self.remaining_seconds <= 0:
            self._on_phase_complete()
        else:
            self._update_timer_display(self.remaining_seconds)
            # Update tray tooltip with remaining time
            mins, secs = divmod(self.remaining_seconds, 60)
            phase_name = "Work" if self.is_work_phase else "Break"
            self.tray_icon.setToolTip(f"Pomodoro - {phase_name}: {mins:02d}:{secs:02d}")

    def _on_phase_complete(self):
        """Handle phase completion (work → break or break → work)."""
        self.tick_timer.stop()
        self._play_alarm()

        if self.is_work_phase:
            # Work phase done → start break
            self.is_work_phase = False
            self.remaining_seconds = self.break_spin.value() * 60
            self._set_phase("BREAK", "break")

            self.tray_icon.showMessage(
                "Break Time! ☕",
                f"Take a {self.break_spin.value()} minute break.",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
        else:
            # Break phase done → start work
            self.is_work_phase = True
            self.remaining_seconds = self.work_spin.value() * 60
            self._set_phase("WORK", "work")

            self.tray_icon.showMessage(
                "Back to Work! 💪",
                f"Work session: {self.work_spin.value()} minutes",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )

        self._update_timer_display(self.remaining_seconds)
        self.tick_timer.start()

    # ═══════════════════════════════════════════════════════════════════
    # UI Helpers
    # ═══════════════════════════════════════════════════════════════════

    def _update_timer_display(self, total_seconds: int):
        """Update the timer label with MM:SS format."""
        mins, secs = divmod(max(0, total_seconds), 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def _update_total_work_display(self):
        """Update the total work time display."""
        hrs, remainder = divmod(self.total_work_seconds_today, 3600)
        mins, secs = divmod(remainder, 60)
        self.total_work_label.setText(f"Session work: {hrs:02d}:{mins:02d}:{secs:02d}")

    def _set_phase(self, text: str, phase_key: str):
        """Update the phase label text and style."""
        self.phase_label.setText(text)
        self.phase_label.setProperty("phase", phase_key)
        # Force style refresh
        self.phase_label.style().unpolish(self.phase_label)
        self.phase_label.style().polish(self.phase_label)

    def _toggle_buttons(self, running: bool):
        """Toggle button enabled states."""
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.work_spin.setEnabled(not running)
        self.break_spin.setEnabled(not running)

        # Tray actions
        self.tray_start_action.setEnabled(not running)
        self.tray_stop_action.setEnabled(running)

    # ═══════════════════════════════════════════════════════════════════
    # Alarm / Sound
    # ═══════════════════════════════════════════════════════════════════

    def _play_alarm(self):
        """Play the alarm sound."""
        sound_path = self.config.get("alarm_sound_path", "")

        if sound_path and os.path.exists(sound_path):
            url = QUrl.fromLocalFile(sound_path)
            self.media_player.setSource(url)
            self.media_player.play()
        else:
            # Fallback: system beep
            QApplication.beep()

    def _on_browse_sound(self):
        """Open file dialog to select alarm sound."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Alarm Sound",
            "",
            "Audio Files (*.mp3 *.wav *.ogg *.m4a *.flac);;All Files (*)"
        )
        if path:
            self.config["alarm_sound_path"] = path
            self.sound_path_label.setText(os.path.basename(path))
            self._save_current_config()

    def _on_clear_sound(self):
        """Reset alarm sound to default beep."""
        self.config["alarm_sound_path"] = ""
        self.sound_path_label.setText("Default beep")
        self._save_current_config()

    # ═══════════════════════════════════════════════════════════════════
    # Settings callbacks
    # ═══════════════════════════════════════════════════════════════════

    def _on_settings_changed(self):
        """Handle work/break spin changes."""
        if not self.is_running:
            self._update_timer_display(self.work_spin.value() * 60)
        self._save_current_config()

    def _on_startup_changed(self, state):
        """Handle startup checkbox toggle."""
        enabled = self.startup_check.isChecked()
        self.config["run_at_startup"] = enabled
        set_run_at_startup(enabled)
        self._save_current_config()

    # ═══════════════════════════════════════════════════════════════════
    # Tray / Window
    # ═══════════════════════════════════════════════════════════════════

    def _on_tray_activated(self, reason):
        """Handle tray icon activation (double-click to show)."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        """Show and activate the main window."""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_app(self):
        """Fully quit the application."""
        self.tray_icon.hide()
        QApplication.instance().quit()

    # ═══════════════════════════════════════════════════════════════════
    # Window Events
    # ═══════════════════════════════════════════════════════════════════

    def closeEvent(self, event):
        """Override close to minimize to tray instead of quitting."""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Pomodoro Reminder",
            "App minimized to tray. Double-click to reopen.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def changeEvent(self, event):
        """Override minimize to hide to tray."""
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                # Delay hide so Qt finishes processing the state change
                QTimer.singleShot(0, self.hide)


# ═══════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray

    window = PomodoroApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
