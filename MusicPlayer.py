import tkinter as tk
from tkinter import filedialog, ttk
import soundfile as sf
import sounddevice as sd
from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC
from PIL import Image, ImageTk
import io
import os

# Shows Device Outputs
print(sd.query_devices())

# Globals
audio_file = None
audio_stream = None
playlist_files = []

AUDIO_EXTENSIONS = ('.flac', '.wav', '.mp3', '.ogg', '.m4a')

# ========== Audio Playback ==========
def audio_callback(outdata, frames, time, status):
    try:
        raw_bytes = audio_file.buffer_read(frames, dtype='int32')
        outdata[:len(raw_bytes)] = raw_bytes
        if len(raw_bytes) < len(outdata):
            outdata[len(raw_bytes):] = b'\x00' * (len(outdata) - len(raw_bytes))
            raise sd.CallbackStop()
    except Exception as e:
        print("Playback error:", e)

def play_audio(file_path):
    global audio_file, audio_stream

    stop_audio()

    try:
        audio_file = sf.SoundFile(file_path)
    except Exception as e:
        file_label.config(text=f"Error: {e}")
        return

    file_label.config(text=os.path.basename(file_path))
    sample_label.config(text=f"Sample Rate: {audio_file.samplerate} Hz")
    bitdepth_label.config(text=f"Bit Depth: {audio_file.subtype}")

    cover_image = extract_cover_art(file_path)
    if cover_image:
        cover_label.config(image=cover_image, text='')
        cover_label.image = cover_image
    else:
        cover_label.config(image='', text='No cover art found')

    try:
        audio_stream = sd.RawOutputStream(
            samplerate=audio_file.samplerate,
            blocksize=0,
            device=0,       #change to desired device output   
            channels=2,
            dtype='int32',
            callback=audio_callback
        )
        audio_stream.start()
    except Exception as e:
        print("Stream error:", e)
        file_label.config(text=f"Audio error: {e}")

def stop_audio():
    global audio_stream
    if audio_stream:
        try:
            audio_stream.stop()
            audio_stream.close()
        except Exception as e:
            print("Error stopping stream:", e)
        audio_stream = None

# ========== Cover Art Extraction ==========
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

        image = Image.open(io.BytesIO(img_data)).resize((500, 500), Image.LANCZOS)
        return ImageTk.PhotoImage(image)
    except Exception as e:
        print("Cover art error:", e)
        return None

# ========== File/Folder Selection ==========
def select_single_file():
    file_path = filedialog.askopenfilename(filetypes=[("Audio Files", AUDIO_EXTENSIONS)])
    if file_path:
        play_audio(file_path)

def select_folder():
    global playlist_files
    folder_path = filedialog.askdirectory()
    if folder_path:
        playlist.delete(0, tk.END)
        playlist_files.clear()

        for file in sorted(os.listdir(folder_path)):
            if file.lower().endswith(AUDIO_EXTENSIONS):
                full_path = os.path.join(folder_path, file)
                playlist.insert(tk.END, file)
                playlist_files.append(full_path)

def on_playlist_select(event):
    selection = playlist.curselection()
    if selection:
        index = selection[0]
        play_audio(playlist_files[index])

# ========== GUI Setup ==========
root = tk.Tk()
root.title("Tkinter Music Player")

cover_label = tk.Label(root, text="No cover art")
cover_label.grid(row=0, column=0, columnspan=3, pady=10)

file_label = ttk.Label(root, text="No file selected")
file_label.grid(row=1, column=0, columnspan=3)

sample_label = ttk.Label(root, text="Sample Rate: N/A")
sample_label.grid(row=2, column=0)

bitdepth_label = ttk.Label(root, text="Bit Depth: N/A")
bitdepth_label.grid(row=2, column=1)

ttk.Button(root, text="Open File", command=select_single_file).grid(row=3, column=0)
ttk.Button(root, text="Select Folder", command=select_folder).grid(row=3, column=1)
ttk.Button(root, text="Stop", command=stop_audio).grid(row=3, column=2)

playlist = tk.Listbox(root, width=60)
playlist.grid(row=4, column=0, columnspan=3, pady=10)
playlist.bind("<<ListboxSelect>>", on_playlist_select)

root.mainloop()
