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
    
    def __init__(self, url, filename):
        super().__init__()
        self.url = url
        self.filename = filename
        self.cancelled = False
    
    def run(self):
        try:
            request = Request(self.url, headers={'User-Agent': 'HelldiversMacro-UpdateChecker'})
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, self.filename)
            
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
        """Open browser to download page"""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(self.update_info['release_url']))
        self.accept()
    
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
