import os, datetime, pickle
from xarray import Dataset
from Modularize.support.FluxBiasDict import FluxBiasDict
from Modularize.support.Notebook import Notebook
from quantify_scheduler.device_under_test.quantum_device import QuantumDevice
from quantify_scheduler.device_under_test.transmon_element import BasicTransmonElement

class QDmanager():
    def __init__(self,QD_path:str=''):
        self.path = QD_path
        self.refIQ = {}
        self.Hcfg = {}
        self.Log = "" 
        self.Identity=""
        self.chip_name = ""

    def register(self,cluster_ip_adress:str,which_dr:str,chip_name:str=''):
        """
        Register this QDmanager according to the cluster ip and in which dr and the chip name.
        """
        specifier = cluster_ip_adress.split(".")[-1] # 192.168.1.specifier
        self.Identity = which_dr.upper()+"#"+specifier # Ex. DR2#171
        self.chip_name = chip_name

    def memo_refIQ(self,ref_dict:dict):
        """
        Memorize the reference IQ according to the given ref_dict, which the key named in "q0"..., and the value is composed in list by IQ values.\n
        Ex. ref_dict={"q0":[0.03,-0.004],...} 
        """
        for q in ref_dict:
            self.refIQ[q] = ref_dict[q]
    
    def refresh_log(self,message:str):
        """
        Leave the message for this file.
        """
        self.Log = message

    def QD_loader(self):
        """
        Load the QuantumDevice, Bias config, hardware config and Flux control callable dict from a given json file path contain the serialized QD.
        """
        with open(self.path, 'rb') as inp:
            gift = pickle.load(inp) # refer to `merged_file` in QD_keeper()
        # string and int
        self.chip_name = gift["chip_name"]
        self.Identity = gift["ID"]
        self.Log = gift["Log"]
        self.q_num = len(list(gift["Flux"].keys()))
        # class    
        self.Fluxmanager :FluxBiasDict = FluxBiasDict(qb_number=self.q_num)
        self.Fluxmanager.activate_from_dict(gift["Flux"])
        self.Notewriter: Notebook = Notebook(q_number=self.q_num)
        self.Notewriter.activate_from_dict(gift["Note"])
        self.quantum_device :QuantumDevice = gift["QD"]
        # dict
        self.Hcfg = gift["Hcfg"]
        self.refIQ = gift["refIQ"]
   

        self.quantum_device.hardware_config(self.Hcfg)
        print("Old friends loaded!")
    
    def QD_keeper(self, special_path:str=''):
        """
        Save the merged dictionary to a json file with the given path. \n
        Ex. merged_file = {"QD":self.quantum_device,"Flux":self.Fluxmanager.get_bias_dict(),"Hcfg":Hcfg,"refIQ":self.refIQ,"Log":self.Log}
        """
        if self.path == '' or self.path.split("/")[-2].split("_")[-1] != datetime.datetime.now().day:
            db = Data_manager()
            db.build_folder_today()
            self.path = os.path.join(db.raw_folder,f"{self.Identity}_SumInfo.pkl")
        Hcfg = self.quantum_device.generate_hardware_config()
        # TODO: Here is onlu for the hightlighs :)
        merged_file = {"ID":self.Identity,"chip_name":self.chip_name,"QD":self.quantum_device,"Flux":self.Fluxmanager.get_bias_dict(),"Hcfg":Hcfg,"refIQ":self.refIQ,"Note":self.Notewriter.get_notebook(),"Log":self.Log}
        
        with open(self.path if special_path == '' else special_path, 'wb') as file:
            pickle.dump(merged_file, file)
            print(f'Summarized info had successfully saved to the given path!')
    
    def build_new_QD(self,qubit_number:int,Hcfg:dict,cluster_ip:str,dr_loc:str):
        """
        Build up a new Quantum Device, here are something must be given about it:\n
        (1) qubit_number: how many qubits is in the chip.\n
        (2) Hcfg: the hardware configuration between chip and cluster.\n
        (3) cluster_ip: which cluster is connected. Ex, cluster_ip='192.168.1.171'\n
        (4) dr_loc: which dr is this chip installed. Ex, dr_loc='dr4'
        """
        print("Building up a new quantum device system....")
        self.q_num = qubit_number
        self.Hcfg = Hcfg
        self.register(cluster_ip_adress=cluster_ip,which_dr=dr_loc)
        self.quantum_device = QuantumDevice("academia_sinica_device")
        self.quantum_device.hardware_config(self.Hcfg)
        
        # store references
        self.quantum_device._device_elements = list()

        for i in range(qubit_number):
            qubit = BasicTransmonElement(f"q{i}")
            qubit.measure.acq_channel(i)
            self.quantum_device.add_element(qubit)
            self.quantum_device._device_elements.append(qubit)

        self.Fluxmanager :FluxBiasDict = FluxBiasDict(self.q_num)
        self.Notewriter: Notebook = Notebook(self.q_num)

    ### Convenient short cuts
# Object to manage data and pictures store.

