"""
Update manager module for Helldivers Numpad Macros
Handles update checking, downloading, and installation dialogs
"""

import os
import sys
import tempfile
import subprocess
from urllib.request import urlopen, Request

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QFileDialog, QMessageBox, QProgressBar, QTextBrowser, 
                             QApplication, QLineEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from . import update_checker
from ..config.config import get_install_type, get_installer_filename, is_installed
from ..config.version import VERSION, APP_NAME, GITHUB_REPO_OWNER, GITHUB_REPO_NAME


class DownloadThread(QThread):
    """Thread for downloading installer"""
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, url, filename, target_dir=None):
        super().__init__()
        self.url = url
        self.filename = filename
        self.target_dir = target_dir
        self.cancelled = False
    
    def run(self):
        try:
            request = Request(self.url, headers={'User-Agent': 'HelldiversMacro-UpdateChecker'})
            
            # Use target_dir if provided, otherwise use temp directory
            if self.target_dir:
                download_dir = self.target_dir
            else:
                download_dir = tempfile.gettempdir()
            
            file_path = os.path.join(download_dir, self.filename)
            
            with urlopen(request, timeout=30) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192
                
                with open(file_path, 'wb') as f:
                    while not self.cancelled:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total_size)
            
            if not self.cancelled:
                self.finished.emit(file_path)
        except Exception as e:
            self.error.emit(str(e))
    
    def cancel(self):
        self.cancelled = True


