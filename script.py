import sys
import time
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QDateTimeEdit, QStatusBar, QSystemTrayIcon, QMenu, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QKeySequence, QShortcut
from pypresence import Presence
import dbus
from urllib.parse import urlparse
import os
import signal

CONFIG_FILE = "config.json"

class CustomRPCApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.rpc_connected = False
        self.rpc = None
        self.session_start_time = None
        self.refresh_timer = QTimer()
        self.refresh_timer.setInterval(5000)  # 5 seconds
        self.refresh_timer.timeout.connect(self.auto_update_presence)
        
        # Add MPRIS refresh timer
        self.mpris_refresh_timer = QTimer()
        self.mpris_refresh_timer.setInterval(5000)  # 5 seconds
        self.mpris_refresh_timer.timeout.connect(self.refresh_mpris_players)
        self.current_mpris_players = set()  # Track current MPRIS players
        
        # Set up signal handlers for clean exit
        signal.signal(signal.SIGINT, self.handle_sigint)
        signal.signal(signal.SIGTERM, self.handle_sigint)
        
        self.init_ui()
        self.setup_system_tray()
        self.load_config()
        self.mpris_refresh_timer.start()  # Start MPRIS refresh timer

    def handle_sigint(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        self.close_application()
        QApplication.quit()

    def init_ui(self):
        self.setWindowTitle("Custom Rich Presence")
        self.setGeometry(100, 100, 400, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Add keyboard shortcuts
        self.setup_shortcuts()

        # Auto-save timer
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setInterval(30000)  # 30 seconds
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start()

        # Create form layout with better organization
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(10, 10, 10, 10)

        # Discord Connection Section
        connection_group = QVBoxLayout()
        self.app_id_label = QLabel("Discord App ID:")
        self.app_id_input = QLineEdit()
        self.app_id_input.setToolTip("Enter your Discord Application ID")
        connection_group.addWidget(self.app_id_label)
        connection_group.addWidget(self.app_id_input)

        self.connect_button = QPushButton("Connect to Discord (Ctrl+C)")
        self.connect_button.clicked.connect(self.toggle_connection)
        self.connect_button.setToolTip("Connect to Discord Rich Presence")
        connection_group.addWidget(self.connect_button)
        form_layout.addLayout(connection_group)

        # Presence Details Section
        details_group = QVBoxLayout()
        self.details_label = QLabel("Details:")
        self.details_input = QLineEdit()
        details_group.addWidget(self.details_label)
        details_group.addWidget(self.details_input)

        self.state_label = QLabel("State:")
        self.state_input = QLineEdit()
        details_group.addWidget(self.state_label)
        details_group.addWidget(self.state_input)
        form_layout.addLayout(details_group)

        # Timestamp Section
        timestamp_group = QVBoxLayout()
        self.timestamp_label = QLabel("Timestamp:")
        self.timestamp_combo = QComboBox()
        self.timestamp_combo.addItems(["None", "Current Time", "Custom Timestamp"])
        self.timestamp_combo.currentIndexChanged.connect(self.toggle_custom_timestamp)
        timestamp_group.addWidget(self.timestamp_label)
        timestamp_group.addWidget(self.timestamp_combo)

        self.custom_timestamp_input = QDateTimeEdit(datetime.now())
        self.custom_timestamp_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.custom_timestamp_input.setCalendarPopup(True)
        self.custom_timestamp_input.hide()
        timestamp_group.addWidget(self.custom_timestamp_input)
        form_layout.addLayout(timestamp_group)

        # MPRIS Section
        mpris_group = QVBoxLayout()
        self.mpris_label = QLabel("Use MPRIS Player:")
        self.mpris_combo = QComboBox()
        self.mpris_combo.addItem("None")
        self.populate_mpris_players()
        self.mpris_combo.currentIndexChanged.connect(self.toggle_auto_refresh)
        mpris_group.addWidget(self.mpris_label)
        mpris_group.addWidget(self.mpris_combo)
        form_layout.addLayout(mpris_group)

        # Images Section
        images_group = QVBoxLayout()
        self.large_image_label = QLabel("Large Image Key:")
        self.large_image_input = QLineEdit()
        self.large_image_input.setText("avatar")
        images_group.addWidget(self.large_image_label)
        images_group.addWidget(self.large_image_input)

        self.large_image_text_label = QLabel("Large Image Hover Text:")
        self.large_image_text_input = QLineEdit()
        images_group.addWidget(self.large_image_text_label)
        images_group.addWidget(self.large_image_text_input)

        self.small_image_label = QLabel("Small Image Key:")
        self.small_image_input = QLineEdit()
        images_group.addWidget(self.small_image_label)
        images_group.addWidget(self.small_image_input)

        self.small_image_text_label = QLabel("Small Image Hover Text:")
        self.small_image_text_input = QLineEdit()
        images_group.addWidget(self.small_image_text_label)
        images_group.addWidget(self.small_image_text_input)
        form_layout.addLayout(images_group)

        # Buttons Section
        buttons_group = QVBoxLayout()
        self.button1_label = QLabel("Button 1 Text:")
        self.button1_text = QLineEdit()
        self.button1_url = QLineEdit()
        self.button1_url.setPlaceholderText("https://example.com")
        buttons_group.addWidget(self.button1_label)
        buttons_group.addWidget(self.button1_text)
        buttons_group.addWidget(self.button1_url)

        self.button2_label = QLabel("Button 2 Text:")
        self.button2_text = QLineEdit()
        self.button2_url = QLineEdit()
        self.button2_url.setPlaceholderText("https://example.com")
        buttons_group.addWidget(self.button2_label)
        buttons_group.addWidget(self.button2_text)
        buttons_group.addWidget(self.button2_url)
        form_layout.addLayout(buttons_group)

        # Update Button
        self.update_button = QPushButton("Update Presence (Ctrl+U)")
        self.update_button.clicked.connect(self.update_presence)
        form_layout.addWidget(self.update_button)

        # Add a clear presence button
        self.clear_button = QPushButton("Clear Presence (Ctrl+X)")
        self.clear_button.clicked.connect(self.clear_presence)
        form_layout.addWidget(self.clear_button)
        
        # Add a status indicator
        self.status_indicator = QLabel("Status: Disconnected")
        self.status_indicator.setStyleSheet("color: #f44336;")
        form_layout.addWidget(self.status_indicator)

        layout.addLayout(form_layout)

    def setup_shortcuts(self):
        """Set up keyboard shortcuts"""
        # Connect to Discord shortcut
        connect_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        connect_shortcut.activated.connect(self.toggle_connection)
        
        # Update presence shortcut
        update_shortcut = QShortcut(QKeySequence("Ctrl+U"), self)
        update_shortcut.activated.connect(self.update_presence)
        
        # Save shortcut
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_config)
        
        # Quit shortcut
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(self.close_application)
        
        # Clear presence shortcut
        clear_shortcut = QShortcut(QKeySequence("Ctrl+X"), self)
        clear_shortcut.activated.connect(self.clear_presence)

    def auto_save(self):
        """Auto-save configuration periodically"""
        if self.rpc_connected:
            self.save_config()
            self.status_bar.showMessage("Configuration auto-saved", 2000)

    def toggle_connection(self):
        """Toggle Discord connection with visual feedback"""
        app_id = self.app_id_input.text().strip()
        if not app_id:
            self.status_bar.showMessage("Please enter a Discord App ID", 3000)
            return

        if not self.validate_app_id(app_id):
            self.status_bar.showMessage("Invalid Discord App ID format", 3000)
            return

        if not self.rpc_connected:
            try:
                self.rpc = Presence(app_id)
                self.rpc.connect()
                self.rpc_connected = True
                self.connect_button.setText("Connected to Discord (Ctrl+C)")
                self.connect_button.setStyleSheet("background-color: #4CAF50; color: white;")
                self.status_bar.showMessage("Connected to Discord", 3000)
                self.save_config()
                # Auto-update presence after connecting
                self.update_presence()
                self.status_indicator.setText("Status: Connected")
                self.status_indicator.setStyleSheet("color: #4CAF50;")
            except Exception as e:
                self.connect_button.setText("Connection Failed (Ctrl+C)")
                self.connect_button.setStyleSheet("background-color: #f44336; color: white;")
                self.status_bar.showMessage(f"Connection failed: {str(e)}", 5000)
                print(f"Error connecting to Discord: {e}")
                self.rpc_connected = False
                self.rpc = None
                self.status_indicator.setText("Status: Connection Failed")
                self.status_indicator.setStyleSheet("color: #f44336;")
        else:
            try:
                self.rpc.clear()
                self.rpc_connected = False
                self.refresh_timer.stop()
                self.connect_button.setText("Connect to Discord (Ctrl+C)")
                self.connect_button.setStyleSheet("")
                self.status_bar.showMessage("Disconnected from Discord", 3000)
                self.status_indicator.setText("Status: Disconnected")
                self.status_indicator.setStyleSheet("color: #f44336;")
            except Exception as e:
                self.status_bar.showMessage(f"Error disconnecting: {str(e)}", 5000)
                print(f"Error disconnecting from Discord: {e}")
                self.status_indicator.setText("Status: Error")
                self.status_indicator.setStyleSheet("color: #f44336;")

    def toggle_custom_timestamp(self):
        if self.timestamp_combo.currentText() == "Custom Timestamp":
            self.custom_timestamp_input.show()
        else:
            self.custom_timestamp_input.hide()

    def toggle_auto_refresh(self):
        if self.mpris_combo.currentText() != "None" and self.rpc_connected:
            self.refresh_timer.start()
        else:
            self.refresh_timer.stop()

    def auto_update_presence(self):
        if self.rpc_connected and self.mpris_combo.currentText() != "None":
            self.update_presence()

    def update_presence(self):
        """Update Discord presence with auto-connect"""
        if not self.rpc_connected:
            # Try to connect first
            app_id = self.app_id_input.text().strip()
            if not app_id:
                self.status_bar.showMessage("Please enter a Discord App ID", 3000)
                return
            if not self.validate_app_id(app_id):
                self.status_bar.showMessage("Invalid Discord App ID format", 3000)
                return
            try:
                self.rpc = Presence(app_id)
                self.rpc.connect()
                self.rpc_connected = True
                self.connect_button.setText("Connected to Discord (Ctrl+C)")
                self.connect_button.setStyleSheet("background-color: #4CAF50; color: white;")
                self.status_bar.showMessage("Connected to Discord", 3000)
                self.status_indicator.setText("Status: Connected")
                self.status_indicator.setStyleSheet("color: #4CAF50;")
            except Exception as e:
                self.status_bar.showMessage(f"Connection failed: {str(e)}", 5000)
                print(f"Error connecting to Discord: {e}")
                self.status_indicator.setText("Status: Connection Failed")
                self.status_indicator.setStyleSheet("color: #f44336;")
                return

        try:
            selected_player = self.mpris_combo.currentText()
            if selected_player != "None":
                artist, info = self.get_mpris_metadata(selected_player)
                details = artist or self.details_input.text()
                state = info or self.state_input.text()
            else:
                details = self.details_input.text()
                state = self.state_input.text()

            timestamp = self.timestamp_combo.currentText()
            large_image = self.large_image_input.text()
            large_text = self.large_image_text_input.text()
            small_image = self.small_image_input.text()
            small_text = self.small_image_text_input.text()

            start_time = None
            if timestamp == "Current Time":
                if self.session_start_time is None:
                    self.session_start_time = int(time.time())
                start_time = self.session_start_time
            elif timestamp == "Custom Timestamp":
                dt = self.custom_timestamp_input.dateTime().toPyDateTime()
                start_time = int(dt.timestamp())
                self.session_start_time = start_time
            else:
                self.session_start_time = None

            buttons = []
            # Button 1
            if self.button1_text.text():
                url = self.button1_url.text()
                if self.validate_url(url):
                    buttons.append({
                        "label": self.button1_text.text(),
                        "url": url if url.startswith(('http://', 'https://')) else f'https://{url}'
                    })
                else:
                    self.status_bar.showMessage("Invalid URL for Button 1", 3000)

            # Button 2
            if self.button2_text.text():
                url = self.button2_url.text()
                if self.validate_url(url):
                    buttons.append({
                        "label": self.button2_text.text(),
                        "url": url if url.startswith(('http://', 'https://')) else f'https://{url}'
                    })
                else:
                    self.status_bar.showMessage("Invalid URL for Button 2", 3000)

            # Update presence with validated data
            self.rpc.update(
                details=details,
                state=state,
                start=start_time,
                large_image=large_image,
                large_text=large_text,
                small_image=small_image,
                small_text=small_text,
                buttons=buttons if buttons else None
            )
            self.status_bar.showMessage("Presence updated successfully", 3000)
            self.save_config()
            
            # Visual feedback for update button
            self.update_button.setStyleSheet("background-color: #4CAF50; color: white;")
            QTimer.singleShot(1000, lambda: self.update_button.setStyleSheet(""))
        except Exception as e:
            self.status_bar.showMessage(f"Error updating presence: {str(e)}", 5000)
            print(f"Error updating presence: {e}")
            self.update_button.setStyleSheet("background-color: #f44336; color: white;")
            QTimer.singleShot(1000, lambda: self.update_button.setStyleSheet(""))

    def get_mpris_metadata(self, service_name):
        """Get metadata from MPRIS player with improved error handling."""
        try:
            bus = dbus.SessionBus()
            player = bus.get_object(service_name, '/org/mpris/MediaPlayer2')
            properties = dbus.Interface(player, 'org.freedesktop.DBus.Properties')
            metadata = properties.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
            
            # Extract metadata with fallbacks
            artist = metadata.get('xesam:artist', ['Unknown Artist'])[0]
            title = metadata.get('xesam:title', 'Unknown Title')
            album = metadata.get('xesam:album', 'Unknown Album')
            
            # Get playback status
            playback_status = properties.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus')
            
            # Format the state based on playback status
            if playback_status == 'Playing':
                state = f"Playing {title} from {album}"
            elif playback_status == 'Paused':
                state = f"Paused: {title}"
            else:
                state = f"Stopped: {title}"
                
            return artist, state
        except dbus.exceptions.DBusException as e:
            print(f"DBus error: {e}")
            return None, None
        except Exception as e:
            print(f"Error getting MPRIS metadata: {e}")
            return None, None

    def populate_mpris_players(self):
        try:
            bus = dbus.SessionBus()
            services = [name for name in bus.list_names() if name.startswith("org.mpris.MediaPlayer2.")]
            self.current_mpris_players = set(services)
            self.mpris_combo.clear()
            self.mpris_combo.addItem("None")
            for name in services:
                try:
                    obj = bus.get_object(name, "/org/mpris/MediaPlayer2")
                    dbus.Interface(obj, dbus_interface="org.freedesktop.DBus.Properties")
                    self.mpris_combo.addItem(name)
                except dbus.exceptions.DBusException:
                    continue
        except Exception as e:
            print(f"Failed to query MPRIS players: {e}")

    def validate_app_id(self, app_id):
        """Validate Discord App ID format."""
        try:
            # Discord App IDs are typically 18-19 digits
            return app_id.isdigit() and len(app_id) >= 18
        except:
            return False

    def validate_url(self, url):
        """Validate URL format."""
        if not url:
            return False
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def validate_config(self, config):
        """Validate configuration data."""
        required_fields = {
            'app_id': str,
            'details': str,
            'state': str,
            'timestamp': str,
            'large_image': str,
            'large_text': str,
            'small_image': str,
            'small_text': str,
            'button1_text': str,
            'button1_url': str,
            'button2_text': str,
            'button2_url': str
        }
        
        # Check if all required fields exist and have correct types
        for field, field_type in required_fields.items():
            if field not in config:
                return False
            if not isinstance(config[field], field_type):
                return False
        
        # Validate timestamp type
        if config['timestamp'] not in ['None', 'Current Time', 'Custom Timestamp']:
            return False
            
        return True

    def save_config(self):
        """Save current configuration to file."""
        try:
            config = {
                'app_id': self.app_id_input.text(),
                'details': self.details_input.text(),
                'state': self.state_input.text(),
                'timestamp': self.timestamp_combo.currentText(),
                'large_image': self.large_image_input.text(),
                'large_text': self.large_image_text_input.text(),
                'small_image': self.small_image_input.text(),
                'small_text': self.small_image_text_input.text(),
                'button1_text': self.button1_text.text(),
                'button1_url': self.button1_url.text(),
                'button2_text': self.button2_text.text(),
                'button2_url': self.button2_url.text()
            }
            
            if self.validate_config(config):
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(config, f, indent=4)
                self.status_bar.showMessage("Configuration saved", 2000)
            else:
                self.status_bar.showMessage("Invalid configuration data", 3000)
        except Exception as e:
            self.status_bar.showMessage(f"Error saving configuration: {str(e)}", 5000)
            print(f"Error saving configuration: {e}")

    def load_config(self):
        """Load configuration from file."""
        try:
            if not os.path.exists(CONFIG_FILE):
                return
                
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                
            if not self.validate_config(config):
                self.status_bar.showMessage("Invalid configuration file", 3000)
                return
                
            self.app_id_input.setText(config['app_id'])
            self.details_input.setText(config['details'])
            self.state_input.setText(config['state'])
            self.large_image_input.setText(config['large_image'])
            self.large_image_text_input.setText(config['large_text'])
            self.small_image_input.setText(config['small_image'])
            self.small_image_text_input.setText(config['small_text'])
            self.button1_text.setText(config['button1_text'])
            self.button1_url.setText(config['button1_url'])
            self.button2_text.setText(config['button2_text'])
            self.button2_url.setText(config['button2_url'])
            
            # Set timestamp type
            index = self.timestamp_combo.findText(config['timestamp'])
            if index >= 0:
                self.timestamp_combo.setCurrentIndex(index)
                if config['timestamp'] == 'Custom Timestamp':
                    self.custom_timestamp_input.show()
                    
            self.status_bar.showMessage("Configuration loaded", 2000)
        except Exception as e:
            self.status_bar.showMessage(f"Error loading configuration: {str(e)}", 5000)
            print(f"Error loading configuration: {e}")

    def refresh_mpris_players(self):
        """Refresh MPRIS players list with improved error handling."""
        try:
            bus = dbus.SessionBus()
            current_players = set()
            
            # Get all MPRIS players
            for service in bus.list_names():
                if service.startswith('org.mpris.MediaPlayer2.'):
                    current_players.add(service)
            
            # Update combo box if players changed
            if current_players != self.current_mpris_players:
                self.current_mpris_players = current_players
                current_selection = self.mpris_combo.currentText()
                
                self.mpris_combo.clear()
                self.mpris_combo.addItem("None")
                
                for player in sorted(current_players):
                    # Extract player name from service name
                    player_name = player.replace('org.mpris.MediaPlayer2.', '')
                    self.mpris_combo.addItem(player)
                
                # Restore previous selection if possible
                index = self.mpris_combo.findText(current_selection)
                if index >= 0:
                    self.mpris_combo.setCurrentIndex(index)
                else:
                    self.mpris_combo.setCurrentIndex(0)
                    
                self.status_bar.showMessage("MPRIS players refreshed", 2000)
        except Exception as e:
            print(f"Error refreshing MPRIS players: {e}")
            self.status_bar.showMessage("Error refreshing MPRIS players", 3000)

    def setup_system_tray(self):
        """Set up system tray icon with proper icon"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create a simple icon (you can replace this with your own icon file)
        icon_pixmap = QPixmap(32, 32)
        icon_pixmap.fill(Qt.GlobalColor.blue)  # Temporary blue square icon
        self.tray_icon.setIcon(QIcon(icon_pixmap))
        
        self.tray_icon.setToolTip("Custom Rich Presence")
        
        # Create tray menu
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.close_application)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def closeEvent(self, event):
        """Handle window close event"""
        reply = QMessageBox.question(
            self, 'Confirm Exit',
            "Do you want to minimize to tray instead of quitting?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Custom Rich Presence",
                "Application minimized to tray. Right-click the tray icon to show or quit.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            self.close_application()
            event.accept()

    def close_application(self):
        """Clean up and close the application"""
        try:
            if self.rpc_connected:
                self.rpc.clear()
            self.mpris_refresh_timer.stop()
            self.refresh_timer.stop()
            self.tray_icon.hide()
            QApplication.quit()
        except Exception as e:
            print(f"Error during cleanup: {e}")
            QApplication.quit()

    def clear_presence(self):
        """Clear the current Discord presence"""
        if self.rpc_connected:
            try:
                self.rpc.clear()
                self.status_bar.showMessage("Presence cleared", 3000)
                self.status_indicator.setText("Status: Connected (No Presence)")
                self.status_indicator.setStyleSheet("color: #FFA500;")
            except Exception as e:
                self.status_bar.showMessage(f"Error clearing presence: {str(e)}", 5000)
        else:
            self.status_bar.showMessage("Not connected to Discord", 3000)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomRPCApp()
    window.show()
    sys.exit(app.exec())
