# Pomodoro Reminder

A minimal black & white desktop Pomodoro timer for Windows, built with Python and PyQt6.

![Python](https://img.shields.io/badge/Python-3.10%2B-black?style=flat-square)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-black?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows-black?style=flat-square)

---

## Features

- **Configurable Timer** — Set custom work (1–120 min) and break (1–60 min) durations
- **Start / Stop Controls** — Simple one-click operation
- **Custom Alarm Sound** — Browse and select your own `.mp3`, `.wav`, `.ogg`, `.m4a`, or `.flac` file
- **System Tray Integration** — Minimizes to tray on close or minimize; runs silently in background
- **Tray Notifications** — Get notified when work/break phases change
- **Session Work Tracker** — Tracks total work time per session in `HH:MM:SS`
- **Run at Startup** — Optional Windows startup registration via registry
- **SQLite Config Storage** — Settings persisted in `~/.pomodoro_reminder/config.db`
- **Clean B&W UI** — Monochrome design with no distractions

## Screenshot

```
┌──────────────────────────┐
│        POMODORO           │
│          WORK             │
│        25:00              │
│   Session work: 00:05:00  │
│                           │
│   [▶ START]  [■ STOP]     │
│  ─────────────────────── │
│  Settings                 │
│   Work (min):  [30]       │
│   Break (min): [ 5]       │
│   Alarm: default  [Browse]│
│   ☑ Run at startup        │
└──────────────────────────┘
```

## Requirements

- Python 3.10+
- Windows 10/11

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/PomodoroReminder.git
   cd PomodoroReminder
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**

   ```bash
   python main.py
   ```

## Build Executable

Generate a standalone `.exe` using PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "PomodoroReminder" --icon=NONE main.py
```

The output will be at `dist/PomodoroReminder.exe`.

## Usage

1. Adjust **Work** and **Break** durations in Settings
2. Optionally select a custom **Alarm** sound
3. Click **▶ START** — the app minimizes to the system tray
4. You'll receive a **tray notification** when it's time to take a break or get back to work
5. **Double-click** the tray icon to reopen the window
6. Click **■ STOP** to reset the timer
7. Close or minimize the window — it stays in the tray (right-click tray → **Quit** to exit)

## Project Structure

```
PomodoroReminder/
├── main.py             # Application entry point & UI
├── config.py           # SQLite configuration management
├── requirements.txt    # Python dependencies
├── README.md
└── .gitignore
```

## Configuration

Settings are stored in a SQLite database at:

```
%USERPROFILE%\.pomodoro_reminder\config.db
```

| Key                | Type   | Default | Description                    |
|--------------------|--------|---------|--------------------------------|
| `work_minutes`     | int    | 30      | Work session duration (minutes)|
| `break_minutes`    | int    | 5       | Break duration (minutes)       |
| `alarm_sound_path` | string | ""      | Path to custom alarm sound     |
| `run_at_startup`   | bool   | false   | Enable Windows startup         |

## License

MIT
