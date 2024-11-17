import os
import subprocess
import signal
import time
import psutil
import socket
import win32api
import win32con
import win32gui
import sys

# Path to your Django project
project_dir = r"C:\Users\Kioscorp\Documents\CAPSTONE\kioscorp_dashboard_backend-1"

# Change the working directory to the project
os.chdir(project_dir)

# Define the port for the Django server
DJANGO_PORT = 8000


def is_port_open(port):
    """Check if a specific port is open (i.e., if a process is listening on it)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(("127.0.0.1", port))
        return result == 0


def start_django_server():
    """Start the Django server."""
    print("Starting Django server...")
    # Start the server in a new process but do not show the script itself
    return subprocess.Popen(
        ["python", "manage.py", "runserver", f"0.0.0.0:{DJANGO_PORT}"], shell=True
    )


def is_django_running(process_name="python.exe"):
    """Check if Django server process is running."""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        if (
            process_name in proc.info["name"].lower()
            and "manage.py" in str(proc.info["cmdline"]).lower()
        ):
            return True
    return False


def shutdown_server(signal, frame):
    """Gracefully shut down the server."""
    print("Shutting down Django server...")
    if django_process:
        django_process.terminate()
        django_process.wait()  # Ensure it has fully terminated
    print("Django server shutdown complete.")


def handle_shutdown():
    """Handle Windows shutdown or restart."""
    print("Shutdown or restart detected. Gracefully shutting down the Django server...")
    shutdown_server(None, None)


# Hook the Windows shutdown event
win32api.SetConsoleCtrlHandler(lambda ctrl_type: True, True)

# Set up signal handlers for graceful shutdown
signal.signal(signal.SIGINT, shutdown_server)
signal.signal(signal.SIGTERM, shutdown_server)

if __name__ == "__main__":
    # Start the Django server only if it's not already running and the port is not open
    if not is_django_running() and not is_port_open(DJANGO_PORT):
        django_process = start_django_server()
    elif is_port_open(DJANGO_PORT):
        print(f"Django server is already running on port {DJANGO_PORT}.")
    else:
        print("Django server is already running.")

    # Monitor the server process
    try:
        while True:
            # Check if Django is running; if not, restart it
            if not is_django_running() and not is_port_open(DJANGO_PORT):
                print(
                    "Django server has been terminated or port is unavailable. Restarting..."
                )
                django_process = start_django_server()

            time.sleep(5)  # Check every 5 seconds

    except KeyboardInterrupt:
        shutdown_server(None, None)
