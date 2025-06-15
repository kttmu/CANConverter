import can
import pandas as pd
import numpy as np
import cantools
from glob import glob
import os
import scipy
from asammdf import MDF
from tqdm import tqdm

class CANFormatConverter:
    def __init__(self, crop_mode=False, excel_path=None):
        self.database = None
        self.temp_data_set = {}
        self.update_counter = 0
        self.crop_mode = crop_mode
        self.crop_target_excel_path = excel_path
        self.crop_ids = []
    
    def load_and_merge_dbc(self, dbc_files):
        try:
            # cantools を使用して複数のDBCファイルを結合
            database = cantools.database.Database()
            for dbc_file in dbc_files:
                database.add_dbc_file(dbc_file)
            self.database = database
        except Exception as e:
            print(f"Error loading DBC files: {e}")
    
    def load_crop_id_list(self):
        #try:
        if 1:
            df = pd.read_excel(self.crop_target_excel_path)
            for val in df['ID']:
                if isinstance(val, str) and val.startswith("0x"):
                    self.crop_ids.append(int(val, 16))
                elif isinstance(val, int):
                    self.crop_ids.append(val)
            self.crop_mode = True
            return
        #except Exception as e:
        else:
            print(f"IDリストの読み込みに失敗しました: {e}")
            self.crop_mode = False
            return
    
    def is_target_id(self, msg):
        """
        メッセージのIDがクロップ対象のIDリストに含まれているかを確認
        """
        if self.crop_mode:
            return msg.arbitration_id in self.crop_ids
        else:
            return True


    # blf -> csv    
    def convert_blf_to_csv(self, input_pth, output_pth):
        
        """
        BLFファイルをcsvに変換
        ライブラリの都合上、CAN→csvの変換はBLFに一時的に変換しておく必要があります。
        """

        # dbcが読み込まれていなければエラーを返す
        if self.database == None:
            print(fr"Databaseが読み込まれていません")
            return
        # blfファイルの読み込み()
        blfdata=can.io.blf.BLFReader(input_pth)

        # Crop IDリストを読み込む
        self.load_crop_id_list()
        
        # 保存用のデータベースの初期化
        self.initialize_decoded_signal_list()

        for msg in tqdm(blfdata):
            try:
                # クロップ対象のIDかどうかを確認
                if self.is_target_id(msg):
                    # decode
                    decoded_signals = self.database.get_message_by_frame_id(msg.arbitration_id).decode(msg.data, decode_choices=False)
                    timestamp = msg.timestamp

                    # update database
                    self.update_decoded_signal_list(timestamp, decoded_signals)

            except Exception as e:
                print(fr"Cannot find id :{e}")
        
        #　デコード結果をcsvとして出力
        self.save_decoded_signal_list(output_pth)

    
    def initialize_decoded_signal_list(self):
        self.temp_data_set = {"time":[]}
        self.update_counter = 0

    def update_decoded_signal_list(self, time, dec_sigs):

        self.update_counter += 1 

        # すべての信号を前回値埋めしておく
        if self.update_counter > 2:
            for sig in self.temp_data_set:
                old_sig = self.temp_data_set[sig]
                self.temp_data_set[sig].append(old_sig[-1])

            # 時間要素の更新 
            self.temp_data_set["time"][-1] = time
        else:
            # 時間要素の更新 
            self.temp_data_set["time"].append(time)

        data_length = len(self.temp_data_set["time"])

        # 入力信号要素を更新、なければ新規で要素を作っておく 
        for sig in dec_sigs:
           
            # 信号が過去に受信されていた場合
            if sig in self.temp_data_set:
                self.temp_data_set[sig][-1] = dec_sigs[sig]
            
            # 信号が過去に受信されていなかった場合
            else:
                self.temp_data_set[sig] = [0 for i in range(data_length)]
                self.temp_data_set[sig][-1] = dec_sigs[sig]


    def save_decoded_signal_list(self, output_pth, chunk_size=100000, sampling_rate=10):
        """
        デコードした CAN データを CSV に保存（大容量データの場合は分割）
        
        Args:
            output_pth (str): 出力 CSV のパス
            chunk_size (int): 1 ファイルあたりの最大行数
        """
        # すべての信号の最大データ長を取得
        max_length = max(len(values) for values in self.temp_data_set.values())
    
        # 各リストを `max_length` に合わせて補完
        for key in self.temp_data_set:
            while len(self.temp_data_set[key]) < max_length:
                self.temp_data_set[key].append(None)  # 長さが足りない場合は `None` で埋める
    
        # DataFrame に変換
        df = pd.DataFrame(self.temp_data_set)
        df = df[["time"] + sorted(self.temp_data_set.keys())]  # カラム順を統一

        # DataFrameをダウンサンプリング
        time_length = float(np.max(df.time) - np.min(df.time))
        after_data_length = int(time_length * sampling_rate)
        down_sampling_rate = int(len(df) // after_data_length)
        if down_sampling_rate > 0:
            df = df[::down_sampling_rate]
    
        # データを `chunk_size` ごとに分割して保存
        total_rows = len(df)
        num_parts = (total_rows // chunk_size) + (1 if total_rows % chunk_size else 0)
    
        base_name, ext = os.path.splitext(output_pth)
    
        for i in range(num_parts):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, total_rows)
            df_chunk = df.iloc[start_idx:end_idx]
    
            # ファイル名に `_part1`, `_part2`, ... を追加
            chunk_file = f"{base_name}_part{i+1}{ext}"

            # 拡張子がcsvの場合
            if ext == ".csv":
                df_chunk.to_csv(chunk_file, index=False)
            # 拡張子がMATの場合
            elif ext == ".mat":
                mat_data = {col: df[col].values for col in df.columns}
                scipy.io.savemat(chunk_file, mat_data)
            else:
                print("Error:inputed file ext is Wrong! Only 'csv' or 'mat' is acceptable")

        print(f"Saved: {chunk_file} ({len(df_chunk)} rows)")

    # mf4 -> csv
    def convert_mf4_to_csv(self, input_pth, output_pth, down_sampling_rate=10):

        # Load the MF4 file
        mdf = MDF(input_pth)

        # Convert the MDF object to a pandas DataFrame
        df = mdf.to_dataframe()

        # Chunk data(※この値は適当なのでもし変えたい場合はIFを変更のこと)
        df = df.loc[::down_sampling_rate]
        
        # 拡張子を判別して出力方法を変更
        _, ext = os.path.splitext(output_pth)

        if ext == ".csv":
            df.to_csv(output_pth)
        elif ext == ".mat":
            mat_data = {col: df[col].values for col in df.columns}
            scipy.io.savemat(output_pth, mat_data)
        else:
            print("Error:inputed file ext is Wrong! Only 'csv' or 'mat' is acceptable")
        
        print(f"Saved: {output_pth}")

    # asc -> blf
    def convert_asc_to_blf(self, input_pth, output_pth):
        try:
            with open(input_pth, 'r') as f_in:
                log_in = can.io.ASCReader(f_in)
        
                with open(output_pth, 'wb') as f_out:
                    log_out = can.io.BLFWriter(f_out)
                    for msg in log_in:
                        log_out.on_message_received(msg)
                    log_out.stop()
        except Exception as e:
            print(fr"Fail to convert : code={e}")
    
    # asc -> bf4 
    def convert_asc_to_mf4(self, input_pth, output_pth):
        try:
            with open(input_pth, 'r') as f_in:
                log_in = can.io.ASCReader(f_in)
        
                with open(output_pth, 'wb') as f_out:
                    log_out = can.io.MF4Writer(f_out)
                    for msg in log_in:
                        log_out.on_message_received(msg)
                    log_out.stop()
        except Exception as e:
            print(fr"Fail to convert : code={e}")

    # blf -> asc
    def convert_blf_to_asc(self, input_pth, output_pth):
        try:
            with open(input_pth, 'rb') as f_in:
                log_in = can.io.BLFReader(f_in)
        
                with open(output_pth, 'w') as f_out:
                    log_out = can.io.ASCWriter(f_out)
                    for msg in log_in:
                        log_out.on_message_received(msg)
                    log_out.stop()
        except Exception as e:
            print(fr"Fail to convert : code={e}")
    
    # blf -> mf4
    def convert_blf_to_mf4(self, input_pth, output_pth):
        try:
            with open(input_pth, 'rb') as f_in:
                log_in = can.io.BLFReader(f_in)
        
                with open(output_pth, 'wb') as f_out:
                    log_out = can.io.MF4Writer(f_out)
                    for msg in log_in:
                        log_out.on_message_received(msg)
                    log_out.stop()
        except Exception as e:
            print(fr"Fail to convert : code={e}")

    # mf4 -> blf
    def convert_mf4_to_blf(self, input_pth, output_pth):
        try:
            with open(input_pth, 'rb') as f_in:
                log_in = can.io.MF4Reader(f_in)
        
                with open(output_pth, 'wb') as f_out:
                    log_out = can.io.BLFWriter(f_out)
                    for msg in log_in:
                        log_out.on_message_received(msg)
                    log_out.stop()
        except Exception as e:
            print(fr"Fail to convert : code={e}")
    
    # mf4 -> asc 
    def convert_mf4_to_asc(self, input_pth, output_pth):
        try:
            with open(input_pth, 'rb') as f_in:
                log_in = can.io.MF4Reader(f_in)
        
                with open(output_pth, 'wb') as f_out:
                    log_out = can.io.ASCWriter(f_out)
                    for msg in log_in:
                        log_out.on_message_received(msg)
                    log_out.stop()
        except Exception as e:
            print(fr"Fail to convert : code={e}")
    
    # 入出力ファイルのファイル形式を判別してコンバータを選択する
    def convert(self, input_pth, output_pth):
        # Get input type
        input_format = input_pth.split(".")[-1]
        # Get output type
        output_format = output_pth.split(".")[-1]
        
        # Convert to other can format
        if ( (input_format in ["asc"]) and (output_format in ["blf", "BLF"]) ):
            self.convert_asc_to_blf(input_pth, output_pth)
        elif ( (input_format in ["asc"]) and (output_format in ["mf4", "MF4"]) ):
            self.convert_asc_to_mf4(input_pth, output_pth)
        elif ( (input_format in ["blf", "BLF"]) and (output_format in ["mf4", "MF4"]) ):
            self.convert_blf_to_mf4(input_pth, output_pth)
        elif ( (input_format in ["blf", "BLF"]) and (output_format in ["asc"]) ):
            self.convert_blf_to_asc(input_pth, output_pth)
        elif ( (input_format in ["MF4", "mf4"]) and (output_format in ["blf", "BLF"]) ):
            self.convert_mf4_to_blf(input_pth, output_pth)
        elif ( (input_format in ["MF4", "mf4"]) and (output_format in ["asc"]) ):
            self.convert_mf4_to_asc(input_pth, output_pth)
        
        # Decode & Convert to csv
        elif ( (input_format in ["MF4", "mf4"]) and (output_format in ["csv","mat"]) ):
            self.convert_mf4_to_csv(input_pth, output_pth)
            os.remove("./tmp.blf")
        elif ( (input_format in ["asc"]) and (output_format in ["csv","mat"]) ):
            self.convert_asc_to_blf(input_pth, "./tmp.blf")
            self.convert_blf_to_csv("./tmp.blf", output_pth)
            os.remove("./tmp.blf")
        elif ( (input_format in ["blf", "BLF"]) and (output_format in ["csv","mat"]) ):
            self.convert_blf_to_csv(input_pth, output_pth)
        else:
            print("Could not get format of input or output path")

if __name__ == "__main__":
    
    dbc_pth = glob(fr"/path/to/dbc")
    input_pth = "./output_sample.blf"

    can_converter = CANFormatConverter()

    #dbcを設定
    can_converter.load_and_merge_dbc(dbc_pth)

    # ひとまず、blfに変換する
    #can_converter.convert(input_pth, "./temp.blf")

    # デコードしてcsvにダンプする
    can_converter.convert(input_pth, "./sample_output.csv")
