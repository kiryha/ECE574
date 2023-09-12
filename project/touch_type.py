"""
ECE579 Embedded Systems

Final Project - Touch Type Workout - The keyboard training system for kids and seniors
"""

import os
import time
import json
from PySide2 import QtWidgets, QtCore, QtGui
from ui import ui_main
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class StatisticCanvas(FigureCanvas):
    def __init__(self, parent=None):

        fig = Figure(dpi=100)
        self.axes = fig.subplots(3, 1, sharex=True)
        self.compute_initial_figure()

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


class MyStaticMplCanvas(StatisticCanvas):
    def __init__(self, json_file, parent=None):
        self.json_file = json_file
        super().__init__(parent)

        self.statistics_data = None
        self.times = None
        self.wpm = None
        self.errors = None
        self.rhythm = None

    def load_data(self):

        with open(self.json_file) as f:
            self.statistics_data = json.load(f)

        self.times = list(self.statistics_data.keys())

        # Calculate WPM
        self.wpm = []
        for value in self.statistics_data.values():
            cps = value['characters']/value['time']
            wpm = (cps * 60) / 5
            self.wpm.append(wpm)

        # Calculate errors
        self.errors = []
        for value in self.statistics_data.values():
            error_value = int((value['errors']/value['characters'])*100)
            self.errors.append(error_value)

        # Get rhythm
        self.rhythm = []
        for value in self.statistics_data.values():
            self.rhythm.append(value['rhythm'])

    def plot(self):
        """
        Draw graphs from data
        """

        linewidth = 4

        self.axes[0].plot(self.times, self.wpm, 'r', label='Words Per Minute', linewidth=linewidth)
        self.axes[1].plot(self.times, self.errors, 'b', label='Errors %', linewidth=linewidth)
        self.axes[2].plot(self.times, self.rhythm, 'g', label='Typing Rhythm',  linewidth=linewidth)

    def compute_initial_figure(self):

        self.load_data()
        self.plot()

        for axe in self.axes:
            axe.legend()
            axe.tick_params(axis='both', which='major', labelsize=8)

        self.axes[0].figure.tight_layout()

    def update_figure(self):

        for axe in self.axes:
            axe.clear()

        self.load_data()
        self.plot()

        for axe in self.axes:
            axe.legend()
            axe.tick_params(axis='both', which='major', labelsize=8)

        self.axes[0].figure.tight_layout()
        self.draw()


