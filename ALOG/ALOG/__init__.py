import tkinter as tk
import sqlite3 as s3

con = s3.connect(r'ALOG\DatabaseFramework\Alog Mappings.db', isolation_level=None)
con.row_factory = lambda cursor, row: row[0]

from ALOG.UIFramework.ui import Application

root = tk.Tk()
app = Application(root)
