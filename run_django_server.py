import os
import subprocess

# Path to your Django project
project_dir = r"C:\Users\Kioscorp\Documents\CAPSTONE\kioscorp_dashboard_backend-1"

# Change the working directory to the project
os.chdir(project_dir)

# Run the Django server
subprocess.Popen(["python", "manage.py", "runserver", "0.0.0.0:8000"], shell=True)