class SetupDialog(QDialog):
    """Dialog for installing/updating the application"""
    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.installer_path = None
        self.download_thread = None
        self.is_app_installed = is_installed()
        
        self.setObjectName("setup_dialog")
        self.setWindowTitle("Setup - Install Update")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        if self.is_app_installed:
            title_text = f"Update to {update_info.get('tag_name', update_info['latest_version'])}"
            desc_text = "The installer will be downloaded and launched to update your installation."
        else:
            title_text = f"Install {update_info.get('tag_name', update_info['latest_version'])}"
            desc_text = "You are running the portable version. Install to get automatic updates."
        
        title = QLabel(title_text)
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #3ddc84;")
        layout.addWidget(title)
        
        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #ccc; padding: 10px 0;")
        layout.addWidget(desc)
        
        # Installation path (only for portable)
        if not self.is_app_installed:
            path_label = QLabel("Installation path:")
            path_label.setStyleSheet("color: #ddd; margin-top: 10px;")
            layout.addWidget(path_label)
            
            path_layout = QHBoxLayout()
            self.path_input = QLineEdit()
            default_path = os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), APP_NAME)
            self.path_input.setText(default_path)
            self.path_input.setStyleSheet("background: #1a1a1a; color: #ddd; padding: 5px; border: 1px solid #333;")
            path_layout.addWidget(self.path_input)
            
            browse_btn = QPushButton("Browse...")
            browse_btn.clicked.connect(self.browse_path)
            path_layout.addWidget(browse_btn)
            layout.addLayout(path_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            "QProgressBar { background: #1a1a1a; border: 1px solid #333; border-radius: 4px; "
            "text-align: center; color: #ddd; }"
            "QProgressBar::chunk { background: #3ddc84; }"
        )
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #aaa; font-size: 11px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addStretch(1)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_setup)
        btn_layout.addWidget(self.cancel_btn)
        
        self.install_btn = QPushButton("Install" if not self.is_app_installed else "Update")
        self.install_btn.setStyleSheet(
            "background: #3ddc84; color: #000; font-weight: bold; "
            "padding: 8px 20px; border-radius: 4px;"
        )
        self.install_btn.clicked.connect(self.start_installation)
        btn_layout.addWidget(self.install_btn)
        
        layout.addLayout(btn_layout)
    
    def browse_path(self):
        """Browse for installation directory"""
        path = QFileDialog.getExistingDirectory(self, "Select Installation Directory")
        if path:
            self.path_input.setText(path)
    
    def start_installation(self):
        """Download and run installer/update"""
        download_url = self._get_download_url()
        
        if not download_url:
            QMessageBox.warning(
                self, "Download Error",
                "Could not find installer download URL.\n\n"
                "Please download manually from GitHub."
            )
            return
        
        # Start download
        self.install_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Downloading installer...")
        
        filename = os.path.basename(download_url.split('?')[0])  # Remove query params
        self.download_thread = DownloadThread(download_url, filename)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.run_installer)
        self.download_thread.error.connect(self.download_error)
        self.download_thread.start()
    
    def _get_download_url(self):
        """Get the appropriate download URL for the installer"""
        # If update checker already provided a download URL, use it
        download_url = self.update_info.get('download_url')
        if download_url:
            return download_url
        
        # Otherwise, manually select based on install type
        assets = self.update_info.get('assets', [])
        current_install_type = get_install_type()
        
        if current_install_type == "installed":
            # Look for setup executable
            for asset in assets:
                name = asset.get('name', '').lower()
                if 'setup' in name and name.endswith('.exe'):
                    return asset.get('browser_download_url')
        else:
            # Look for portable executable
            for asset in assets:
                name = asset.get('name', '').lower()
                if 'portable' in name and name.endswith('.exe'):
                    return asset.get('browser_download_url')
        
        # Fallback to any .exe asset if specific type not found
        for asset in assets:
            name = asset.get('name', '').lower()
            if name.endswith('.exe'):
                return asset.get('browser_download_url')
        
        # Final fallback: construct expected download URL
        tag_name = self.update_info.get('tag_name', self.update_info['latest_version'])
        filename = get_installer_filename(tag_name)
        return f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/download/{tag_name}/{filename}"
    
    def update_progress(self, downloaded, total):
        """Update download progress"""
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.status_label.setText(f"Downloading: {mb_downloaded:.1f} MB / {mb_total:.1f} MB")
    
    def run_installer(self, file_path):
        """Run the downloaded installer"""
        self.installer_path = file_path
        self.status_label.setText("Download complete! Launching installer...")
        self.progress_bar.setValue(100)
        
        try:
            # Prepare installer arguments
            if self.is_app_installed:
                # Silent update (or with minimal UI)
                subprocess.Popen([file_path, '/SILENT'])
            else:
                # Install to custom directory
                install_dir = self.path_input.text()
                subprocess.Popen([file_path, f'/DIR="{install_dir}"'])
            
            QMessageBox.information(
                self, "Installer Launched",
                "The installer has been launched. This application will now close.\n\n"
                "Please complete the installation and restart the application."
            )
            
            # Close the application
            self.accept()
            QApplication.quit()
            
        except Exception as e:
            self.download_error(f"Failed to launch installer: {str(e)}")
    
    def download_error(self, error_msg):
        """Handle download error"""
        self.install_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
        
        QMessageBox.warning(
            self, "Download Failed",
            f"Failed to download installer:\n{error_msg}\n\n"
            "Please download manually from GitHub."
        )
    
    def cancel_setup(self):
        """Cancel installation"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.download_thread.wait()
        self.reject()


class PortableUpdateDialog(QDialog):
    """Dialog for downloading and installing portable updates"""
    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.download_thread = None
        self.downloaded_file = None
        
        self.setObjectName("portable_update_dialog")
        self.setWindowTitle("Update Portable Version")
        self.setMinimumWidth(500)
        self.setMinimumHeight(250)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title = QLabel(f"Update to {update_info.get('tag_name', update_info['latest_version'])}")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #3ddc84;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel("The new version will be downloaded to the same folder as the current executable.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #ccc; padding: 10px 0;")
        layout.addWidget(desc)
        
        # Current path info
        current_exe = sys.executable
        if hasattr(sys, 'frozen') and sys.frozen:
            current_exe = sys.executable
        else:
            # Running from Python, use main.py location
            current_exe = os.path.abspath(sys.argv[0])
        
        self.current_dir = os.path.dirname(current_exe)
        self.current_exe_name = os.path.basename(current_exe)
        
        path_label = QLabel(f"Location: {self.current_dir}")
        path_label.setStyleSheet("color: #aaa; font-size: 11px; padding: 5px 0;")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            "QProgressBar { background: #1a1a1a; border: 1px solid #333; border-radius: 4px; "
            "text-align: center; color: #ddd; }"
            "QProgressBar::chunk { background: #3ddc84; }"
        )
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #aaa; font-size: 11px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addStretch(1)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_update)
        btn_layout.addWidget(self.cancel_btn)
        
        self.download_btn = QPushButton("Download Update")
        self.download_btn.setStyleSheet(
            "background: #3ddc84; color: #000; font-weight: bold; "
            "padding: 8px 20px; border-radius: 4px;"
        )
        self.download_btn.clicked.connect(self.start_download)
        btn_layout.addWidget(self.download_btn)
        
        layout.addLayout(btn_layout)
    
    def start_download(self):
        """Start downloading the portable update"""
        download_url = self._get_portable_download_url()
        
        if not download_url:
            QMessageBox.warning(
                self, "Download Error",
                "Could not find portable version download URL.\n\n"
                "Please download manually from GitHub."
            )
            return
        
        # Start download
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Downloading update...")
        
        # Generate filename for new version
        filename = os.path.basename(download_url.split('?')[0])  # Remove query params
        if not filename.endswith('.exe'):
            filename = f"HelldiversNumpadMacros_{self.update_info.get('tag_name', 'new')}.exe"
        
        # Add suffix to avoid overwriting current exe during download
        self.new_filename = filename.replace('.exe', '_new.exe')
        
        self.download_thread = DownloadThread(download_url, self.new_filename, self.current_dir)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_complete)
        self.download_thread.error.connect(self.download_error)
        self.download_thread.start()
    
    def _get_portable_download_url(self):
        """Get the portable executable download URL"""
        # Check if update_info already has download_url
        download_url = self.update_info.get('download_url')
        if download_url:
            return download_url
        
        # Search in assets for portable executable
        assets = self.update_info.get('assets', [])
        for asset in assets:
            name = asset.get('name', '').lower()
            if 'portable' in name and name.endswith('.exe'):
                return asset.get('browser_download_url')
        
        # Fallback: look for any .exe that's not setup
        for asset in assets:
            name = asset.get('name', '').lower()
            if name.endswith('.exe') and 'setup' not in name:
                return asset.get('browser_download_url')
        
        return None
    
    def update_progress(self, downloaded, total):
        """Update download progress"""
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.status_label.setText(f"Downloading: {mb_downloaded:.1f} MB / {mb_total:.1f} MB")
    
    def download_complete(self, file_path):
        """Handle download completion"""
        self.downloaded_file = file_path
        self.status_label.setText("Download complete!")
        self.progress_bar.setValue(100)
        
        # Ask user if they want to delete the old version
        reply = QMessageBox.question(
            self, "Delete Old Version?",
            f"The new version has been downloaded to:\n{file_path}\n\n"
            f"Do you want to delete the previous version?\n{os.path.join(self.current_dir, self.current_exe_name)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.replace_old_version()
        else:
            self.keep_both_versions()
    
    def replace_old_version(self):
        """Replace the old version with the new one"""
        try:
            old_exe_path = os.path.join(self.current_dir, self.current_exe_name)
            backup_path = old_exe_path + '.old'
            
            # Rename old exe to .old (in case we need to rollback)
            if os.path.exists(old_exe_path):
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(old_exe_path, backup_path)
            
            # Rename new exe to proper name
            final_path = os.path.join(self.current_dir, self.current_exe_name)
            os.rename(self.downloaded_file, final_path)
            
            # Schedule old backup for deletion on next start
            QMessageBox.information(
                self, "Update Complete",
                f"Update installed successfully!\n\n"
                f"The new version is ready at:\n{final_path}\n\n"
                f"Please restart the application to use the new version.\n\n"
                f"Old version backup: {backup_path}\n"
                f"(You can delete it manually if the new version works correctly)"
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Update Error",
                f"Failed to replace old version:\n{str(e)}\n\n"
                f"The new version is available at:\n{self.downloaded_file}\n\n"
                f"You can manually rename it to replace the old version."
            )
    
    def keep_both_versions(self):
        """Keep both old and new versions"""
        # Remove the '_new' suffix for cleaner filename
        final_filename = self.new_filename.replace('_new.exe', '.exe')
        if final_filename == self.current_exe_name:
            # If names would conflict, keep the _new suffix but make it version-specific
            tag = self.update_info.get('tag_name', 'updated')
            final_filename = self.current_exe_name.replace('.exe', f'_{tag}.exe')
        
        final_path = os.path.join(self.current_dir, final_filename)
        
        try:
            # Rename to final name
            if final_path != self.downloaded_file:
                if os.path.exists(final_path):
                    os.remove(final_path)
                os.rename(self.downloaded_file, final_path)
            
            QMessageBox.information(
                self, "Download Complete",
                f"The new version has been downloaded to:\n{final_path}\n\n"
                f"You can use either version. To use the new version, run:\n{final_filename}"
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.warning(
                self, "Rename Failed",
                f"Could not rename file:\n{str(e)}\n\n"
                f"The new version is available at:\n{self.downloaded_file}"
            )
            self.accept()
    
    def download_error(self, error_msg):
        """Handle download error"""
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
        
        QMessageBox.warning(
            self, "Download Failed",
            f"Failed to download update:\n{error_msg}\n\n"
            "Please try again or download manually from GitHub."
        )
    
    def cancel_update(self):
        """Cancel the update download"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.download_thread.wait()
        self.reject()


