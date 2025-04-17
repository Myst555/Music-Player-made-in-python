import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import soundfile as sf
import sounddevice as sd
from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC
from PIL import Image, ImageTk
import io
import os

audioFile = None
stream = None
playlist_files = []

AUDIO_EXTENSIONS = ('.flac', '.wav', '.mp3', '.ogg', '.m4a')

def callback(outdata, frames, time, status):
    raw_bytes = audioFile.buffer_read(frames, dtype='int32')
    bytes_to_write = min(len(outdata), len(raw_bytes))
    outdata[:bytes_to_write] = raw_bytes[:bytes_to_write]

    if bytes_to_write < len(outdata):
        outdata[bytes_to_write:] = b'\x00' * (len(outdata) - bytes_to_write)
        raise sd.CallbackStop()

def extract_cover_art(file_path):
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

        image = Image.open(io.BytesIO(img_data))
        image = image.resize((500, 500))
        return ImageTk.PhotoImage(image)
    except Exception as e:
        print("Cover art error:", e)
    return None

def play_file(file_path):
    global audioFile, stream
    if stream:
        stream.stop()
        stream.close()

    fileLabel.config(text=file_path)
    audioFile = sf.SoundFile(file_path)
    sample.config(text=audioFile.samplerate)
    bitdepth.config(text=audioFile.subtype)

    photo = extract_cover_art(file_path)
    if photo:
        image_label.config(image=photo, text='')
        image_label.image = photo
    else:
        image_label.config(image='', text='No cover found')

    stream = sd.RawOutputStream(
        samplerate=audioFile.samplerate,
        blocksize=0,
        device=8,
        channels=2,
        dtype='int32',
        callback=callback
    )
    stream.start()
    stop.config(command=stream.stop)

def select_file():
    selected_file = filedialog.askopenfilename(title='Select File')
    if selected_file:
        play_file(selected_file)

def select_folder():
    global playlist_files
    folder = filedialog.askdirectory(title="Select Folder")
    if folder:
        playlist.delete(0, tk.END)
        playlist_files = []
        for file in os.listdir(folder):
            if file.lower().endswith(AUDIO_EXTENSIONS):
                full_path = os.path.join(folder, file)
                playlist.insert(tk.END, file)
                playlist_files.append(full_path)

def on_playlist_select(event):
    selection = playlist.curselection()
    if selection:
        index = selection[0]
        play_file(playlist_files[index])

root = tk.Tk()
root.title('Music Player')

image_label = tk.Label(root, text='No cover')
image_label.grid(column=0, row=0, columnspan=3, pady=10)

fileLabel = ttk.Label(root, text='N/a')
fileLabel.grid(column=0, row=1)

sample = ttk.Label(root, text='N/a')
sample.grid(column=0, row=2)

bitdepth = ttk.Label(root, text='N/a')
bitdepth.grid(column=1, row=2)

folder_btn = ttk.Button(root, text='Select Folder', command=select_folder)
folder_btn.grid(column=0, row=3)

stop = ttk.Button(root, text='Stop', command='')
stop.grid(column=1, row=3)

playlist = tk.Listbox(root, width=60)
playlist.grid(column=0, row=5, columnspan=3, pady=10)
playlist.bind("<<ListboxSelect>>", on_playlist_select)

root.mainloop()