class Data_manager:
    
    def __init__(self):
        from support.Path_Book import meas_raw_dir
        from support.Path_Book import qdevice_backup_dir
        self.QD_back_dir = qdevice_backup_dir
        self.raw_data_dir = meas_raw_dir

    # generate time label for netCDF file name
    def get_time_now(self)->str:
        """
        Since we save the Xarray into netCDF, we use the current time to encode the file name.\n
        Ex: 19:23:34 return H19M23S34 
        """
        current_time = datetime.datetime.now()
        return f"H{current_time.hour}M{current_time.minute}S{current_time.second}"
    
    def get_date_today(self)->str:
        current_time = datetime.datetime.now()
        return f"{current_time.year}_{current_time.month}_{current_time.day}"

    # build the folder for the data today
    def build_folder_today(self,parent_path:str=''):
        """
        Build up and return the folder named by the current date in the parent path.\n
        Ex. parent_path='D:/Examples/'
        """ 
        if parent_path == '':
            parent_path = self.QD_back_dir

        folder = self.get_date_today()
        new_folder = os.path.join(parent_path, folder) 
        if not os.path.isdir(new_folder):
            os.mkdir(new_folder) 
            print(f"Folder {folder} had been created!")

        pic_folder = os.path.join(new_folder, "pic")
        if not os.path.isdir(pic_folder):
            os.mkdir(pic_folder) 
        
        self.raw_folder = new_folder
        self.pic_folder = pic_folder

    
    def save_raw_data(self,QD_agent:QDmanager,ds:Dataset,qb:str='q0',histo_label:str=0,exp_type:str='CS', get_data_loc:bool=False):
        exp_timeLabel = self.get_time_now()
        self.build_folder_today(self.raw_data_dir)
        dr_loc = QD_agent.Identity.split("#")[0]
        if exp_type.lower() == 'cs':
            path = os.path.join(self.raw_folder,f"{dr_loc}{qb}_CavitySpectro_{exp_timeLabel}.nc")
            ds.to_netcdf(path)
        elif exp_type.lower() == 'pd':
            path = os.path.join(self.raw_folder,f"{dr_loc}{qb}_PowerCavity_{exp_timeLabel}.nc")
            ds.to_netcdf(path)
        elif exp_type.lower() == 'fd':
            path = os.path.join(self.raw_folder,f"{dr_loc}{qb}_FluxCavity_{exp_timeLabel}.nc")
            ds.to_netcdf(path)
        elif exp_type.lower() == 'ss':
            path = os.path.join(self.raw_folder,f"{dr_loc}{qb}_SingleShot_{exp_timeLabel}.nc")
            ds.to_netcdf(path)
        elif exp_type.lower() == '2tone':
            path = os.path.join(self.raw_folder,f"{dr_loc}{qb}_2tone_{exp_timeLabel}.nc")
            ds.to_netcdf(path)
        elif exp_type.lower() == 'f2tone':
            path = os.path.join(self.raw_folder,f"{dr_loc}{qb}_Flux2tone_{exp_timeLabel}.nc")
            ds.to_netcdf(path)
        elif exp_type.lower() == 'powerrabi':
            path = os.path.join(self.raw_folder,f"{dr_loc}{qb}_powerRabi_{exp_timeLabel}.nc")
            ds.to_netcdf(path)
        elif exp_type.lower() == 'timerabi':
            path = os.path.join(self.raw_folder,f"{dr_loc}{qb}_timeRabi_{exp_timeLabel}.nc")
            ds.to_netcdf(path)
        elif exp_type.lower() == 'ramsey':
            path = os.path.join(self.raw_folder,f"{dr_loc}{qb}_ramsey_{exp_timeLabel}.nc")
            ds.to_netcdf(path)
        elif exp_type.lower() == 't1':
            path = os.path.join(self.raw_folder,f"{dr_loc}{qb}_ramsey_{exp_timeLabel}.nc")
            ds.to_netcdf(path)
        elif exp_type.lower() == 't2':
            path = os.path.join(self.raw_folder,f"{dr_loc}{qb}_T2({histo_label})_{exp_timeLabel}.nc")
            ds.to_netcdf(path)
        else:
            path = ''
            raise KeyError("Wrong experience type!")
        
        if get_data_loc:
            return path
    
    def save_histo_pic(self,QD_agent:QDmanager,hist_dict:dict,qb:str='q0',mode:str="t1", show_fig:bool=False, save_fig:bool=True):
        from Modularize.support.Pulse_schedule_library import hist_plot
        exp_timeLabel = self.get_time_now()
        self.build_folder_today(self.raw_data_dir)
        dr_loc = QD_agent.Identity.split("#")[0]
        if mode.lower() =="t1" :
            if save_fig:
                fig_path = os.path.join(self.pic_folder,f"{dr_loc}{qb}_T1histo_{exp_timeLabel}.png")
            else:
                fig_path = ''
            hist_plot(qb,hist_dict ,title=r"$T_{1}\  (\mu$s)",save_path=fig_path, show=show_fig)
        elif mode.lower() =="t2" :
            if save_fig:
                fig_path = os.path.join(self.pic_folder,f"{dr_loc}{qb}_T2histo_{exp_timeLabel}.png")
            else:
                fig_path = ''
            hist_plot(qb,hist_dict ,title=r"$T_{2}\  (\mu$s)",save_path=fig_path, show=show_fig)
        else:
            raise KeyError("mode should be 'T1' or 'T2'!")
        
    def save_dict2json(self,QD_agent:QDmanager,data_dict:dict,qb:str='q0',get_json:bool=False):
        """
        Save a dict into json file. Currently ONLY support z-gate 2tone fitting data.
        """
        import json
        exp_timeLabel = self.get_time_now()
        self.build_folder_today(self.raw_data_dir)
        dr_loc = QD_agent.Identity.split("#")[0]
        path = os.path.join(self.raw_folder,f"{dr_loc}{qb}_FluxFqFIT_{exp_timeLabel}.json")
        with open(path, "w") as json_file:
            json.dump(data_dict, json_file)
        print("Flux vs fq to-fit data had been saved!")
        if get_json:
            return path
    
    def get_today_picFolder(self)->str:
        """
        Get the picture folder today. Return its path.
        """
        self.build_folder_today(self.raw_data_dir)
        return self.pic_folder


