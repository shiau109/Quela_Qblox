"""
    Path_book keeps the path indecated to the directories, and the object will be saved in the folder named by date.
"""
import os, datetime, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from qblox_drive_AS.support.UserFriend import eyeson_print

root = os.getcwd()
# The directory for measurement raw data
meas_raw_dir = os.path.join(root,'qblox_drive_AS/Meas_raw')
# The directory for qauntum device
qdevice_backup_dir = os.path.join(root,'qblox_drive_AS/QD_backup')


def decode_datetime_2_foldername(date:datetime):
    latest = date.strftime("%Y%m%d")
    y = latest[:4]
    m = latest[4:6]
    d = latest[6:8]
    folder_name =  y+m+d
    return folder_name

def find_latest_QD_pkl_for_dr(which_dr:str,ip_label:str=''):
    folders = [name for name in os.listdir(qdevice_backup_dir) if os.path.isdir(os.path.join(qdevice_backup_dir,name))]
    date = []
    for name in folders:
        year_str = name[:4]
        mon_str  = name[4:6]
        day_str  = name[6:]
        date.append(datetime.datetime.strptime(day_str+mon_str+year_str, "%d%m%Y").date())

    date.sort(reverse=True)
    
    for date_obj_idx in range(len(date)):
        date_folder = decode_datetime_2_foldername(date[date_obj_idx])
        date_folder_path = os.path.join(qdevice_backup_dir,date_folder)
        target_file_list = [name for name in os.listdir(date_folder_path) if (os.path.isfile(os.path.join(date_folder_path,name)) and (name.split(".")[-1]=='pkl' and name.split("#")[0].lower()==which_dr.lower()))]

        if len(target_file_list) > 1:
            if ip_label == '' :
                for idx, name in enumerate(target_file_list):
                    print(f"index={idx}: {name}")
                idx = int(input("Found many files, which index is your wanted file?"))
                wanted_QD_pkl_path = os.path.join(date_folder_path,target_file_list[idx])
            else:
                button = 1
                for name in target_file_list:
                    if name.split("#")[-1].split("_")[0] == ip_label and name.split("_")[-1].split(".")[0]=="SumInfo":
                        wanted_QD_pkl_path = os.path.join(date_folder_path,name)
                        eyeson_print(f"now use QD_file in {date_folder_path.split('/')[-1]}")
                        button = 0
                        break
                if button:
                    raise ValueError(f"Can't find a suitable QD file for {which_dr}#{ip_label}")
        elif len(target_file_list) == 1:
            if ip_label == '' :
                wanted_QD_pkl_path = os.path.join(date_folder_path,target_file_list[0])
                eyeson_print(f"now use QD_file in {date_folder_path.split('/')[-1]}")
                break
            else:
                if target_file_list[0].split("#")[-1].split("_")[0] == ip_label:
                    eyeson_print(f"now use QD_file in {date_folder_path.split('/')[-1]}")
                    wanted_QD_pkl_path = os.path.join(date_folder_path,target_file_list[0])
                    break
                else:
                    raise ValueError(f"Can't find a suitable QD file for {which_dr}#{ip_label}")
        else:
            pass
        if date_obj_idx == len(date) - 1:
            raise ValueError(f"No QD.pkl for the target_dr={which_dr}")
    
    return wanted_QD_pkl_path




if __name__ == "__main__":
    meas_dr_now = 'dr2'
    which_ip_last = '10'
    print(find_latest_QD_pkl_for_dr(meas_dr_now,which_ip_last))

