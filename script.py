import sys
import time
import json
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QDateTimeEdit
from pypresence import Presence

CONFIG_FILE = "config.json"

class CustomRPCApp(QWidget):
    def __init__(self):
        super().__init__()
        self.rpc_connected = False
        self.rpc = None  # Placeholder for Presence object
        self.init_ui()
        self.load_config()  # ✅ Load saved settings on startup

    def init_ui(self):
        self.setWindowTitle("Custom Rich Presence")
        self.setGeometry(100, 100, 400, 500)
        layout = QVBoxLayout()

        # App ID Input
        self.app_id_label = QLabel("Discord App ID:")
        self.app_id_input = QLineEdit()
        layout.addWidget(self.app_id_label)
        layout.addWidget(self.app_id_input)

        # Connection Button
        self.connect_button = QPushButton("Connect to Discord")
        self.connect_button.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_button)

        # Details Input
        self.details_label = QLabel("Details:")
        self.details_input = QLineEdit()
        layout.addWidget(self.details_label)
        layout.addWidget(self.details_input)

        # State Input
        self.state_label = QLabel("State:")
        self.state_input = QLineEdit()
        layout.addWidget(self.state_label)
        layout.addWidget(self.state_input)

        # Timestamp Options
        self.timestamp_label = QLabel("Timestamp:")
        self.timestamp_combo = QComboBox()
        self.timestamp_combo.addItems(["None", "Current Time", "Custom Timestamp"])
        self.timestamp_combo.currentIndexChanged.connect(self.toggle_custom_timestamp)
        layout.addWidget(self.timestamp_label)
        layout.addWidget(self.timestamp_combo)

        # Custom Timestamp Input (Hidden by Default)
        self.custom_timestamp_input = QDateTimeEdit(datetime.now())
        self.custom_timestamp_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.custom_timestamp_input.setCalendarPopup(True)
        self.custom_timestamp_input.hide()
        layout.addWidget(self.custom_timestamp_input)

        # Large Image Key (Default = avatar)
        self.large_image_label = QLabel("Large Image Key:")
        self.large_image_input = QLineEdit()
        self.large_image_input.setText("avatar")  # Default value
        layout.addWidget(self.large_image_label)
        layout.addWidget(self.large_image_input)

        # Large Image Hover Text
        self.large_image_text_label = QLabel("Large Image Hover Text:")
        self.large_image_text_input = QLineEdit()
        layout.addWidget(self.large_image_text_label)
        layout.addWidget(self.large_image_text_input)

        # Small Image Key
        self.small_image_label = QLabel("Small Image Key:")
        self.small_image_input = QLineEdit()
        layout.addWidget(self.small_image_label)
        layout.addWidget(self.small_image_input)

        # Small Image Hover Text
        self.small_image_text_label = QLabel("Small Image Hover Text:")
        self.small_image_text_input = QLineEdit()
        layout.addWidget(self.small_image_text_label)
        layout.addWidget(self.small_image_text_input)

        # Button 1
        self.button1_label = QLabel("Button 1 Text:")
        self.button1_text = QLineEdit()
        self.button1_url = QLineEdit()
        self.button1_url.setPlaceholderText("https://example.com")
        layout.addWidget(self.button1_label)
        layout.addWidget(self.button1_text)
        layout.addWidget(self.button1_url)

        # Button 2
        self.button2_label = QLabel("Button 2 Text:")
        self.button2_text = QLineEdit()
        self.button2_url = QLineEdit()
        self.button2_url.setPlaceholderText("https://example.com")
        layout.addWidget(self.button2_label)
        layout.addWidget(self.button2_text)
        layout.addWidget(self.button2_url)

        # Update Presence Button
        self.update_button = QPushButton("Update Presence")
        self.update_button.clicked.connect(self.update_presence)  # ✅ Fixed missing function
        layout.addWidget(self.update_button)

        self.setLayout(layout)

    def toggle_connection(self):
        """Connect or Disconnect from Discord RPC."""
        app_id = self.app_id_input.text().strip()
        if not app_id:
            print("Please enter a Discord App ID.")
            return

        if not self.rpc_connected:
            try:
                self.rpc = Presence(app_id)
                self.rpc.connect()
                self.rpc_connected = True
                self.connect_button.setText("Connected to Discord")
                self.save_config()  # Save app ID
            except Exception as e:
                self.connect_button.setText("Connection Failed")
                print(f"Error connecting to Discord: {e}")
        else:
            self.rpc.clear()
            self.rpc_connected = False
            self.connect_button.setText("Connect to Discord")

    def toggle_custom_timestamp(self):
        """Show or hide the custom timestamp input field based on selection."""
        if self.timestamp_combo.currentText() == "Custom Timestamp":
            self.custom_timestamp_input.show()
        else:
            self.custom_timestamp_input.hide()

    def update_presence(self):
        """Update the Discord Rich Presence status."""
        if not self.rpc_connected:
            print("Not connected to Discord.")
            return

        details = self.details_input.text()
        state = self.state_input.text()
        timestamp = self.timestamp_combo.currentText()
        large_image = self.large_image_input.text()
        large_text = self.large_image_text_input.text()
        small_image = self.small_image_input.text()
        small_text = self.small_image_text_input.text()

        # Handle Timestamps
        start_time = None
        if timestamp == "Current Time":
            start_time = int(time.time())
        elif timestamp == "Custom Timestamp":
            dt = self.custom_timestamp_input.dateTime().toPyDateTime()
            start_time = int(dt.timestamp())

        # Handle Buttons
        buttons = []
        if self.button1_text.text() and self.button1_url.text():
            url = self.button1_url.text().strip()
            if not url.startswith("https://"):
                url = "https://" + url
            buttons.append({"label": self.button1_text.text(), "url": url})

        if self.button2_text.text() and self.button2_url.text():
            url = self.button2_url.text().strip()
            if not url.startswith("https://"):
                url = "https://" + url
            buttons.append({"label": self.button2_text.text(), "url": url})

        # Update Presence
        try:
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
            print("Discord Presence Updated!")
            self.save_config()  # Save settings
        except Exception as e:
            print(f"Error updating presence: {e}")

    def save_config(self):
        """Save user settings to a JSON file."""
        config = {
            "app_id": self.app_id_input.text(),
            "details": self.details_input.text(),
            "state": self.state_input.text(),
            "timestamp": self.timestamp_combo.currentText(),
            "large_image": self.large_image_input.text(),
            "large_text": self.large_image_text_input.text(),
            "small_image": self.small_image_input.text(),
            "small_text": self.small_image_text_input.text(),
            "button1_text": self.button1_text.text(),
            "button1_url": self.button1_url.text(),
            "button2_text": self.button2_text.text(),
            "button2_url": self.button2_url.text(),
        }
        with open(CONFIG_FILE, "w") as file:
            json.dump(config, file, indent=4)

    def load_config(self):
        """Load user settings from a JSON file."""
        try:
            with open(CONFIG_FILE, "r") as file:
                config = json.load(file)

            self.app_id_input.setText(config.get("app_id", ""))
            self.details_input.setText(config.get("details", ""))
            self.state_input.setText(config.get("state", ""))
            self.timestamp_combo.setCurrentText(config.get("timestamp", "None"))
            self.large_image_input.setText(config.get("large_image", "avatar"))
            self.large_image_text_input.setText(config.get("large_text", ""))
            self.small_image_input.setText(config.get("small_image", ""))
            self.small_image_text_input.setText(config.get("small_text", ""))
            self.button1_text.setText(config.get("button1_text", ""))
            self.button1_url.setText(config.get("button1_url", ""))
            self.button2_text.setText(config.get("button2_text", ""))
            self.button2_url.setText(config.get("button2_url", ""))
        except FileNotFoundError:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomRPCApp()
    window.show()
    sys.exit(app.exec())
