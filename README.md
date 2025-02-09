# **CAN Format Converter**  

🚗 **CAN Format Converter** は、**CAN データのフォーマット変換** および **DBC を用いたデコード** をサポートする Python アプリケーションです。  
`.asc`、`.blf`、`.mf4` などの **CANログフォーマットの相互変換** や、**CSV/MAT 形式へのエクスポート** に対応しています。  

---

## **📌 主な機能**
- ✅ **複数の DBC ファイルを統合** (`load_and_merge_dbc`)  
- ✅ **CANログフォーマットの相互変換** (`.asc` ⇄ `.blf` ⇄ `.mf4`)  
- ✅ **DBC を使用した CAN メッセージのデコード** (`convert_blf_to_csv`)  
- ✅ **大容量データの分割出力** (`chunk_size` 設定可能)  

---

## **📥 インストール**
### **🔧 必要なライブラリ**
本アプリを使用するには、以下の Python ライブラリが必要です。  

```bash
pip install python-can cantools pandas asammdf
```

---


## **🚀 実行方法**
GUIツールをコンソール上で実行ください。もしくは`CANFormatConverter`をAPIのように利用いただくことも可能です。
```bash
python ./src/ConverterGUI.py
```

---


## **🚀 使い方**
### **1️⃣ DBC ファイルを読み込む**
DBCファイルをドラッグアンドドロップ or `select DBC`からファイルを読み込む
### **2️⃣ BLF 形式の CANログを 選択**
CANログファイルをドラッグアンドドロップ or `select Files`からファイルを読み込む
### **3️⃣ 変換フォーマットを選択**
CANログファイルをドラッグアンドドロップ or `select Files`からファイルを読み込む
### **4⃣ フォーマット変換**
`Convert`をボタンを押して変換を実行

---

## **📩 お問い合わせ**
バグ報告や機能追加のリクエストは、GitHub の Issues に投稿してください！
