import sys
import json
import psycopg2
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QTextEdit, QDateEdit, QPushButton, QScrollArea, QMessageBox)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QCheckBox, QComboBox, QColorDialog
from PyQt5.QtGui import QColor

from dotenv import load_dotenv
import os
from PyQt5.QtMultimedia import QSound
from PyQt5.QtCore import QTime




load_dotenv()

class DatabaseWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        print("TimeboxingApp initialized")

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))




class TimeboxingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Timeboxing Daily Planner")
        self.setGeometry(100, 100, 1000, 800)
        self.setStyleSheet("background-color: #f0f4f8;")
        self.worker_threads = []
        self.alert_timer = QTimer(self)
        self.alert_timer.timeout.connect(self.check_alerts)
        self.alert_timer.start(60000)  # Check every minute
        self.init_db()
        self.init_ui()
        
        # Load the entry for the current date after a short delay
        QTimer.singleShot(100, self.load_entry)
        
        print("TimeboxingApp initialized")
        print("Init complete")


    def check_alerts(self):
        current_time = QTime.currentTime()
        current_time_str = current_time.toString("HH:mm")
        
        for time, task_combo in self.schedule_inputs.items():
            task = task_combo.currentText()
            if task:
                if time == current_time_str:
                    if self.start_alert_checkbox.isChecked():
                        self.show_alert(f"Start task: {task}")
                elif self.time_diff(time, current_time_str) == 1:
                    if self.end_alert_checkbox.isChecked():
                        self.show_alert(f"End task soon: {task}")



    def show_alert(self, message):
        QSound.play("path/to/your/sound/file.wav")  # Play a sound
        QMessageBox.information(self, "Task Alert", message)

    def time_diff(self, time1, time2):
        t1 = QTime.fromString(time1, "HH:mm")
        t2 = QTime.fromString(time2, "HH:mm")
        return t1.secsTo(t2) // 60  # Return difference in minutes


    def change_font_size(self, size_text):
        size_map = {'Small': 8, 'Medium': 10, 'Large': 12}
        size = size_map[size_text]
        self.setStyleSheet(f"font-size: {size}pt;")
        self.update_widgets_font_size(size)

    def update_widgets_font_size(self, size):
        for widget in self.findChildren(QWidget):
            font = widget.font()
            font.setPointSize(size)
            widget.setFont(font)
        
        # Update specific widgets that might need adjustments
        self.top_priorities.setStyleSheet(f"font-size: {size}pt; background-color: white; border: 1px solid #ddd; border-radius: 4px;")
        self.brain_dump.setStyleSheet(f"font-size: {size}pt; background-color: white; border: 1px solid #ddd; border-radius: 4px;")
        
        for combo in self.schedule_inputs.values():
            combo.setStyleSheet(f"font-size: {size}pt;")
        
        # Refresh the layout
        self.update()



    def closeEvent(self, event):
        try:
            if self.conn:
                self.conn.close()
            print("Database connection closed.")
        except Exception as e:
            print(f"Error closing database connection: {e}")
        event.accept()


    def init_db(self):
        self.conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST')
        )
        self.conn.set_session(autocommit=True)  # This will auto-commit transactions
        self.cursor = self.conn.cursor()
        self.check_table_structure()
        self.add_unique_constraint()
        

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Header
        header_layout = QHBoxLayout()
        icon_label = QLabel("⏱")
        icon_label.setStyleSheet("font-size: 24px; background-color: #34495e; color: white; padding: 5px; border-radius: 5px;")
        title_label = QLabel("TIMEBOXING")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #34495e;")
        subtitle_label = QLabel("Daily Planner")
        subtitle_label.setStyleSheet("font-size: 18px; color: #7f8c8d;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(subtitle_label)
        main_layout.addLayout(header_layout)

        # Date picker
        date_layout = QHBoxLayout()
        date_label = QLabel("Date:")
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.on_date_changed)
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_edit)
        date_layout.addStretch()
        main_layout.addLayout(date_layout)


        # Main content area
        content_layout = QHBoxLayout()

        # Left column
        left_column = QVBoxLayout()
        
        # Top Priorities
        left_column.addWidget(QLabel("Top Priorities:"))
        self.top_priorities = QTextEdit()
        self.top_priorities.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 4px;")
        self.top_priorities.textChanged.connect(self.update_task_options)

        left_column.addWidget(self.top_priorities)

        # Brain Dump
        left_column.addWidget(QLabel("Brain-Dump:"))
        self.brain_dump = QTextEdit()
        self.brain_dump.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 4px;")
        self.brain_dump.textChanged.connect(self.update_task_options)
        left_column.addWidget(self.brain_dump)



        # Font size selector
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("Font Size:"))
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(['Small', 'Medium', 'Large'])
        self.font_size_combo.setCurrentIndex(1)  # Set 'Medium' as default
        self.font_size_combo.currentTextChanged.connect(self.change_font_size)
        font_size_layout.addWidget(self.font_size_combo)

        # Add this layout to your main layout, for example:
        main_layout.addLayout(font_size_layout)




        # Alert controls
        alert_layout = QHBoxLayout()
        alert_layout.addWidget(QLabel("Alerts:"))

        self.start_alert_checkbox = QCheckBox("Start Task")
        self.end_alert_checkbox = QCheckBox("End Task")
        alert_layout.addWidget(self.start_alert_checkbox)
        alert_layout.addWidget(self.end_alert_checkbox)

        # Add this layout near your font size selector
        main_layout.addLayout(alert_layout)


        # Add left column to content layout
        content_layout.addLayout(left_column, 1)

        # Right column (Schedule)
        right_column = QVBoxLayout()
        right_column.addWidget(QLabel("Schedule:"))
        
        schedule_widget = QWidget()
        self.schedule_layout = QVBoxLayout(schedule_widget)
        
        self.schedule_inputs = {}
        self.schedule_checkboxes = {}
        self.schedule_colors = {}
        for hour in range(5, 24):
            for minute in ['00', '30']:
                time = f"{hour:02d}:{minute}"
                hour_layout = QHBoxLayout()
                
                checkbox = QCheckBox()
                hour_layout.addWidget(checkbox)
                
                hour_layout.addWidget(QLabel(time))
                
                task_combo = QComboBox()
                task_combo.setEditable(True)
                hour_layout.addWidget(task_combo)
                
                color_button = QPushButton("Color")
                color_button.clicked.connect(lambda _, t=time: self.choose_color(t))
                hour_layout.addWidget(color_button)
                
                self.schedule_layout.addLayout(hour_layout)
                self.schedule_inputs[time] = task_combo
                self.schedule_checkboxes[time] = checkbox
                self.schedule_colors[time] = QColor(255, 255, 255)  # Default white

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(schedule_widget)
        right_column.addWidget(scroll_area)

        # Add right column to content layout
        content_layout.addLayout(right_column, 1)

        main_layout.addLayout(content_layout)
        # Save button
        save_button = QPushButton("Save")
        save_button.setStyleSheet("background-color: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 4px;")
        save_button.clicked.connect(self.save_entry)
        main_layout.addWidget(save_button, alignment=Qt.AlignCenter)
        self.change_font_size('Medium')

        



    def choose_color(self, time):
        color = QColorDialog.getColor()
        if color.isValid():
            self.schedule_colors[time] = color
            self.update_schedule_colors()



    def update_schedule_colors(self):
        for time, combo in self.schedule_inputs.items():
            combo.setStyleSheet(f"background-color: {self.schedule_colors[time].name()};")

    def update_task_options(self):
        top_priorities = self.top_priorities.toPlainText().split('\n')
        brain_dump = self.brain_dump.toPlainText().split('\n')
        all_tasks = top_priorities + brain_dump
        all_tasks = [task.strip() for task in all_tasks if task.strip()]
        
        for combo in self.schedule_inputs.values():
            current_text = combo.currentText()
            combo.clear()
            combo.addItems(all_tasks)
            combo.setCurrentText(current_text)



    def check_table_structure(self):
        self.cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'timeboxing_entry'
        """)
        columns = self.cursor.fetchall()
        print("Existing table structure:")
        for column in columns:
            print(f"{column[0]}: {column[1]}")
        
        if not columns:
            print("Table 'timeboxing_entry' does not exist. Creating it now.")
            self.cursor.execute('''
                CREATE TABLE timeboxing_entry (
                    id SERIAL PRIMARY KEY,
                    date DATE UNIQUE NOT NULL,
                    top_priorities TEXT,
                    brain_dump TEXT,
                    schedule JSONB
                )
            ''')
            self.conn.commit()
            print("Table created successfully.")


    def add_unique_constraint(self):
        try:
            self.cursor.execute("""
                ALTER TABLE timeboxing_entry
                ADD CONSTRAINT unique_date UNIQUE (date);
            """)
            self.conn.commit()
            print("Unique constraint added to date column.")
        except psycopg2.errors.DuplicateTable:
            print("Unique constraint already exists on date column.")
        except Exception as e:
            print(f"Error adding unique constraint: {e}")


    def save_entry(self):
        print("Starting save_entry")
        date = self.date_edit.date().toString("yyyy-MM-dd")
        top_priorities = self.top_priorities.toPlainText()
        brain_dump = self.brain_dump.toPlainText()
        schedule = {
            time: {
                'task': input.currentText(),
                'checked': self.schedule_checkboxes[time].isChecked(),
                'color': self.schedule_colors[time].name()
            } for time, input in self.schedule_inputs.items()
        }
        schedule_json = json.dumps(schedule)

        try:
            result = self._save_entry(date, top_priorities, brain_dump, schedule_json)
            self.on_save_finished(result)
        except Exception as e:
            self.on_save_error(str(e))
        
        self.update_alerts()
        print("Finished save_entry")

    def update_alerts(self):
        if self.start_alert_checkbox.isChecked() or self.end_alert_checkbox.isChecked():
            self.alert_timer.start(60000)  # Check every minute
        else:
            self.alert_timer.stop()

    def _save_entry(self, date, top_priorities, brain_dump, schedule):
        try:
            self.conn.rollback()
            
            self.cursor.execute("SELECT id FROM timeboxing_entry WHERE date = %s", (date,))
            existing_entry = self.cursor.fetchone()

            if existing_entry:
                self.cursor.execute('''
                    UPDATE timeboxing_entry
                    SET top_priorities = %s, brain_dump = %s, schedule = %s
                    WHERE date = %s
                ''', (top_priorities, brain_dump, schedule, date))
            else:
                self.cursor.execute('''
                    INSERT INTO timeboxing_entry (date, top_priorities, brain_dump, schedule)
                    VALUES (%s, %s, %s, %s)
                ''', (date, top_priorities, brain_dump, schedule))

            self.conn.commit()
            return "Entry saved successfully!"
        except Exception as e:
            self.conn.rollback()
            raise e

    def on_save_finished(self, message):
        print("Starting on_save_finished")
        QMessageBox.information(self, "Success", message)
        print("Finished on_save_finished")

    def on_save_error(self, error_message):
        print(f"Save error: {error_message}")
        QMessageBox.critical(self, "Error", f"Failed to save entry: {error_message}")
        if self.sender() in self.worker_threads:
            self.worker_threads.remove(self.sender())

    

    def load_entry(self, date=None):
        if date is None:
            date = self.date_edit.date().toString("yyyy-MM-dd")
        elif isinstance(date, QDate):
            date = date.toString("yyyy-MM-dd")
        
        worker = DatabaseWorker(self._load_entry, date)
        worker.finished.connect(self.on_load_finished)
        worker.error.connect(self.on_load_error)
        worker.start()
        self.worker_threads.append(worker)


    def on_date_changed(self, new_date):
        date_str = new_date.toString("yyyy-MM-dd")
        self.load_entry(date_str)

    def _load_entry(self, date):
        try:
            self.conn.rollback()
            
            self.cursor.execute("SELECT * FROM timeboxing_entry WHERE date = %s", (date,))
            entry = self.cursor.fetchone()

            if entry:
                id, date, top_priorities, brain_dump, schedule = entry
                # Ensure schedule is a JSON string
                if isinstance(schedule, dict):
                    schedule = json.dumps(schedule)
                return (id, date, top_priorities, brain_dump, schedule)
            return None  # Return None if no entry is found
        except Exception as e:
            print(f"Error in _load_entry: {e}")  # Print the error for debugging
            return None  # Return None on any error

    def on_load_finished(self, entry):
        if entry:
            _, date, top_priorities, brain_dump, schedule = entry
            self.top_priorities.setPlainText(top_priorities)
            self.brain_dump.setPlainText(brain_dump)
            
            if isinstance(schedule, str):
                try:
                    schedule_dict = json.loads(schedule)
                except json.JSONDecodeError:
                    schedule_dict = {}
            elif isinstance(schedule, dict):
                schedule_dict = schedule
            else:
                schedule_dict = {}
            
            for time, data in schedule_dict.items():
                if time in self.schedule_inputs:
                    if isinstance(data, str):
                        # Old format: just a string task
                        self.schedule_inputs[time].setCurrentText(data)
                        self.schedule_checkboxes[time].setChecked(False)
                        self.schedule_colors[time] = QColor(255, 255, 255)
                    elif isinstance(data, dict):
                        # New format: dictionary with task, checked, and color
                        self.schedule_inputs[time].setCurrentText(data.get('task', ''))
                        self.schedule_checkboxes[time].setChecked(data.get('checked', False))
                        self.schedule_colors[time] = QColor(data.get('color', '#FFFFFF'))
                    else:
                        # Unexpected format, set to default values
                        self.schedule_inputs[time].setCurrentText('')
                        self.schedule_checkboxes[time].setChecked(False)
                        self.schedule_colors[time] = QColor(255, 255, 255)
            
            self.update_schedule_colors()
        else:
            # Clear all fields if no entry is found
            self.top_priorities.clear()
            self.brain_dump.clear()
            for input in self.schedule_inputs.values():
                input.setCurrentText("")
            for checkbox in self.schedule_checkboxes.values():
                checkbox.setChecked(False)
            for time in self.schedule_colors:
                self.schedule_colors[time] = QColor(255, 255, 255)
            self.update_schedule_colors()
        
        self.update_task_options()
        
        if self.sender() in self.worker_threads:
            self.worker_threads.remove(self.sender())

    def on_load_error(self, error_message):
        QMessageBox.critical(self, "Error", f"Failed to load entry: {error_message}")
        if self.sender() in self.worker_threads:
            self.worker_threads.remove(self.sender())



    def closeEvent(self, event):
        # Wait for all worker threads to finish
        for worker in self.worker_threads:
            worker.wait()
        
        try:
            if self.conn:
                self.conn.close()
            print("Database connection closed.")
        except Exception as e:
            print(f"Error closing database connection: {e}")
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TimeboxingApp()
    window.show()
    
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting...")
    except Exception as e:
        print(f"Unexpected error occurred: {e}")
    finally:
        window.close()
        sys.exit(0)