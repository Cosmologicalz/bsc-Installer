import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import requests
import zipfile
import shutil
import subprocess
import threading
import time
from packaging.version import parse as parse_version # Using packaging.version for robust comparison

# Define constants for GitHub repositories and release files
BSI_REPO_OWNER = "Cosmologicalz"
BSI_REPO_NAME = "Beammp-server-creator"
INSTALLER_REPO_OWNER = "Cosmologicalz"
INSTALLER_REPO_NAME = "bsc-Installer"

BSI_ZIP_URL_FORMAT = f"https://github.com/{BSI_REPO_OWNER}/{BSI_REPO_NAME}/archive/refs/tags/{{version}}.zip"
BEAMMP_SERVER_EXE_URL = "https://github.com/BeamMP/BeamMP-Server/releases/latest/download/BeamMP-Server.exe"

CURRENT_INSTALLER_VERSION = "v0.4" # This installer's version

class BSIInstaller(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"BSI Installer - {CURRENT_INSTALLER_VERSION}")
        self.geometry("750x500") 
        self.resizable(False, False)
        self.iconbitmap(default='')

        # Configure style for better aesthetics
        self.style = ttk.Style(self)
        self.style.theme_use('clam') # 'clam', 'alt', 'default', 'classic'
        self.style.configure('TProgressbar', thickness=25, background='#4CAF50', troughcolor='#e0e0e0', bordercolor='#d0d0d0', lightcolor='#d0d0d0', darkcolor='#d0d0d0')
        self.style.map('TProgressbar',
                       background=[('active', '#4CAF50')])
        
        # Variables
        self.install_path = tk.StringVar(self)
        self.delete_zip_var = tk.BooleanVar(self, value=True)
        self.create_server_var = tk.BooleanVar(self, value=False)
        self.default_install_path = os.path.join(os.path.expanduser("~"), "Documents", "Beam Server")
        self.install_path.set(self.default_install_path)

        # Update status variables
        self.bsi_update_available = False
        self.installer_update_available = False
        self.latest_bsi_version = None
        self.latest_installer_version = None
        self.current_bsc_version = None
        self.current_installer_installed_version = None # Version of the installer that's part of the Beam Server installation

        # Configure grid for the main window to ensure frames fill it
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frames = {}
        self.create_frames()
        self.show_frame("WelcomePage")

        # Start update check in a separate thread
        self.after(100, self.start_update_check) # Small delay to allow GUI to render

    def create_frames(self):
        welcome_frame = WelcomePage(self, self)
        self.frames["WelcomePage"] = welcome_frame
        welcome_frame.grid(row=0, column=0, sticky="nsew")

        install_options_frame = InstallOptionsPage(self, self)
        self.frames["InstallOptionsPage"] = install_options_frame
        install_options_frame.grid(row=0, column=0, sticky="nsew")

        install_progress_frame = InstallProgressPage(self, self)
        self.frames["InstallProgressPage"] = install_progress_frame
        install_progress_frame.grid(row=0, column=0, sticky="nsew")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

    def start_installation(self):
        progress_page = self.frames["InstallProgressPage"]
        progress_page.reset_status()
        progress_page.update_status("Starting installation...", 0)

        installation_thread = threading.Thread(target=self._run_installation, args=(progress_page,))
        installation_thread.start()

    def _run_installation(self, progress_page):
        install_base_path = self.install_path.get()
        beam_server_path = os.path.join(install_base_path, "Beam Server")
        bsi_folder_path = os.path.join(beam_server_path, "BSI")
        
        # Use a placeholder for BSI_ZIP_URL_FORMAT as the version is dynamic or from the latest release
        # For initial install, we'll use the version requested in the previous prompt v0.2.3.3
        bsi_zip_url = BSI_ZIP_URL_FORMAT.format(version="v0.2.3.3") # Default for initial install
        bsi_zip_filename = os.path.join(beam_server_path, "Beammp-server-creator-v0.2.3.3.zip") # Specific filename

        try:
            # 1. Create main folder: Beam Server
            progress_page.update_status("Creating 'Beam Server' folder...", 5)
            os.makedirs(beam_server_path, exist_ok=True)

            # 2. Create other folder: BSI inside Beam Server
            progress_page.update_status("Creating 'BSI' folder...", 10)
            os.makedirs(bsi_folder_path, exist_ok=True)

            # 3. Download BSI zipfile
            progress_page.update_status(f"Downloading BSI zipfile from {bsi_zip_url}...", 20)
            try:
                response = requests.get(bsi_zip_url, stream=True)
                response.raise_for_status() 
                with open(bsi_zip_filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            except requests.exceptions.RequestException as e:
                progress_page.update_status(f"Error downloading BSI zip: {e}", 100, error=True)
                messagebox.showerror("Download Error", f"Failed to download BSI zip from '{bsi_zip_url}'. Please ensure the repository is public.")
                return 

            # 4. Extract the zip file in the main folder
            progress_page.update_status("Extracting BSI zipfile...", 40)
            try:
                # The extracted folder name will be 'Beammp-server-creator-X.Y.Z'
                with zipfile.ZipFile(bsi_zip_filename, 'r') as zip_ref:
                    # Find the root folder inside the zip (e.g., Beammp-server-creator-0.2.3.3)
                    # We want to extract content of this folder directly into beam_server_path
                    for member in zip_ref.namelist():
                        if member.startswith(f"{BSI_REPO_NAME}-") and member.endswith('/'):
                            # This is the root folder. Extract its contents.
                            # Skip the root folder itself to avoid nested directory
                            continue 
                        
                        source = zip_ref.open(member)
                        target_path = os.path.join(beam_server_path, os.path.relpath(member, os.path.commonpath([m for m in zip_ref.namelist() if m.startswith(f"{BSI_REPO_NAME}-")])))
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with open(target_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                        source.close()


            except zipfile.BadZipFile:
                progress_page.update_status("Error: Downloaded BSI zip is corrupted.", 100, error=True)
                messagebox.showerror("Extraction Error", "Downloaded BSI zip file is corrupted.")
                return
            except Exception as e:
                progress_page.update_status(f"Error during BSI zip extraction: {e}", 100, error=True)
                messagebox.showerror("Extraction Error", f"An error occurred during BSI zip extraction: {e}")
                return

            # 5. Delete zipfile or move it into the BSI folder
            progress_page.update_status("Handling BSI zipfile...", 50)
            if self.delete_zip_var.get():
                os.remove(bsi_zip_filename)
                progress_page.update_status("Deleted BSI zipfile.", 55)
            else:
                shutil.move(bsi_zip_filename, os.path.join(bsi_folder_path, os.path.basename(bsi_zip_filename)))
                progress_page.update_status("Moved BSI zipfile to BSI folder.", 55)

            # 6. If the checkbox to create a server
            if self.create_server_var.get():
                progress_page.update_status("Setting up BeamMP server...", 60)
                server1_folder_path = os.path.join(beam_server_path, "Server 1")
                resource_folder_path = os.path.join(server1_folder_path, "Resource")
                client_folder_path = os.path.join(resource_folder_path, "Client")

                os.makedirs(server1_folder_path, exist_ok=True)
                os.makedirs(resource_folder_path, exist_ok=True)
                os.makedirs(client_folder_path, exist_ok=True)

                beammp_exe_dest = os.path.join(server1_folder_path, "BeamMP-Server.exe")
                progress_page.update_status("Downloading BeamMP-Server.exe...", 65)
                try:
                    response = requests.get(BEAMMP_SERVER_EXE_URL, stream=True)
                    response.raise_for_status()
                    with open(beammp_exe_dest, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                except requests.exceptions.RequestException as e:
                    progress_page.update_status(f"Error downloading BeamMP-Server.exe: {e}", 100, error=True)
                    messagebox.showerror("Download Error", f"Failed to download BeamMP-Server.exe: {e}")
                    return

                # Open it up silently so it creates its stuff.
                progress_page.update_status("Running BeamMP-Server.exe to initialize...", 75)
                try:
                    if os.name == 'nt':
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startupinfo.wShowWindow = subprocess.SW_HIDE
                        process = subprocess.Popen([beammp_exe_dest], cwd=server1_folder_path, startupinfo=startupinfo)
                    else:
                        process = subprocess.Popen([beammp_exe_dest], cwd=server1_folder_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    time.sleep(2)
                    process.terminate()
                    process.wait()
                except Exception as e:
                    progress_page.update_status(f"Error running BeamMP-Server.exe: {e}", 100, error=True)
                    messagebox.showerror("Execution Error", f"Failed to run BeamMP-Server.exe: {e}")
                    return

                # Create a shortcut
                progress_page.update_status("Creating BeamMP-Server shortcut...", 85)
                shortcut_path = os.path.join(beam_server_path, "Start BeamMP Server.bat" if os.name == 'nt' else "start_beammp_server.sh")
                with open(shortcut_path, 'w') as f:
                    if os.name == 'nt':
                        f.write(f'@echo off\ncd "{server1_folder_path}"\n"{os.path.basename(beammp_exe_dest)}"\npause')
                    else:
                        f.write(f'#!/bin/bash\ncd "{server1_folder_path}"\n./"{os.path.basename(beammp_exe_dest)}"\nread -p "Press Enter to continue..."')
                if os.name != 'nt':
                    os.chmod(shortcut_path, 0o755)

                progress_page.update_status("Verifying BeamMP-Server files...", 90)
                if not os.path.exists(beammp_exe_dest):
                    progress_page.update_status("Error: BeamMP-Server.exe not found where expected.", 100, error=True)
                    messagebox.showerror("Verification Error", "BeamMP-Server.exe was not found in 'Server 1' folder.")
                    return

                server_config_main_path = os.path.join(beam_server_path, "ServerConfig.toml")
                server_config_server1_path = os.path.join(server1_folder_path, "ServerConfig.toml")
                if os.path.exists(server_config_main_path) and not os.path.exists(server_config_server1_path):
                    shutil.move(server_config_main_path, server_config_server1_path)
                    progress_page.update_status("Moved ServerConfig.toml to 'Server 1' folder.", 95)

                if not os.path.exists(shortcut_path):
                    progress_page.update_status("Error: Shortcut not found where expected.", 100, error=True)
                    messagebox.showerror("Verification Error", "The 'Start BeamMP Server' shortcut was not created.")
                    return
            
            # Write/Update release.txt after successful installation
            self.write_release_file("v0.2.3.3", CURRENT_INSTALLER_VERSION) # Assuming BSI installed is v0.2.3.3 initially
            
            progress_page.update_status("Installation complete!", 100, success=True)
            messagebox.showinfo("Installation Complete", "BSI and BeamMP Server (if selected) have been installed successfully!")

        except Exception as e:
            progress_page.update_status(f"An error occurred: {e}", 100, error=True)
            messagebox.showerror("Installation Error", f"An unexpected error occurred during installation: {e}")

    def get_release_file_path(self):
        # The release.txt file will be in the 'Beam Server' main folder
        install_base_path = self.install_path.get()
        beam_server_path = os.path.join(install_base_path, "Beam Server")
        return os.path.join(beam_server_path, "release.txt")

    def read_release_file(self):
        release_file_path = self.get_release_file_path()
        bsc_version = None
        installer_version = None
        if os.path.exists(release_file_path):
            try:
                with open(release_file_path, 'r') as f:
                    for line in f:
                        if line.startswith("BSC_Current_Version ="):
                            bsc_version = line.split('=')[1].strip()
                        elif line.startswith("BSC_installer_Current_version ="):
                            installer_version = line.split('=')[1].strip()
            except Exception as e:
                print(f"Error reading release.txt: {e}")
        return bsc_version, installer_version

    def write_release_file(self, bsc_version, installer_version):
        release_file_path = self.get_release_file_path()
        try:
            # Ensure the directory exists before writing the file
            os.makedirs(os.path.dirname(release_file_path), exist_ok=True)
            with open(release_file_path, 'w') as f:
                f.write(f"BSC_Current_Version = {bsc_version}\n")
                f.write(f"BSC_installer_Current_version = {installer_version}\n")
        except Exception as e:
            print(f"Error writing release.txt: {e}")

    def get_latest_github_release_tag(self, repo_owner, repo_name):
        api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            latest_release_data = response.json()
            return latest_release_data.get("tag_name")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching latest release for {repo_owner}/{repo_name}: {e}")
            return None

    def start_update_check(self):
        threading.Thread(target=self._run_update_check).start()

    def _run_update_check(self):
        # Read installed versions
        self.current_bsc_version, self.current_installer_installed_version = self.read_release_file()

        # Get latest GitHub versions
        self.latest_bsi_version = self.get_latest_github_release_tag(BSI_REPO_OWNER, BSI_REPO_NAME)
        self.latest_installer_version = self.get_latest_github_release_tag(INSTALLER_REPO_OWNER, INSTALLER_REPO_NAME)

        self.bsi_update_available = False
        self.installer_update_available = False

        if self.latest_bsi_version and self.current_bsc_version:
            try:
                if parse_version(self.latest_bsi_version) > parse_version(self.current_bsc_version):
                    self.bsi_update_available = True
            except Exception as e:
                print(f"Error comparing BSI versions: {e}")
                
        # Compare current running installer version to latest GitHub installer version
        # The installer's own version is CURRENT_INSTALLER_VERSION
        if self.latest_installer_version:
            try:
                if parse_version(self.latest_installer_version) > parse_version(CURRENT_INSTALLER_VERSION):
                    self.installer_update_available = True
            except Exception as e:
                print(f"Error comparing installer versions: {e}")

        # Update UI indicator on main thread
        self.after(10, self.frames["WelcomePage"].update_update_indicator)

    def show_update_dialog(self):
        update_text = "Checking for updates...\n"

        if self.bsi_update_available or self.installer_update_available:
            update_text = "Updates available!\n\n"
            if self.bsi_update_available:
                update_text += f"BSI (BeamMP Server Creator): Installed {self.current_bsc_version}, Latest {self.latest_bsi_version}\n"
            if self.installer_update_available:
                update_text += f"BSI Installer: Installed {CURRENT_INSTALLER_VERSION}, Latest {self.latest_installer_version}\n"
            update_text += "\nDo you want to proceed with the update?"
            
            response = messagebox.askyesno("Update Available", update_text)
            if response:
                self.start_perform_update()
        else:
            update_text = "No updates found. Your applications are up to date."
            messagebox.showinfo("No Updates", update_text)

    def start_perform_update(self):
        progress_page = self.frames["InstallProgressPage"]
        self.show_frame("InstallProgressPage") # Switch to progress page
        progress_page.reset_status()
        progress_page.update_status("Starting update process...", 0)

        threading.Thread(target=self._run_perform_update, args=(progress_page,)).start()

    def _run_perform_update(self, progress_page):
        try:
            update_success = True

            if self.bsi_update_available:
                progress_page.update_status(f"Updating BSI (BeamMP Server Creator) to {self.latest_bsi_version}...", 10)
                bsi_zip_url_to_download = BSI_ZIP_URL_FORMAT.format(version=self.latest_bsi_version)
                install_base_path = self.install_path.get()
                beam_server_path = os.path.join(install_base_path, "Beam Server")
                bsi_zip_filename = os.path.join(beam_server_path, f"{BSI_REPO_NAME}-{self.latest_bsi_version}.zip")

                try:
                    response = requests.get(bsi_zip_url_to_download, stream=True)
                    response.raise_for_status()
                    with open(bsi_zip_filename, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    progress_page.update_status("BSI zip downloaded.", 20)

                    # Extract the zip file, replacing existing BSI files
                    progress_page.update_status("Extracting new BSI files...", 30)
                    with zipfile.ZipFile(bsi_zip_filename, 'r') as zip_ref:
                         for member in zip_ref.namelist():
                            if member.startswith(f"{BSI_REPO_NAME}-") and member.endswith('/'):
                                continue 
                            
                            source = zip_ref.open(member)
                            target_path = os.path.join(beam_server_path, os.path.relpath(member, os.path.commonpath([m for m in zip_ref.namelist() if m.startswith(f"{BSI_REPO_NAME}-")])))
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            with open(target_path, "wb") as target:
                                shutil.copyfileobj(source, target)
                            source.close()
                    progress_page.update_status("BSI extracted.", 40)
                    os.remove(bsi_zip_filename) # Clean up downloaded zip

                    self.write_release_file(self.latest_bsi_version, self.current_installer_installed_version or CURRENT_INSTALLER_VERSION)
                    progress_page.update_status("BSI updated successfully!", 50)
                except requests.exceptions.RequestException as e:
                    progress_page.update_status(f"Error updating BSI: {e}", 100, error=True)
                    messagebox.showerror("Update Error", f"Failed to update BSI: {e}")
                    update_success = False
                except Exception as e:
                    progress_page.update_status(f"Error extracting BSI update: {e}", 100, error=True)
                    messagebox.showerror("Update Error", f"An error occurred during BSI extraction: {e}")
                    update_success = False

            if self.installer_update_available and update_success: # Only proceed if BSI updated successfully or no BSI update needed
                progress_page.update_status(f"Updating BSI Installer to {self.latest_installer_version}...", 60)
                installer_zip_url_to_download = BSI_ZIP_URL_FORMAT.format(version=self.latest_installer_version) # Assuming installer is packaged same way as BSI
                
                # If the installer is a single .py file, we need a different download path.
                # Let's assume the installer's source is downloaded as a zip, and we are looking for the main .py file
                # A more robust self-update mechanism usually involves a bootstrap script or dedicated installer builder.
                # For this example, we'll download the new script and prompt the user to restart.

                new_installer_script_url = f"https://raw.githubusercontent.com/{INSTALLER_REPO_OWNER}/{INSTALLER_REPO_NAME}/{self.latest_installer_version}/bsi_installer.py"
                temp_new_installer_path = os.path.join(os.path.dirname(__file__), "new_bsi_installer.py")
                
                try:
                    response = requests.get(new_installer_script_url, stream=True)
                    response.raise_for_status()
                    with open(temp_new_installer_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    progress_page.update_status("New installer script downloaded.", 80)

                    self.write_release_file(self.current_bsc_version or self.latest_bsi_version, self.latest_installer_version) # Update installed installer version

                    progress_page.update_status("Installer update downloaded. Please restart the application to use the new version.", 90, success=True)
                    messagebox.showinfo("Installer Update", "The new installer version has been downloaded. Please close this installer and run 'new_bsi_installer.py' (or your original installer script if it was updated in place) to complete the update.")
                    
                    # Indicate that restart is required and disable further actions
                    self.install_button.config(state=tk.DISABLED) # Disable further updates from this old instance
                    update_success = True # Indicate the download was successful, even if restart is pending

                except requests.exceptions.RequestException as e:
                    progress_page.update_status(f"Error updating BSI Installer: {e}", 100, error=True)
                    messagebox.showerror("Update Error", f"Failed to update BSI Installer: {e}")
                    update_success = False
                except Exception as e:
                    progress_page.update_status(f"Error handling installer update: {e}", 100, error=True)
                    messagebox.showerror("Update Error", f"An error occurred during installer update: {e}")
                    update_success = False
            
            if update_success:
                progress_page.update_status("All selected updates completed!", 100, success=True)
                messagebox.showinfo("Update Complete", "All available updates have been processed. If the installer itself was updated, please restart it.")
            else:
                progress_page.update_status("Update process finished with errors.", 100, error=True)

        except Exception as e:
            progress_page.update_status(f"An unexpected error occurred during update: {e}", 100, error=True)
            messagebox.showerror("Update Error", f"An unexpected error occurred: {e}")


class WelcomePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg="#f0f0f0")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1) # Row for update button and indicator

        heading = tk.Label(self, text="BSI Installer", font=("Inter", 28, "bold"), fg="#333", bg="#f0f0f0")
        heading.grid(row=0, column=0, pady=(60, 20), sticky="s")

        description_text = (
            "BSI (BeamMP Server Installer) creates BeamMP servers very quickly, "
            "making it easier to set up and manage your server instances."
        )
        description = tk.Label(self, text=description_text, font=("Inter", 14), wraplength=550,
                               justify="center", fg="#555", bg="#f0f0f0")
        description.grid(row=1, column=0, padx=50, pady=20, sticky="nsew")

        # Container for Next and Update buttons
        button_container = tk.Frame(self, bg="#f0f0f0")
        button_container.grid(row=2, column=0, pady=(30, 20), sticky="n")
        button_container.columnconfigure(0, weight=1)
        button_container.columnconfigure(1, weight=1)

        next_button = tk.Button(button_container, text="Install New", command=lambda: controller.show_frame("InstallOptionsPage"),
                                font=("Inter", 14, "bold"), bg="#4CAF50", fg="white",
                                activebackground="#45a049", activeforeground="white",
                                relief="raised", bd=0, padx=25, pady=12, cursor="hand2")
        next_button.grid(row=0, column=0, padx=10, sticky="e")

        # Update Button and Indicator
        update_frame = tk.Frame(button_container, bg="#f0f0f0")
        update_frame.grid(row=0, column=1, padx=10, sticky="w")

        self.update_button = tk.Button(update_frame, text="Update", command=self.controller.show_update_dialog,
                                       font=("Inter", 14, "bold"), bg="#007BFF", fg="white",
                                       activebackground="#0056b3", activeforeground="white",
                                       relief="raised", bd=0, padx=25, pady=12, cursor="hand2")
        self.update_button.pack(side=tk.LEFT)

        # Update indicator (red dot)
        self.update_indicator = tk.Canvas(update_frame, width=15, height=15, bg="#f0f0f0", highlightthickness=0)
        self.update_indicator_oval = self.update_indicator.create_oval(3, 3, 12, 12, fill="red", outline="red")
        self.update_indicator.pack(side=tk.RIGHT, padx=(5,0))
        self.update_indicator.pack_forget() # Hide initially

    def update_update_indicator(self):
        if self.controller.bsi_update_available or self.controller.installer_update_available:
            self.update_indicator.pack(side=tk.RIGHT, padx=(5,0)) # Show indicator
        else:
            self.update_indicator.pack_forget() # Hide indicator

class InstallOptionsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg="#f0f0f0")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=3)
        self.columnconfigure(2, weight=1)

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=0)
        self.rowconfigure(4, weight=2)

        tk.Label(self, text="Installation Options", font=("Inter", 24, "bold"), fg="#333", bg="#f0f0f0") \
            .grid(row=0, column=0, columnspan=3, pady=(40, 20), sticky="n")

        tk.Label(self, text="Install Location:", font=("Inter", 12), fg="#555", bg="#f0f0f0") \
            .grid(row=1, column=0, padx=(50, 10), pady=10, sticky="e")

        path_entry = tk.Entry(self, textvariable=controller.install_path, font=("Inter", 11), bd=2, relief="groove")
        path_entry.grid(row=1, column=1, pady=10, sticky="ew", padx=5)

        browse_button = tk.Button(self, text="Browse...", command=self.browse_folder,
                                  font=("Inter", 11), bg="#007BFF", fg="white",
                                  activebackground="#0056b3", activeforeground="white",
                                  relief="raised", bd=0, padx=12, pady=6, cursor="hand2")
        browse_button.grid(row=1, column=2, padx=(5, 50), pady=10, sticky="w")

        tk.Checkbutton(self, text="Delete BSI zipfile after extraction", variable=controller.delete_zip_var,
                       font=("Inter", 11), bg="#f0f0f0", fg="#333",
                       selectcolor="#d9d9d9", relief="flat", bd=0) \
            .grid(row=2, column=0, columnspan=3, padx=(100, 50), pady=5, sticky="w")

        tk.Checkbutton(self, text="Create BeamMP server (recommended)", variable=controller.create_server_var,
                       font=("Inter", 11), bg="#f0f0f0", fg="#333",
                       selectcolor="#d9d9d9", relief="flat", bd=0) \
            .grid(row=3, column=0, columnspan=3, padx=(100, 50), pady=5, sticky="w")

        button_frame = tk.Frame(self, bg="#f0f0f0")
        button_frame.grid(row=4, column=0, columnspan=3, pady=(40, 40), sticky="s")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        back_button = tk.Button(button_frame, text="Back", command=lambda: controller.show_frame("WelcomePage"),
                                font=("Inter", 14, "bold"), bg="#6c757d", fg="white",
                                activebackground="#5a6268", activeforeground="white",
                                relief="raised", bd=0, padx=25, pady=12, cursor="hand2")
        back_button.grid(row=0, column=0, padx=20, sticky="e")

        install_button = tk.Button(button_frame, text="Install", command=lambda: controller.start_installation(),
                                  font=("Inter", 14, "bold"), bg="#28a745", fg="white",
                                  activebackground="#218838", activeforeground="white",
                                  relief="raised", bd=0, padx=25, pady=12, cursor="hand2")
        install_button.grid(row=0, column=1, padx=20, sticky="w")

    def browse_folder(self):
        folder_selected = filedialog.askdirectory(initialdir=self.controller.install_path.get())
        if folder_selected:
            self.controller.install_path.set(folder_selected)

class InstallProgressPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg="#f0f0f0")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=3)
        self.rowconfigure(3, weight=1)

        tk.Label(self, text="Installation Progress", font=("Inter", 24, "bold"), fg="#333", bg="#f0f0f0") \
            .grid(row=0, column=0, pady=(40, 20), sticky="n")

        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=400, mode="determinate", style='TProgressbar')
        self.progress_bar.grid(row=1, column=0, pady=20, sticky="ew", padx=100)

        self.status_label = tk.Label(self, text="Ready to install...", font=("Inter", 12), wraplength=550,
                                      justify="center", fg="#555", bg="#f0f0f0")
        self.status_label.grid(row=2, column=0, padx=50, pady=20, sticky="n")

        self.action_button = tk.Button(self, text="Start Installation", command=self.controller.start_installation, # This button's command will change based on context
                                         font=("Inter", 14, "bold"), bg="#007BFF", fg="white",
                                         activebackground="#0056b3", activeforeground="white",
                                         relief="raised", bd=0, padx=25, pady=12, cursor="hand2")
        self.action_button.grid(row=3, column=0, pady=(30, 40), sticky="n")

    def update_status(self, message, progress_value, error=False, success=False):
        self.after(10, self._update_gui_elements, message, progress_value, error, success)

    def _update_gui_elements(self, message, progress_value, error, success):
        self.progress_bar["value"] = progress_value
        self.status_label.config(text=message)
        
        if error:
            self.status_label.config(fg="red")
            self.action_button.config(state=tk.DISABLED) 
        elif success:
            self.status_label.config(fg="green")
            self.action_button.config(state=tk.DISABLED) 
        else:
            self.status_label.config(fg="#555") 
            self.action_button.config(state=tk.DISABLED) # Disable button while installing or updating

        if progress_value == 100 and not error:
            self.action_button.config(text="Process Complete!", state=tk.DISABLED, bg="#28a745")
        
        self.update_idletasks() 

    def reset_status(self):
        self.progress_bar["value"] = 0
        self.status_label.config(text="Ready...", fg="#555")
        # Reset button text based on context (install or update) if needed, otherwise keep general
        self.action_button.config(text="Start Process", state=tk.NORMAL, bg="#007BFF", command=self.controller.start_installation)


if __name__ == "__main__":
    app = BSIInstaller()
    app.mainloop()