class TouchType(QtWidgets.QMainWindow, ui_main.Ui_TouchType):
    def __init__(self):
        super(TouchType, self).__init__()
        self.setupUi(self)
        font = QtGui.QFont('Free Range Hive')
        font.setPointSize(48)
        self.labTasks.setFont(font)
        font.setPointSize(32)
        self.labRecommendation.setFont(font)
        self.labTasks.setText('PRESS  <font color="red">START LESSON</font> OR <font color="red">START TEST</font>')

        # Data
        self.statistic = f'{user}/Documents/touch_type_stat.json'
        self.keyboard_blank = f'{root}/data/images/_blank.png'
        self.keyboard_all = f'{root}/data/images/_all.png'
        self.lessons = f'{root}/data/lessons.json'
        self.tests = f'{root}/data/tests.json'
        self.lessons_data = None
        self.tests_data = None

        # Lesson flow control
        self.lesson_started = False
        self.lesson_name = None
        self.sequence_ended = False
        self.sequence_text = None
        self.number_of_sequences = 0
        self.current_sequence = 0
        self.current_string = 0
        self.string_length = None
        self.user_input = ''

        # Test flow control
        self.test_started = False
        self.test_name = None

        # Statistic flow control
        self.start_wpm = False
        self.time = None
        self.wpm_lesson_time = 0
        self.wpm_lesson_characters = 0
        self.errors = 0
        self.key_stamps = []

        # Setup UI with data
        self.init_ui()

        # Setup graph
        self.canvas = MyStaticMplCanvas(self.statistic, self)
        self.layStatistics.addWidget(self.canvas)

        # UI calls
        self.btnStartLesson.pressed.connect(self.start_lesson)
        self.btnStartTest.pressed.connect(self.start_test)
        self.btnReloadStatistics.pressed.connect(self.reload_stat)

    # UI setup
    def reset_ui(self):

        pixmap = QtGui.QPixmap(self.keyboard_blank)
        self.labPictures.setPixmap(pixmap)
        self.labTasks.clear()

        if self.lesson_started:
            string = 'LESSON'
        else:
            string = 'TEST'

        # Display lesson statistics
        self.labTasks.setText(f'{string} <font color="red">COMPLETE!</font> '
                              f'WPM: {self.cps_to_wpm()}, '
                              f'ERR: {self.errors_rate()}%, '
                              f'RHM: {self.rhythm()}')

    def init_ui(self):

        # Create empty statistic file if it is not exists:
        if not os.path.exists(self.statistic):
            with open(self.statistic, 'w') as file_content:
                json.dump({}, file_content, indent=4)

        # Tests and Lessons
        # Load keyboard
        pixmap = QtGui.QPixmap(self.keyboard_blank)
        self.labPictures.setPixmap(pixmap)

        # Load lessons and tests
        with open(self.lessons, 'r') as file_content:
            self.lessons_data = json.load(file_content)

        with open(self.tests, 'r') as file_content:
            self.tests_data = json.load(file_content)

        self.comLessons.addItems(self.lessons_data.keys())
        self.comTests.addItems(self.tests_data.keys())

        # Show recommendations
        self.recommendation()

    # Statistics
    def recommendation(self):
        """
        Read statistics of last session and provide recommendations
        """

        with open(self.statistic) as f:
            statistics_data = json.load(f)

        last_key = len(statistics_data.keys()) - 1
        last_session_data = statistics_data.get(str(last_key))

        if not last_session_data:
            print('>> The Statistics data is not available!')
            return

        # Get parameters data
        wpm = self.cps_to_wpm(last_session_data['characters'], last_session_data['time'])
        errors_rate = self.errors_rate(last_session_data['characters'], last_session_data['errors'])
        rhythm = last_session_data["rhythm"]
        # print(f'Last Session data: {wpm}, {errors_rate}, {rhythm}')

        # Calibrate parameters
        wpm_high = False
        wpm_low = False
        error_high = False
        error_low = False
        rhythm_high = False
        rhythm_low = False

        if wpm < 20:
            wpm_low = True
        else:
            wpm_high = True
        if errors_rate > 50:
            error_high = True
        else:
            error_low = True
        if rhythm > 5:
            rhythm_low = True
        else:
            rhythm_high = True

        # Calculate recommendation
        string = f'You are awesome! WPM: <font color="red">{wpm}</font>, ' \
                 f'ERRORS:  <font color="red">{errors_rate}</font>, ' \
                 f'RHYTHM: <font color="red">{rhythm}</font>!'

        # High WPM, High Error Rate, High Rhythm
        if wpm_high and error_high and rhythm_high:
            string = f'Reduce speed and focus on accuracy. Try to maintain a steady rhythm when typing.'

        # High WPM, High Error Rate, Low Rhythm
        if wpm_high and error_high and rhythm_low:
            string = f'Slow down your typing speed and concentrate on accuracy.'

        # High WPM, Low Error Rate, High Rhythm
        if wpm_high and error_low and rhythm_high:
            string = f'Your rhythm is inconsistent. Try to establish a steady pace to increase efficiency.'

        # High WPM, Low Error Rate, Low Rhythm
        if wpm_high and error_low and rhythm_low:
            string = f'Your typing speed and accuracy are impressive, and you maintain a steady rhythm!'

        # Low WPM, High Error Rate, High Rhythm
        if wpm_low and error_high and rhythm_high:
            string = f'Practice typing at a slower pace, concentrate on accuracy, try to develop a consistent rhythm.'

        # Low WPM, High Error Rate, Low Rhythm
        if wpm_low and error_high and rhythm_low:
            string = f'Focus more on accuracy and gradually increase your speed.'

        # Low WPM, Low Error Rate, High Rhythm
        if wpm_low and error_low and rhythm_high:
            string = f'You need to improve your typing speed and establish a steady rhythm.'

        # Low WPM, Low Error Rate, Low Rhythm
        if wpm_low and error_low and rhythm_low:
            string = f'Accuracy and rhythm are great! Focus on increasing your typing speed through practice.'

        self.labRecommendation.setText(string)

    def rhythm(self):
        """
        The rhythm value provides a measure of the speed and consistency of typing.

        A lower rhythm value indicates faster and more consistent typing, since the time between subsequent
        key presses is less.
        A higher rhythm value indicates slower and/or less consistent typing,
        since the time between subsequent key presses is more.
        """

        # Calculate the differences between subsequent timestamps
        intervals = [j - i for i, j in zip(self.key_stamps[:-1], self.key_stamps[1:])]

        # Get rhythm as average of intervals
        rhythm = sum(intervals) / len(intervals)

        # return round(rhythm, 2)
        return int(rhythm*10)

    def errors_rate(self, characters=None, errors=None):
        """
        Calculates number of incorrect keys pressed by user
        """

        if not characters:
            rate = self.errors / self.wpm_lesson_characters
        else:
            rate = errors / characters

        return int(rate * 100)

    def cps_to_wpm(self, characters=None, lesson_time=None):
        """
        words per minute = (characters per second * 60) / letters in word
        f"{wpm:.2f}"
        """

        if not characters:
            cps = self.wpm_lesson_characters/self.wpm_lesson_time
        else:
            cps = characters / lesson_time

        wpm = (cps*60)/5

        return int(wpm)

    def sequence_wpm(self):
        """
        Calculate sequence typing time (seconds)
        """

        sequence_time = time.time() - self.time
        self.wpm_lesson_time += sequence_time
        self.start_wpm = False

        # print(f'sequence_time = {sequence_time}')

    def record_statistics(self):
        """
        Calculate and record for each lesson or test session:
            - Words per Minute

        statistics = { 'session_index': {session data}}
            session data = WPM: [letters, time]
        """

        # Load existing stat
        with open(self.statistic, 'r') as file_content:
            statistic_data = json.load(file_content)

        # Calculate Stat
        session_data = {'characters': self.wpm_lesson_characters,
                        'time': self.wpm_lesson_time,
                        'errors': self.errors,
                        'rhythm': self.rhythm()}

        if not statistic_data.keys():  # First launch
            statistic_data[0] = session_data
        else:
            number_of_sessions = len(statistic_data.keys())
            statistic_data[number_of_sessions] = session_data

        # Save updated stat
        with open(self.statistic, 'w') as file_content:
            json.dump(statistic_data, file_content, indent=4)

    # Flow control
    def check_user_input(self, user_text):
        """
        Paint green correct keys, red - incorrect
        """

        colored_string = ""

        for correct_character, user_character in zip(self.sequence_text, user_text):
            # Correct characters
            if correct_character == user_character:
                colored_string += f"<font color='green'>{user_character}</font>"
            # Incorrect characters
            else:
                colored_string += f"<font color='red'>{user_character}</font>"

        # Preserve the rest of the original string after the user's input
        colored_string += self.sequence_text[len(user_text):]

        # Update the label text
        self.labTasks.setText(colored_string)

    def set_next_picture(self):

        # print(f' self.sequence_text = { self.sequence_text}')
        # print(f' self.current_string = { self.current_string}')

        # Get pressed key
        if self.sequence_text[self.current_string] == ' ':
            key = '_space'
        elif self.sequence_text[self.current_string] == '.':
            key = '_dot'
        elif self.sequence_text[self.current_string] == ',':
            key = '_comma'
        else:
            key = self.sequence_text[self.current_string].upper()

        # Show next letter in UI
        pixmap = f'{root}/data/images/{key}.png'
        self.labPictures.setPixmap(pixmap)

    def start_sequence(self):
        """
        Display sequence of strings for current lesson
        """

        if self.lesson_started:
            self.sequence_text = self.lessons_data[self.lesson_name]['sequences'][self.current_sequence]
        else:
            self.sequence_text = self.tests_data[self.test_name]['sequences'][self.current_sequence]

        self.labTasks.setText(self.sequence_text)

        pixmap = f'{root}/data/images/{self.sequence_text[self.current_string].upper()}.png'
        self.labPictures.setPixmap(pixmap)

        self.current_string = 1
        self.string_length = len(self.sequence_text)

        # Stat
        self.wpm_lesson_characters += self.string_length

    def keyPressEvent(self, event):
        """
        Lesson Flow control
        """

        if self.lesson_started or self.test_started:

            # print(f'current key = {event.key()}')
            # print(f'current sequence = {self.current_sequence}')
            # print(f'string_length = {self.string_length}')
            # print(f'current string = {self.current_string}')

            # Check if it was a correct key
            task_letter = self.sequence_text[self.current_string - 1]
            pressed_letter = chr(event.key())
            self.user_input += pressed_letter

            # Statistic
            # Words per minute
            if not self.start_wpm:
                # print(f'Start timing WPM')
                self.time = time.time()
                self.start_wpm = True

            # Key errors
            if task_letter != pressed_letter and not self.sequence_ended:
                self.errors += 1

            # Rhythm
            self.key_stamps.append(time.time())

            # Display errors in UI
            self.check_user_input(self.user_input)

            # Process all keys
            if self.current_string == self.string_length:
                if self.number_of_sequences == self.current_sequence + 1:
                    # End of lesson
                    # print('END SESSION')
                    # print('End timing WPM')
                    self.lesson_started = False
                    self.test_started = False
                    self.sequence_wpm()
                    self.record_statistics()
                    self.reset_ui()

                    return

                # End of Sequence
                pixmap = QtGui.QPixmap(self.keyboard_all)
                self.labPictures.setPixmap(pixmap)
                if self.sequence_ended:
                    # Last letter of sequence
                    self.sequence_ended = False
                    self.user_input = ''
                    self.current_string = 0
                    self.current_sequence += 1
                    self.start_sequence()
                    return

                self.sequence_ended = True
                # print('End timing WPM')
                self.sequence_wpm()
                return

            self.set_next_picture()

            # Update string counter
            self.current_string += 1

    # UI calls
    def start_lesson(self):

        self.lesson_name = self.comLessons.currentText()

        self.number_of_sequences = len(self.lessons_data[self.lesson_name]['sequences'])

        # Reset Flow
        self.user_input = ''
        self.current_sequence = 0
        self.current_string = 0
        self.lesson_started = True

        # Reset stat
        self.time = None
        self.wpm_lesson_time = 0
        self.wpm_lesson_characters = 0
        self.errors = 0
        del self.key_stamps[:]

        # Run sequence
        self.start_sequence()

        self.labPictures.setFocus()  # Allow application to catch SPACE key

    def start_test(self):

        self.test_name = self.comTests.currentText()
        self.number_of_sequences = len(self.tests_data[self.test_name]['sequences'])
        self.user_input = ''
        self.current_sequence = 0
        self.current_string = 0
        self.test_started = True
        self.start_sequence()

        self.labPictures.setFocus()  # Allow application to catch SPACE key

    def reload_stat(self):

        self.canvas.update_figure()
        self.recommendation()


if __name__ == "__main__":

    root = os.path.dirname(os.path.abspath(__file__))
    user = os.path.expanduser('~')
    app = QtWidgets.QApplication([])
    touch_type = TouchType()
    touch_type.setWindowIcon(QtGui.QIcon('{0}/icons/touch_type.ico'.format(root)))
    touch_type.show()
    app.exec_()
