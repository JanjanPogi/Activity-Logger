from pygubu.builder import Builder
from ALOG import con
from tkinter import messagebox, END, Toplevel
import datetime as dt
import pytz
import os
import pandas as pd
import sqlite3 as s3


class BaseApplication():
    def __init__(self, master, file, title):
        self.multi_marker = lambda x: ','.join(['?'] * x)
        self.__builder = Builder()
        self.__master = master
        self.__builder.add_from_file(file)
        self.__master.title(title)
        self.__master.resizable(False, False)
        self.__master.wm_attributes("-topmost", 1)
        self.__master.geometry("+{}+0".format(int(self.__master.winfo_screenwidth() / 2 + 200)))
        self.cursor = con.cursor()
        self.user_id = self.cursor.execute(f'SELECT UserID FROM tblUsers WHERE EmployeeDesktopName= ?',
                                           (os.getlogin(),)).fetchone()
        self.groups = self.cursor.execute(f'SELECT Sub_group FROM tblMain WHERE Users= ?', (self.user_id,)).fetchall()

    @property
    def master(self):
        return self.__master

    @property
    def builder(self):
        return self.__builder

    def get_builder_object(self, name):
        return self.__builder.get_object(name, self.__master)


class Application(BaseApplication):
    def __init__(self, master):
        super().__init__(master, r'ALOG\UIFramework\ALOG_UI.xml', 'ALOG Application')
        self.toplevel = self.master.winfo_toplevel()
        self.master.protocol('WM_DELETE_WINDOW', self.prevent_close)
        self.mainWindow = self.get_builder_object('frm_Main')
        self.cbxProcess = self.get_builder_object('cbxProcess')
        self.txtComments = self.get_builder_object('txtComments')
        self.menu = self.get_builder_object('main_menu')
        self.login_date = dt.datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Asia/Shanghai'))
        self.lblDate = self.get_builder_object('lblDateBucket')
        self.lblDate['text'] = '{} PH'.format(self.login_date.strftime('%b %d, %Y'))
        self.cbxProcess['height'] = 20
        self.ProcessContents = self.cursor.execute('SELECT Process FROM tblCoreProcess WHERE Groups_ID IN '
                                                   f'({self.multi_marker(len(self.groups))})', (self.groups)).fetchall()
        self.user_list = self.cursor.execute('SELECT EmployeeDesktopName FROM tblUsers').fetchall()
        self.cbxProcess['values'] = self.ProcessContents
        self.builder.connect_callbacks(self)
        self.current_process = 0
        self.groupValues = self.cursor.execute('SELECT Groups_ID FROM tblGroups').fetchall()
        self.groupList = self.cursor.execute('SELECT Group_Name FROM tblGroups').fetchall()
        if self.cursor.execute('SELECT Is_Admin FROM tblUsers WHERE UserID=?', (self.user_id,)).fetchone():
            self.toplevel.config(menu=self.menu)
        self.date_selected = [dt.datetime(self.login_date.year, self.login_date.month, self.login_date.day)]

    def calendar_select(self, event):
        active_day = event.widget.selection
        if len(self.date_selected) == 2:
            event.widget.unmark_day(self.date_selected[0].day)
            self.date_selected.pop(0)
        self.date_selected.append(active_day)
        event.widget.mark_day(active_day.day)

    def new_user(self):
        self.get_builder_object('frm_new_user').lift(self.mainWindow)
        self.builder.connect_callbacks(self)

    def cancel_new_user(self):
        self.get_builder_object('frm_new_user').lower(self.mainWindow)

    def save_new_user(self):
        entries = ['ent_first', 'ent_last', 'ent_desktop', 'ent_email']
        if self.get_builder_object(entries[2]).get() in self.user_list:
            messagebox.showwarning('Warning', 'DesktopName has already been mapped, please try again !')
        else:
            self.cursor.execute('INSERT INTO tblUsers (First_Name, Last_Name, EmployeeDesktopName, Email) VALUES (?,'
                                '?,?,?)', ([self.get_builder_object(i).get() for i in entries]))
            for i in entries:
                self.get_builder_object(i).delete(0, END)
            self.get_builder_object('frm_new_user').lower(self.mainWindow)

    def edit_user(self):
        self.get_builder_object('frm_edit_user').lift(self.mainWindow)
        objTree = self.get_builder_object('treeGroups')
        objUsers = self.get_builder_object('cbxUsers')
        objTree["columns"] = ("1", "2")
        objTree.column("1", width=100, anchor='c')
        objTree.column("2", width=100, anchor='c')
        objTree.heading("1", text="ID")
        objTree.heading("2", text="Group Name")
        for i, j in zip(self.groupList, self.groupValues):
            objTree.insert('', END, j, text=j, values=(j, i))
        objUsers['values'] = self.user_list
        self.builder.connect_callbacks(self)

    def select_users(self, event):
        objTree = self.get_builder_object('treeGroups')
        selected_groups = self.cursor.execute('SELECT Sub_Group FROM tblMain WHERE Users=(SELECT UserID FROM tblUsers '
                                              'WHERE EmployeeDesktopName=?)', (event.widget.get(),)).fetchall()
        if selected_groups:
            objTree.selection_set(tuple(selected_groups))
        else:
            objTree.selection_set()

    def cancel_edit(self):
        self.get_builder_object('frm_edit_user').lower(self.mainWindow)
        objTree = self.get_builder_object('treeGroups')
        objTree.delete(*objTree.get_children())

    def save_edit(self):
        objTree = self.get_builder_object('treeGroups')
        curUserId = self.cursor.execute('SELECT UserID FROM tblUsers WHERE EmployeeDesktopName=?',
                                        (self.get_builder_object('cbxUsers').get(),)).fetchone()
        curItem = objTree.selection()
        self.cursor.execute(
            f'DELETE FROM tblMain WHERE Users=? AND Sub_group NOT IN ({self.multi_marker(len(curItem))})',
            (curUserId, *curItem))
        for indx in curItem:
            self.cursor.execute('INSERT INTO tblMain (Users, Sub_group) SELECT ?, ? WHERE NOT EXISTS(SELECT 1 FROM '
                                'tblMain WHERE Users=? AND Sub_group=?)', (curUserId, indx, curUserId, indx))
        objTree.delete(*objTree.get_children())
        self.get_builder_object('cbxUsers').set('')
        self.get_builder_object('frm_edit_user').lower(self.mainWindow)
        self.groups = self.cursor.execute(f'SELECT Sub_group FROM tblMain WHERE Users= ?', (self.user_id,)).fetchall()
        self.cbxProcess['values'] = self.cursor.execute('SELECT Process FROM tblCoreProcess WHERE Groups_ID IN '
                                              f'({self.multi_marker(len(self.groups))})', (self.groups)).fetchall()

    def generate_excel(self):
        self.get_builder_object('frm_excel_report').lift(self.mainWindow)
        objCalendar = self.get_builder_object('calendarframe_1')
        objCalendar.clear_marks()
        self.builder.connect_callbacks(self)

    def desktop_excel(self):
        df = pd.read_sql('SELECT * FROM vwMain_Data WHERE ProcessTime_IN>=? AND ProcessTime_IN<=?', s3.connect(r'ALOG\DatabaseFramework\Alog Mappings.db', isolation_level=None),
                         params=(self.date_selected[0], self.date_selected[1]))
        df.to_csv("C:" + os.sep + os.environ["HOMEPATH"] + os.sep + "Desktop" + os.sep + f'{os.getlogin()}_{dt.datetime.strftime(dt.datetime.now(),"%Y%m%d" )}_logs.csv', index=False)
        self.get_builder_object('frm_excel_report').lower(self.mainWindow)

    def close_excel(self):
        self.get_builder_object('frm_excel_report').lower(self.mainWindow)

    def on_time_in(self):
        if not self.current_process == 0:
            self.cursor.execute('UPDATE tblHoursWorked SET ProcessTime_Out = ? WHERE ProcessTime_Out = ""',
                                (dt.datetime.now(),))
            self.cursor.execute(f'INSERT INTO tblHoursWorked (ProcessTime_In, ProcessTime_Out, ProcessID, UserID, '
                                f'Comments) VALUES({self.multi_marker(5)})', (dt.datetime.now(), '',
                                                                              self.current_process, self.user_id,
                                                                              self.txtComments.get('1.0', END)))
            self.reset_widgets()
        else:
            messagebox.showinfo('New Item', 'Please select a process first !')

    def on_unmap(self, event):
        self.master.withdraw()
        Timer(Toplevel(self.master), self.master)

    def reset_widgets(self):
        self.current_process = 0
        self.txtComments.delete('1.0', END)
        self.cbxProcess.set('')
        self.master.withdraw()

    def on_logout_clicked(self):
        self.update_last_entry()
        self.master.destroy()
        #  logout_email(dname=os.getlogin())

    def pop_subprocess(self, event):
        self.current_process = self.cursor.execute('SELECT ProcessID FROM tblCoreProcess WHERE Process=?',
                                                   (self.cbxProcess.get(),)).fetchone()

    @staticmethod
    def prevent_close():
        pass
        messagebox.showinfo('Exit', 'Please press logout button to close !')

    def update_last_entry(self):
        self.cursor.execute('UPDATE tblHoursWorked SET ProcessTime_Out = ? WHERE ProcessTime_Out = ""',
                            (dt.datetime.now(),))


