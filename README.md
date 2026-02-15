# Window Always On Top & Crop Tool

A lightweight, native Windows utility that allows you to force any window to stay on top of others and crop it to show only a specific region. It uses native Windows APIs (ctypes) for maximum performance and minimal memory usage.

## Features

- **Always On Top**: Pin any window so it floats above all other applications.
- **Crop View**: Select a specific region of a window to display, hiding the rest (great for monitoring specific data, videos, or game HUDs).
- **Native Performance**: Uses `SetWindowPos` and `SetWindowRgn` directly. No heavy image processing libraries.
- **DPI Aware**: Works correctly on high-resolution screens and multi-monitor setups.
- **Background Mode**: Can be set to run silently in the background on system startup.

## Requirements

- Windows 10 or 11
- [Python 3.x](https://www.python.org/downloads/)
- Administrator privileges (required for system-wide hotkeys and manipulating other windows)

## Installation

1.  Clone this repository or download the files.

2.  Install the required Python dependency:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: The only dependency is `keyboard`)*.

3.  (Optional) Create a virtual environment:
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    ```

## Hotkeys

| Hotkey | Action | Description |
| :--- | :--- | :--- |
| **CTRL + ALT + P** | **Toggle Pin** | Pins or Unpins the currently active window. |
| **CTRL + ALT + C** | **Crop Selection** | Opens an overlay to draw a box. The selected area will be the only visible part of the window. |
| **CTRL + ALT + Q** | **Reset / Unpin** | Resets any applied crop and unpins the window. |

## How to Run

### Manual Run
Double-click `run_as_admin.bat`. This will launch the tool with the necessary Administrator privileges.

### Auto-Start (Run on Startup)
To have the tool run automatically in the background every time you log in:

1.  Open **PowerShell** as **Administrator**.
2.  Navigate to the project folder:
    ```powershell
    cd "E:\Path\To\This\Folder"
    ```
3.  Run the installer script:
    ```powershell
    .\install_autorun.ps1
    ```

The tool will now start silently with Windows. To remove it, run `uninstall_autorun.bat`.

## Troubleshooting

- **"Access Denied" or Hotkeys not working?**
    Ensure you are running the script as **Administrator**. Windows prevents standard programs from interacting with elevated windows (like Task Manager).

- **Crop selection is offset?**
    The script attempts to handle High-DPI scaling automatically. If selection is wrong, ensure your display settings scaling is consistent or restart the script.

## License
MIT License