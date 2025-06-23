import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import requests
import zipfile
import shutil
import subprocess
import threading
import time

class BSIInstaller(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BSI Installer - v0.1")
        self.geometry("600x400")
        self.resizable(False, False)
        self.iconbitmap(default='') # Prevents an error on some systems if no icon is provided

        self.install_path = tk.StringVar(self)
        self.delete_zip_var = tk.BooleanVar(self, value=True)
        self.create_server_var = tk.BooleanVar(self, value=False)
        self.default_install_path = os.path.join(os.path.expanduser("~"), "Documents", "Beam Server")
        self.install_path.set(self.default_install_path)

        self.frames = {}
        self.create_frames()
        self.show_frame("WelcomePage")

    def create_frames(self):
        # Page 1: Welcome Page
        welcome_frame = WelcomePage(self, self)
        self.frames["WelcomePage"] = welcome_frame
        welcome_frame.grid(row=0, column=0, sticky="nsew")

        # Page 2: Install Instructions Page
        install_options_frame = InstallOptionsPage(self, self)
        self.frames["InstallOptionsPage"] = install_options_frame
        install_options_frame.grid(row=0, column=0, sticky="nsew")

        # Page 3: Installation Progress Page
        install_progress_frame = InstallProgressPage(self, self)
        self.frames["InstallProgressPage"] = install_progress_frame
        install_progress_frame.grid(row=0, column=0, sticky="nsew")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

    def start_installation(self):
        # Get references to the progress page elements
        progress_page = self.frames["InstallProgressPage"]
        progress_page.reset_status()
        progress_page.update_status("Starting installation...", 0)

        # Run installation in a separate thread to keep GUI responsive
        installation_thread = threading.Thread(target=self._run_installation, args=(progress_page,))
        installation_thread.start()

    def _run_installation(self, progress_page):
        install_base_path = self.install_path.get()
        beam_server_path = os.path.join(install_base_path, "Beam Server")
        bsi_folder_path = os.path.join(beam_server_path, "BSI")
        bsi_zip_url = "[https://github.com/Cosmologicalz/Beammp-server-creator/archive/refs/tags/v0.2.3.zip](https://github.com/Cosmologicalz/Beammp-server-creator/archive/refs/tags/v0.2.3.zip)"
        bsi_zip_filename = os.path.join(beam_server_path, "v0.2.3.zip")
        beammp_server_exe_url = "[https://github.com/BeamMP/BeamMP-Server/releases/latest/download/BeamMP-Server.exe](https://github.com/BeamMP/BeamMP-Server/releases/latest/download/BeamMP-Server.exe)"

        try:
            # 1. Create main folder: Beam Server
            progress_page.update_status("Creating 'Beam Server' folder...", 5)
            os.makedirs(beam_server_path, exist_ok=True)

            # 2. Create other folder: BSI inside Beam Server
            progress_page.update_status("Creating 'BSI' folder...", 10)
            os.makedirs(bsi_folder_path, exist_ok=True)

            # 3. Download BSI zipfile
            progress_page.update_status("Downloading BSI zipfile...", 20)
            try:
                response = requests.get(bsi_zip_url, stream=True)
                response.raise_for_status() # Raise an exception for bad status codes
                with open(bsi_zip_filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            except requests.exceptions.RequestException as e:
                progress_page.update_status(f"Error downloading BSI zip: {e}", 100, error=True)
                messagebox.showerror("Download Error", f"Failed to download BSI zip: {e}")
                return

            # 4. Extract the zip file in the main folder
            progress_page.update_status("Extracting BSI zipfile...", 40)
            try:
                with zipfile.ZipFile(bsi_zip_filename, 'r') as zip_ref:
                    zip_ref.extractall(beam_server_path)
            except zipfile.BadZipFile:
                progress_page.update_status("Error: Downloaded BSI zip is corrupted.", 100, error=True)
                messagebox.showerror("Extraction Error", "Downloaded BSI zip file is corrupted.")
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
                    response = requests.get(beammp_server_exe_url, stream=True)
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
                    # Use subprocess.Popen for non-blocking execution and silent start
                    # CREATE_NO_WINDOW is for Windows, preexec_fn for Unix-like
                    if os.name == 'nt': # Windows
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startupinfo.wShowWindow = subprocess.SW_HIDE
                        process = subprocess.Popen([beammp_exe_dest], cwd=server1_folder_path, startupinfo=startupinfo)
                    else: # Unix-like
                        process = subprocess.Popen([beammp_exe_dest], cwd=server1_folder_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    # Give it a moment to create files, then terminate
                    time.sleep(2) # Increased sleep time slightly for better reliability
                    process.terminate()
                    process.wait() # Wait for process to actually terminate
                except Exception as e:
                    progress_page.update_status(f"Error running BeamMP-Server.exe: {e}", 100, error=True)
                    messagebox.showerror("Execution Error", f"Failed to run BeamMP-Server.exe: {e}")
                    return

                # Create a shortcut of the BeamMP-Server.exe in the main folder.
                # Python does not have a built-in cross-platform way to create .lnk (Windows) or .desktop (Linux) shortcuts.
                # For simplicity, we'll create a simple batch/shell script shortcut or a Python-specific "shortcut" (e.g., a simple wrapper script).
                # For a true installer, pyinstaller's --onefile option often handles this or dedicated libraries.
                # For this exercise, we'll create a simple batch file for Windows or a shell script for Linux/macOS.
                progress_page.update_status("Creating BeamMP-Server shortcut...", 85)
                shortcut_path = os.path.join(beam_server_path, "Start BeamMP Server.bat" if os.name == 'nt' else "start_beammp_server.sh")
                with open(shortcut_path, 'w') as f:
                    if os.name == 'nt':
                        f.write(f'@echo off\ncd "{server1_folder_path}"\n"{os.path.basename(beammp_exe_dest)}"\npause')
                    else:
                        f.write(f'#!/bin/bash\ncd "{server1_folder_path}"\n./"{os.path.basename(beammp_exe_dest)}"\nread -p "Press Enter to continue..."')
                if os.name != 'nt':
                    os.chmod(shortcut_path, 0o755) # Make it executable

                # After a second has passed (already done with the sleep above)
                # Check that the BeamMp-Server.exe is in its designated folder
                progress_page.update_status("Verifying BeamMP-Server files...", 90)
                if not os.path.exists(beammp_exe_dest):
                    progress_page.update_status("Error: BeamMP-Server.exe not found where expected.", 100, error=True)
                    messagebox.showerror("Verification Error", "BeamMP-Server.exe was not found in 'Server 1' folder.")
                    return

                # Check for ServerConfig.toml in the main folder, and if it's there and not in server 1 folder, move it
                server_config_main_path = os.path.join(beam_server_path, "ServerConfig.toml")
                server_config_server1_path = os.path.join(server1_folder_path, "ServerConfig.toml")
                if os.path.exists(server_config_main_path) and not os.path.exists(server_config_server1_path):
                    shutil.move(server_config_main_path, server_config_server1_path)
                    progress_page.update_status("Moved ServerConfig.toml to 'Server 1' folder.", 95)

                # Finally check that the shortcut is in the main folder and exists.
                if not os.path.exists(shortcut_path):
                    progress_page.update_status("Error: Shortcut not found where expected.", 100, error=True)
                    messagebox.showerror("Verification Error", "The 'Start BeamMP Server' shortcut was not created.")
                    return

            progress_page.update_status("Installation complete!", 100, success=True)
            messagebox.showinfo("Installation Complete", "BSI and BeamMP Server (if selected) have been installed successfully!")

        except Exception as e:
            progress_page.update_status(f"An error occurred: {e}", 100, error=True)
            messagebox.showerror("Installation Error", f"An unexpected error occurred during installation: {e}")

class WelcomePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg="#f0f0f0") # Light grey background

        # Use a grid layout for better control over element positioning
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=1)

        # Heading
        heading = tk.Label(self, text="BSI Installer", font=("Inter", 24, "bold"), fg="#333", bg="#f0f0f0")
        heading.grid(row=0, column=0, pady=(40, 20), sticky="s") # Padded at top, sticks to south

        # Description
        description_text = (
            "BSI (BeamMP Server Installer) creates BeamMP servers very quickly, "
            "making it easier to set up and manage your server instances."
        )
        description = tk.Label(self, text=description_text, font=("Inter", 12), wraplength=400,
                               justify="center", fg="#555", bg="#f0f0f0")
        description.grid(row=1, column=0, padx=50, pady=10, sticky="nsew")

        # Next Button
        next_button = tk.Button(self, text="Next", command=lambda: controller.show_frame("InstallOptionsPage"),
                                font=("Inter", 12, "bold"), bg="#4CAF50", fg="white",
                                activebackground="#45a049", activeforeground="white",
                                relief="raised", bd=0, padx=20, pady=10, cursor="hand2")
        next_button.grid(row=2, column=0, pady=(20, 40), sticky="n") # Padded at bottom, sticks to north

        # Add some subtle styling
        for widget in self.winfo_children():
            widget.grid_configure(padx=10) # Add some horizontal padding to all children

class InstallOptionsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(bg="#f0f0f0")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=3) # Make path entry wider
        self.columnconfigure(2, weight=1)

        # Install Instructions Label
        tk.Label(self, text="Installation Options", font=("Inter", 20, "bold"), fg="#333", bg="#f0f0f0") \
            .grid(row=0, column=0, columnspan=3, pady=(30, 20), sticky="n")

        # Install Path Label and Entry
        tk.Label(self, text="Install Location:", font=("Inter", 12), fg="#555", bg="#f0f0f0") \
            .grid(row=1, column=0, padx=(50, 10), pady=10, sticky="w")
        
        path_entry = tk.Entry(self, textvariable=controller.install_path, width=50, font=("Inter", 10), bd=2, relief="groove")
        path_entry.grid(row=1, column=1, pady=10, sticky="ew")

        browse_button = tk.Button(self, text="Browse...", command=self.browse_folder,
                                  font=("Inter", 10), bg="#007BFF", fg="white",
                                  activebackground="#0056b3", activeforeground="white",
                                  relief="raised", bd=0, padx=10, pady=5, cursor="hand2")
        browse_button.grid(row=1, column=2, padx=(10, 50), pady=10, sticky="w")

        # Checkboxes
        tk.Checkbutton(self, text="Delete BSI zipfile after extraction", variable=controller.delete_zip_var,
                       font=("Inter", 11), bg="#f0f0f0", fg="#333",
                       selectcolor="#d9d9d9", relief="flat", bd=0) \
            .grid(row=2, column=0, columnspan=3, padx=50, pady=5, sticky="w")

        tk.Checkbutton(self, text="Create BeamMP server (recommended)", variable=controller.create_server_var,
                       font=("Inter", 11), bg="#f0f0f0", fg="#333",
                       selectcolor="#d9d9d9", relief="flat", bd=0) \
            .grid(row=3, column=0, columnspan=3, padx=50, pady=5, sticky="w")

        # Back and Install Buttons
        button_frame = tk.Frame(self, bg="#f0f0f0")
        button_frame.grid(row=4, column=0, columnspan=3, pady=(30, 30), sticky="s")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        back_button = tk.Button(button_frame, text="Back", command=lambda: controller.show_frame("WelcomePage"),
                                font=("Inter", 12, "bold"), bg="#6c757d", fg="white",
                                activebackground="#5a6268", activeforeground="white",
                                relief="raised", bd=0, padx=20, pady=10, cursor="hand2")
        back_button.grid(row=0, column=0, padx=10, sticky="e")

        install_button = tk.Button(button_frame, text="Install", command=lambda: controller.show_frame("InstallProgressPage"),
                                  font=("Inter", 12, "bold"), bg="#28a745", fg="white",
                                  activebackground="#218838", activeforeground="white",
                                  relief="raised", bd=0, padx=20, pady=10, cursor="hand2")
        install_button.grid(row=0, column=1, padx=10, sticky="w")

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
        self.rowconfigure(2, weight=3) # Status messages take more space
        self.rowconfigure(3, weight=1)


        tk.Label(self, text="Installation Progress", font=("Inter", 20, "bold"), fg="#333", bg="#f0f0f0") \
            .grid(row=0, column=0, pady=(30, 20), sticky="n")

        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(row=1, column=0, pady=10, sticky="ew", padx=50)

        self.status_label = tk.Label(self, text="Ready to install...", font=("Inter", 11), wraplength=450,
                                      justify="center", fg="#555", bg="#f0f0f0")
        self.status_label.grid(row=2, column=0, padx=50, pady=10, sticky="n")

        self.install_button = tk.Button(self, text="Start Installation", command=self.controller.start_installation,
                                         font=("Inter", 12, "bold"), bg="#007BFF", fg="white",
                                         activebackground="#0056b3", activeforeground="white",
                                         relief="raised", bd=0, padx=20, pady=10, cursor="hand2")
        self.install_button.grid(row=3, column=0, pady=(20, 30), sticky="n")

    def update_status(self, message, progress_value, error=False, success=False):
        # Update progress bar and status label. Use after() to ensure GUI updates
        self.after(10, self._update_gui_elements, message, progress_value, error, success)

    def _update_gui_elements(self, message, progress_value, error, success):
        self.progress_bar["value"] = progress_value
        self.status_label.config(text=message)
        
        if error:
            self.status_label.config(fg="red")
            self.install_button.config(state=tk.DISABLED) # Disable button on error
        elif success:
            self.status_label.config(fg="green")
            self.install_button.config(state=tk.DISABLED) # Installation done, disable button
        else:
            self.status_label.config(fg="#555") # Default color for ongoing
            self.install_button.config(state=tk.DISABLED) # Disable button while installing

        if progress_value == 100 and not error:
            # Re-enable/change button text or add a "Finish" button
            self.install_button.config(text="Installation Complete!", state=tk.DISABLED, bg="#28a745")

        self.update_idletasks() # Force GUI update

    def reset_status(self):
        self.progress_bar["value"] = 0
        self.status_label.config(text="Ready to install...", fg="#555")
        self.install_button.config(text="Start Installation", state=tk.NORMAL, bg="#007BFF")


if __name__ == "__main__":
    app = BSIInstaller()
    app.mainloop()