class Timer(BaseApplication):
    dt_format = "%Y-%m-%d %H:%M:%S.%f"

    def __init__(self, master, master_instance):
        super().__init__(master, r'ALOG\UIFramework\Timer_UI.xml', 'Timer App')
        self.cursor = con.cursor()
        self.main_window = self.get_builder_object('frmTimer')
        self.master_instance = master_instance
        self.master.overrideredirect(True)
        self.builder.connect_callbacks(self)
        self.lblProcess = self.get_builder_object('lblProcess')
        self.lblTime = self.get_builder_object('lblTime')
        self.get_recent_entry = self.cursor.execute(
            'SELECT Log_ID FROM tblHoursWorked WHERE UserID = ? AND ProcessTime_Out = ""', (self.user_id,)).fetchone()
        self.last_process_name = self.cursor.execute(
            'SELECT Process FROM tblCoreProcess WHERE ProcessID= (SELECT ProcessID FROM tblHoursWorked WHERE Log_ID=?)',
            (self.get_recent_entry,)).fetchone()
        self.last_time_in = self.cursor.execute('SELECT ProcessTime_In FROM tblHoursWorked WHERE Log_ID=?',
                                                (self.get_recent_entry,)).fetchone()

        if self.get_recent_entry:
            self._log_time = dt.datetime.strptime(self.last_time_in, Timer.dt_format)
            self._min_time = dt.datetime.strptime(str(dt.datetime.now()), Timer.dt_format)
            self.show_time = (self._min_time - self._log_time).seconds
            self.lblTime['text'] = f'{str(self.show_time // 60)} minute(s)'
            self.lblProcess['text'] = self.last_process_name
        else:
            self.lblTime['text'] = 0
            self.lblProcess['text'] = 'No Process Logged'

    def show_window(self):
        self.master.destroy()
        self.master_instance.deiconify()