class UpdateDialog(QDialog):
    """Dialog to notify user of available update"""
    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.setObjectName("update_dialog")
        self.setWindowTitle("Update Available")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Title with clickable link
        title = QLabel(
            f"New version available: "
            f"<a href=\"{update_info['release_url']}\" style=\"color: #3ddc84; text-decoration: none;\">"
            f"{update_info.get('tag_name', update_info['latest_version'])}</a>"
        )
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #3ddc84; padding: 10px;")
        title.setOpenExternalLinks(True)
        title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title)
        
        # Version info
        version_info = QLabel(
            f"Current version: {update_info['current_version']}\n"
            f"Latest version: {update_info.get('tag_name', update_info['latest_version'])}"
        )
        version_info.setStyleSheet("color: #ddd; padding: 5px;")
        layout.addWidget(version_info)
        
        # Release notes
        notes_label = QLabel("Release Notes:")
        notes_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        notes_label.setStyleSheet("color: #ddd; margin-top: 10px;")
        layout.addWidget(notes_label)
        
        notes_browser = QTextBrowser()
        notes_browser.setObjectName("release_notes")
        notes_browser.setOpenExternalLinks(True)
        notes_browser.setMarkdown(update_info['release_notes'])
        notes_browser.setStyleSheet(
            "background: #1a1a1a; color: #ccc; border: 1px solid #333; "
            "padding: 8px; border-radius: 4px;"
        )
        layout.addWidget(notes_browser)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        
        skip_btn = QPushButton("Skip This Version")
        skip_btn.setObjectName("update_skip")
        skip_btn.clicked.connect(self.skip_version)
        btn_layout.addWidget(skip_btn)
        
        remind_btn = QPushButton("Remind Me Later")
        remind_btn.clicked.connect(self.reject)
        btn_layout.addWidget(remind_btn)
        
        # Show install/download button based on installation type
        if is_installed():
            install_btn = QPushButton("Install Update")
            install_btn.setStyleSheet(
                "background: #3ddc84; color: #000; font-weight: bold; "
                "padding: 8px 20px; border-radius: 4px;"
            )
            install_btn.clicked.connect(self.show_setup)
        else:
            install_btn = QPushButton("Download")
            install_btn.setStyleSheet(
                "background: #3ddc84; color: #000; font-weight: bold; "
                "padding: 8px 20px; border-radius: 4px;"
            )
            install_btn.clicked.connect(self.download_update)
        
        btn_layout.addWidget(install_btn)
        layout.addLayout(btn_layout)
    
    def show_setup(self):
        """Show setup dialog for installation"""
        self.accept()
        setup_dlg = SetupDialog(self.update_info, self.parent())
        setup_dlg.exec()
    
    def download_update(self):
        """Download portable update to current directory"""
        self.accept()
        portable_dlg = PortableUpdateDialog(self.update_info, self.parent())
        portable_dlg.exec()
    
    def skip_version(self):
        """Skip this version and don't show again"""
        from ..config.config import load_settings, save_settings
        settings = load_settings()
        settings['skipped_version'] = self.update_info.get('tag_name', self.update_info['latest_version'])
        save_settings(settings)
        self.reject()


def check_for_updates_startup(parent_widget, global_settings):
    """Check for updates in background on startup"""
    result = update_checker.check_for_updates(
        VERSION, GITHUB_REPO_OWNER, GITHUB_REPO_NAME,
        install_type=get_install_type(), timeout=10
    )
    
    if not result['success'] or not result['has_update']:
        return
    
    # Check if this version was skipped
    skipped_version = global_settings.get('skipped_version', '')
    if skipped_version == result.get('tag_name', result['latest_version']):
        return  # Don't show dialog for skipped version
    
    dlg = UpdateDialog(result, parent_widget)
    dlg.exec()
