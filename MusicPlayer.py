from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QListWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6 import uic
from mutagen.id3 import ID3, APIC
from mutagen.flac import FLAC
import sounddevice as sd
import soundfile as sf
import sys
import os

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("style.ui", self)

        self.OpenFile.triggered.connect(self.selectFile)
        self.Open_Folder_obj.triggered.connect(self.openFolder)
        self.play.clicked.connect(self.toggle)
        self.playlist.itemDoubleClicked.connect(self.onItemSelected)
        self.Slider.sliderReleased.connect(self.sliderMoved)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateSlider)

        self.file_paths = []
        self.handling_done = False
        self.file_path = None
        self.isplaying = False
        self.isStream = False
        self.fileFinished = False
        self.currentIndex = None
        self.singleFile = False
        self.seeking = False

    def selectFile(self):
        self.file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Audio Files (*.mp3 *.flac *.wav *.ogg *.aiff)"
        )
        if self.file_path:
            self.singleFile = True
            self.loadFile()


    def openFolder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder_path:
            files = [f for f in os.listdir(folder_path) if f.endswith(('.mp3', '.flac', '.wav', '.ogg', '.aiff'))]
            self.file_paths = [os.path.join(folder_path, f) for f in files]
            self.playlist.clear()
            for f in files:
                self.playlist.addItem(f)

    def onItemSelected(self):
        self.singleFile = False
        self.currentIndex = self.playlist.currentRow()
        self.file_path = self.file_paths[self.currentIndex]
        self.loadFile()

    def extractCoverArt(self, file_path):
        try:
            if file_path.endswith('.flac'):
                audio = FLAC(file_path)
                if audio.pictures:
                    img_data = audio.pictures[0].data
                else:
                    return None
            elif file_path.endswith('.mp3'):
                audio = ID3(file_path)
                for tag in audio.values():
                    if isinstance(tag, APIC):
                        img_data = tag.data
                        break
                else:
                    return None
            else:
                return None
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            return pixmap
        except Exception as e:
            print("Cover art error:", e)
            return None

    def loadFile(self):
        self.handling_done = False
        if self.isStream:
            self.stream.stop()
            self.stream.close()
            self.timer.stop()  
            self.Slider.setValue(0)
            self.isplaying = False
            self.isStream = False
            self.fileFinished = False
            self.play.setText("▶")

        if self.file_path:
            self.title.setText(os.path.basename(self.file_path))

            self.audio_file = sf.SoundFile(self.file_path)
            self.Slider.setMinimum(0)
            self.Slider.setMaximum(self.audio_file.frames) 
            self.Bitrate.setText(self.audio_file.subtype)
            self.SampleRate.setText(f"{str(self.audio_file.samplerate)}khz")

            get_cover_image = self.extractCoverArt(self.file_path)
            if get_cover_image:
                pixmap = get_cover_image.scaled(
                    self.label_art.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.label_art.setPixmap(pixmap)

                self.playFile()

    def audio_callback(self, outdata, frames, status, time):
        try:
            buffer = self.audio_file.read(frames, dtype='float32')
            if len(buffer) < frames:
                outdata[:len(buffer)] = buffer
                outdata[len(buffer):] = 0.0
                raise sd.CallbackStop()
            else:
                outdata[:] = buffer
        except sd.CallbackStop:
            pass
        except Exception as e:
            print("Playback error:", e)
        finally:
            if self.audio_file.tell() >= self.audio_file.frames and not self.handling_done:
                self.handling_done = True
                QTimer.singleShot(100, self.playbackDone)

    def playFile(self):
        self.stream = sd.OutputStream(
            samplerate=self.audio_file.samplerate,
            blocksize=4096,
            device=0, #change this to desired audio output device
            channels=self.audio_file.channels,
            dtype='float32',
            latency='high',
            extra_settings=None,
            callback=self.audio_callback,
        )
        self.stream.start()
        self.timer.start(1000)
        self.play.setText("||")
        self.isStream = True
        self.isplaying = True
        self.fileFinished = False

    def sliderMoved(self):
        if self.isStream:
            self.stream.stop()
            self.audio_file.seek(self.Slider.value())
            if self.isplaying:
                self.stream.start()

    def updateSlider(self):
        if not self.seeking:
            current_pos = self.audio_file.tell()
            self.Slider.setValue(current_pos)

    def toggle(self):
        if not self.isStream and not self.fileFinished:
            self.playFile()
            self.play.setText("||")
        elif self.fileFinished and not self.isStream:
            self.audio_file.seek(0)
            self.playFile()
        elif self.isplaying:
            self.stream.stop()
            self.isplaying = False
            self.play.setText("▶")
        else:
            self.stream.start()
            self.isplaying = True
            self.play.setText("||")

    def playbackDone(self):
        if self.handling_done:
            return
        self.handling_done = True
        
        if self.isStream:
            self.stream.stop()
            self.stream.close() 
            
        self.fileFinished = True
        self.timer.stop()
        self.isplaying = False
        self.isStream = False
        self.play.setText("▶")
        self.Slider.setValue(0)
        if not self.singleFile:
            self.currentIndex += 1
            if self.currentIndex < len(self.file_paths):
                self.file_path = self.file_paths[self.currentIndex]
                self.loadFile()

print(sd.query_devices())

app = QApplication(sys.argv)
window = MyWindow()
window.show()
sys.exit(app.exec())
