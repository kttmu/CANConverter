import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import cantools
import os
import asammdf
import csv
import pandas as pd
from CANFormatConveter import CANFormatConverter
import threading


def on_drop_db(event):
    files = root.tk.splitlist(event.data)
    for file in files:
        if file.lower().endswith('.dbc'):
            dbc_listbox.insert(tk.END, file)
        else:
            messagebox.showwarning("Warning", f"'{os.path.basename(file)}' is not a DBC file.")

def on_drop_input(event):
    files = root.tk.splitlist(event.data)
    for file in files:
        if file.lower().endswith(('.asc', '.blf', '.BLF', '.mf4', '.mat')):
            input_listbox.insert(tk.END, file)
        else:
            messagebox.showwarning("Warning", f"'{os.path.basename(file)}' is not a supported input file.")

def on_drop_target_id(event):
    files = root.tk.splitlist(event.data)
    for file in files:
        if file.lower().endswith(('.xlsx')):
            target_id_listbox.insert(tk.END, file)
        else:
            messagebox.showwarning("Warning", f"'{os.path.basename(file)}' is not a supported input file.")

def select_db_files():
    files = filedialog.askopenfilenames(filetypes=[("DBC files", "*.dbc")], title="Select DBC Files")
    for file in files:
        dbc_listbox.insert(tk.END, file)

def select_input_files():
    files = filedialog.askopenfilenames(filetypes=[("CAN logs", "*.asc;*.blf;*.BLF;*.mf4;*.mat")], title="Select Input Files")
    for file in files:
        input_listbox.insert(tk.END, file)

def clear_list(listbox):
    listbox.delete(0, tk.END)

def load_and_merge_dbc(dbc_files):
    try:
        database = cantools.database.Database()
        for dbc_file in dbc_files:
            database.add_dbc_file(dbc_file)
        return database
    except Exception as e:
        print(f"Error loading DBC files: {e}")
        return None

def convert_to_other_format():
    
    # リストボックス内の情報を取得
    dbc_files = list(dbc_listbox.get(0, tk.END))
    input_files = list(input_listbox.get(0, tk.END))
    target_id_files = list(target_id_listbox.get(0, tk.END))
    save_dir = filedialog.askdirectory(title="Select Output Directory")

    # 入力データがない、もしくは入力データがCANでDBCが含まれない場合はメッセージを表示して初期状態に戻す
    _, ext = os.path.splitext(input_files[0])
    if (ext in [".asc", ".blf", ".BLF"]):
        if dbc_listbox.size() == 0 or input_listbox.size() == 0:
            messagebox.showwarning("Warning", "Please select DBC and input files before converting.")
            return
        else: 
            pass

    # 何らかのトラブルで保存先フォルダが取得できていない場合は強制終了
    if not save_dir:
        return
    
    # プログレスバーを表示
    progress_window = tk.Toplevel(root)
    progress_window.title("Conversion Progress")
    progress_window.geometry("400x100")
    
    progress_label = tk.Label(progress_window, text="Converting files...")
    progress_label.pack(pady=10)
    
    progress_bar = ttk.Progressbar(progress_window, orient="horizontal", length=300, mode="indeterminate")
    progress_bar.pack(pady=10)
    progress_bar.start()
    
    # 別スレッドで変換処理を実行
    def convert_files_thread():

        total_files = len(input_files)
        processed_files = 0
        selected_format = output_format_combobox.get().lower()

        # 入力ファイルを取得順に変換していく
        for file in input_files:
            if len(target_id_files)>0:
                converter = CANFormatConverter(excel_path=target_id_files[0])
            else:
                converter = CANFormatConverter()
            
            # DBCファイルを読み込む
            converter.load_and_merge_dbc(dbc_files)

            output_file = os.path.join(save_dir, os.path.basename(file) + f".{selected_format}")
            converter.convert(file, output_file)
            
            processed_files += 1
            progress_bar['value'] = (processed_files / total_files) * 100
            progress_window.update()

        # 変換が完了したのでプログレスバーを消しておく
        progress_bar.stop()
        progress_window.destroy()
        messagebox.showinfo("Success", "Conversion completed successfully!")
    
    # スレッド開始
    threading.Thread(target=convert_files_thread, daemon=True).start()
    

# GUI Setup
root = TkinterDnD.Tk()
root.title("CAN Data Converter")
root.geometry("600x550")

frame = tk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Database Listbox
db_frame = tk.LabelFrame(frame, text="DBC Files", padx=5, pady=5)
db_frame.pack(fill=tk.BOTH, expand=True)
dbc_listbox = tk.Listbox(db_frame, selectmode=tk.MULTIPLE, height=4)
dbc_listbox.pack(fill=tk.BOTH, expand=True)
dbc_listbox.drop_target_register(DND_FILES)
dbc_listbox.dnd_bind("<<Drop>>", on_drop_db)

# Input File Listbox
input_frame = tk.LabelFrame(frame, text="Input Files", padx=5, pady=5)
input_frame.pack(fill=tk.BOTH, expand=True)
input_listbox = tk.Listbox(input_frame, selectmode=tk.MULTIPLE, height=4)
input_listbox.pack(fill=tk.BOTH, expand=True)
input_listbox.drop_target_register(DND_FILES)
input_listbox.dnd_bind("<<Drop>>", on_drop_input)

# Input convertion target id list
target_id_frame = tk.LabelFrame(frame, text="Convertion target", padx=1, pady=1)
target_id_frame.pack(fill=tk.BOTH, expand=True)
target_id_listbox = tk.Listbox(target_id_frame, selectmode=tk.MULTIPLE, height=2)
target_id_listbox.pack(fill=tk.BOTH, expand=True)
target_id_listbox.drop_target_register(DND_FILES)
target_id_listbox.dnd_bind("<<Drop>>", on_drop_target_id)

# Output Format Selection
format_frame = tk.LabelFrame(frame, text="Output Format", padx=5, pady=5)
format_frame.pack(fill=tk.X, expand=True)
output_format_combobox = ttk.Combobox(format_frame, values=["csv", "blf", "mf4", "asc", "mat"], state="readonly")
output_format_combobox.pack(fill=tk.X, padx=5, pady=5)
output_format_combobox.current(0)

# Buttons
button_frame = tk.Frame(frame)
button_frame.pack(fill=tk.X, pady=10)

db_button = tk.Button(button_frame, text="Select DBC", command=select_db_files)
db_button.pack(side=tk.LEFT, padx=5, pady=5)

input_button = tk.Button(button_frame, text="Select Input Files", command=select_input_files)
input_button.pack(side=tk.LEFT, padx=5, pady=5)

convert_button = tk.Button(button_frame, text="Convert", command=convert_to_other_format)
convert_button.pack(side=tk.LEFT, padx=5, pady=5)

clear_db_button = tk.Button(button_frame, text="Clear DBC", command=lambda: clear_list(dbc_listbox))
clear_db_button.pack(side=tk.LEFT, padx=5, pady=5)

clear_input_button = tk.Button(button_frame, text="Clear Input", command=lambda: clear_list(input_listbox))
clear_input_button.pack(side=tk.LEFT, padx=5, pady=5)

quit_button = tk.Button(button_frame, text="Quit", command=root.quit)
quit_button.pack(side=tk.RIGHT, padx=5, pady=5)

# GUI内に追加
crop_mode_var = tk.BooleanVar()
crop_check = tk.Checkbutton(root, text="クロップモード（指定IDのみ）", variable=crop_mode_var)
#crop_check.grid(row=5, column=0, sticky="w")

root.mainloop()