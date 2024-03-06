import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import tkinter as tk
from tkinter import ttk

# Initialize measurement window
def init_meas_window() -> tuple[str, str, str, str, bool]:
    
    root = tk.Tk()
    root.title('Init meas window')
    root.geometry('200x300')
    def init():
        global QD_path, dr, ip, mode, vpn
        QD_path = QD_path_en.get()
        dr = DR_box.get()
        ip = ip_box.get()
        mode = mode_box.get()
        vpn = vpn_box.get()
        root.destroy()
    QD_path_la = tk.Label(root, text = 'QD path')
    QD_path_la.pack()
    QD_path_en = tk.Entry(root, width=30, justify='center')
    QD_path_en.pack()
    
    DR_la = tk.Label(root, text = 'DR location')   
    DR_la.pack()
    DR_box = ttk.Combobox(root,
                          width=15,
                          values=['DR1','DR2','DR3','DR4'])
    DR_box.pack()
    
    ip_la = tk.Label(root, text = 'IP location')   
    ip_la.pack()
    ip_box = ttk.Combobox(root,
                          width=15,
                          values=[170, 171])
    ip_box.pack()
    
    mode_la = tk.Label(root, text = 'mode')   
    mode_la.pack()
    mode_box = ttk.Combobox(root,
                          width=15,
                          values=['new','load'])
    mode_box.pack()
    
    vpn_la = tk.Label(root, text = 'mode')   
    vpn_la.pack()
    vpn_box = ttk.Combobox(root,
                          width=15,
                          values=['y','n'])
    vpn_box.pack()

    btn = tk.Button(root, text='Enter', command=init)   # 建立按鈕，點擊按鈕時，執行 show 函式
    btn.pack()
    root.mainloop()
    if dr == '' or ip == '' or mode == '' or vpn =='':
            raise KeyError('You have to insert the variables!')
    if vpn == 'y':
        vpnbool = True
    else:
        vpnbool = False
    
    return QD_path, dr, ip, mode, vpnbool

def chip_name_window() -> str:
    setfile = tk.Tk()
    setfile.title('Chip name window')
    setfile.geometry('200x200')
    def create_name():
        global chip_name
        chip_name = chip_name_en.get()
        setfile.destroy()
    chip_name_la = tk.Label(setfile, text = "chip name")
    chip_name_la.pack()
    chip_name_en = tk.Entry(setfile, width=20, justify='center')
    chip_name_en.pack()
    check_button = tk.Button(setfile, text="Enter", command=create_name)
    check_button.pack()
    setfile.mainloop()
    if chip_name == '':
        raise KeyError("Please set name")
    return chip_name

def Basic_information_window() -> tuple[str, int, int]:
    setfile = tk.Tk()
    setfile.title('Basic information window')
    setfile.geometry('200x200')
    def create_file():
        global chip_type, ro_out_att, xy_out_att
        chip_type = chip_type_en.get()
        ro_out_att = int(ro_out_att_en.get())
        xy_out_att = int(xy_out_att_en.get())
        if ro_out_att > 60 or xy_out_att > 60:
            raise ValueError("Attenuation is too high!")
        else:
            
            setfile.destroy()
    def validate(P):
        if str.isdigit(P) or P == "":
            return True
        else:
            return False
    vcmd = (setfile.register(validate), '%P')
    chip_type_la = tk.Label(setfile, text = "chip type")
    chip_type_la.pack()
    chip_type_en = tk.Entry(setfile, width=20, justify='center')
    chip_type_en.pack()
    ro_out_att_la = tk.Label(setfile, text = "RO output attenuation")
    ro_out_att_la.pack()
    ro_out_att_en = tk.Entry(setfile, width=20, justify='center', validate='key', validatecommand=vcmd)
    ro_out_att_en.pack()
    xy_out_att_la = tk.Label(setfile, text = "XY output attenuation")
    xy_out_att_la.pack()
    xy_out_att_en = tk.Entry(setfile, width=20, justify='center', validate='key', validatecommand=vcmd)
    xy_out_att_en.pack()
    check_button = tk.Button(setfile, text="Enter", command=create_file)
    check_button.pack()
    setfile.mainloop()
    if chip_type == '' or ro_out_att == '' or xy_out_att == '':
        raise KeyError('You have to insert the variables!')
    return chip_type, ro_out_att, xy_out_att