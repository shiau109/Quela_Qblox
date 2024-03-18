import pickle
from typing import Callable
from Modularize.support.Experiment_setup import get_FluxController
from typing import Tuple
import ipywidgets as widgets
from IPython.display import display
from qblox_instruments import Cluster, PlugAndPlay, ClusterType
from qblox_instruments.qcodes_drivers.qcm_qrm import QcmQrm
from qcodes import Instrument
from quantify_core.measurement.control import MeasurementControl
from quantify_core.visualization.pyqt_plotmon import PlotMonitor_pyqt as PlotMonitor
from quantify_scheduler.device_under_test.quantum_device import QuantumDevice
from quantify_scheduler.instrument_coordinator import InstrumentCoordinator
from quantify_scheduler.instrument_coordinator.components.qblox import ClusterComponent
from utils.tutorial_utils import (
    set_drive_attenuation,
    set_readout_attenuation,
)

from support.QDmanager import QDmanager, Data_manager
import support.UI_Window as uw
import support.Chip_Data_Store as cds

# initialize a measurement
def init_meas(QuantumDevice_path:str='',dr_loc:str='',cluster_ip:str='170',qubit_number:int=5, mode:str='new',vpn:bool=False)->Tuple[QDmanager, Cluster, MeasurementControl, InstrumentCoordinator, dict]:
    """
    Initialize a measurement by the following 2 cases:\n
    ### Case 1: QD_path isn't given, create a new QD accordingly.\n
    ### Case 2: QD_path is given, load the QD with that given path.\n
    args:\n
    cluster_ip: '170' for DR3 (default), '171' for DR2.
    mode: 'new'/'n' or 'load'/'l'. 'new' need a self defined hardware config. 'load' load the given path. 
    """
    import quantify_core.data.handling as dh
    meas_datadir = '.data'
    dh.set_datadir(meas_datadir)
    if mode.lower() in ['new', 'n']:
        from Modularize.support.Experiment_setup import hcfg_map
        cfg, pth = hcfg_map[cluster_ip], ''
        if dr_loc == '':
            raise ValueError ("arg 'dr_loc' should not be ''!")
    elif mode.lower() in ['load', 'l']:
        cluster_ip = get_ip_specifier(QuantumDevice_path)
        cfg, pth = {}, QuantumDevice_path 
    else:
        raise KeyError("The given mode can not be recognized!")
    
    # Connect to the Qblox cluster
    if not vpn:
        # connect, ip = connect_clusters() ## Single cluster online
        # cluster = Cluster(name = "cluster0", identifier = ip.get(connect.value))
        ip, ser = connect_clusters_withinMulti(cluster_ip)
        cluster = Cluster(name = f"cluster{cluster_ip}", identifier = ip)
    else:
        if cluster_ip == '170':
            cluster = Cluster(name = f"cluster{cluster_ip}",identifier = f"qum.phys.sinica.edu.tw", port=5025)
            ip = "192.168.1.170"
        elif cluster_ip == '171':
            cluster = Cluster(name = f"cluster{cluster_ip}",identifier = f"qum.phys.sinica.edu.tw", port=5171)
            ip = "192.168.1.171"
        else:
            raise KeyError("args 'cluster_ip' should be assigned with '170' or '171', check it!")
    enable_QCMRF_LO(cluster)
    Qmanager = QDmanager(pth)
    if pth == '':
        Qmanager.build_new_QD(qubit_number,cfg,ip,dr_loc)
        Qmanager.refresh_log("new-born!")
    else:
        Qmanager.QD_loader()

    meas_ctrl, ic = configure_measurement_control_loop(Qmanager.quantum_device, cluster)
    bias_controller = get_FluxController(cluster,cluster_ip)
    reset_offset(bias_controller)
    return Qmanager, cluster, meas_ctrl, ic, bias_controller

def get_ip_specifier(QD_path:str):
    specifier = QD_path.split("#")[-1].split("_")[0]
    return specifier 

# Configure_measurement_control_loop
def configure_measurement_control_loop(
    device: QuantumDevice, cluster: Cluster, live_plotting: bool = False
    ) ->Tuple[MeasurementControl,InstrumentCoordinator]:
    # Close QCoDeS instruments with conflicting names
    for name in [
        "PlotMonitor",
        "meas_ctrl",
        "ic",
        "ic_generic",
        f"ic_{cluster.name}",
        ] + [f"ic_{module.name}" for module in cluster.modules]:
        try:
            Instrument.find_instrument(name).close()
        except KeyError as kerr:
            pass

    meas_ctrl = MeasurementControl("meas_ctrl")
    ic = InstrumentCoordinator("ic")
    ic.timeout(60*60)

    # Add cluster to instrument coordinator
    ic_cluster = ClusterComponent(cluster)
    ic.add_component(ic_cluster)

    if live_plotting:
        # Associate plot monitor with measurement controller
        plotmon = PlotMonitor("PlotMonitor")
        meas_ctrl.instr_plotmon(plotmon.name)

    # Associate measurement controller and instrument coordinator with the quantum device
    device.instr_measurement_control(meas_ctrl.name)
    device.instr_instrument_coordinator(ic.name)

    return (meas_ctrl, ic)


# close all instruments
def shut_down(cluster:Cluster,flux_map:dict):
    '''
        Disconnect all the instruments.
    '''
    reset_offset(flux_map)
    cluster.reset() 
    Instrument.close_all() 
    print("All instr are closed and zeroed all flux bias!")

# connect to clusters
def connect_clusters():
    with PlugAndPlay() as p:            # Scan for available devices and display
        device_list = p.list_devices()  # Get info of all devices

    names = {dev_id: dev_info["description"]["name"] for dev_id, dev_info in device_list.items()}
    ip_addresses = {dev_id: dev_info["identity"]["ip"] for dev_id, dev_info in device_list.items()}
    connect_options = widgets.Dropdown(         # Create widget for names and ip addresses *** Should be change into other interface in the future
        options=[(f"{names[dev_id]} @{ip_addresses[dev_id]}", dev_id) for dev_id in device_list],
        description="Select Device",
    )
    display(connect_options)
    
    return connect_options, ip_addresses

# Multi-clusters online version connect_clusters()
def connect_clusters_withinMulti(ip_last_posi:str='170'):
    """
    This function is only for who doesn't use jupyter notebook to connect cluster.
    args: \n
    ip_last_posi: '170' for DR3 (default), '171' for DR2.\n
    So far the ip for Qblox cluster is named with 192.168.1.170 and 192.168.1.171
    """
    permissions = {}
    with PlugAndPlay() as p:            # Scan for available devices and display
        device_list = p.list_devices()
    for devi, info in device_list.items():
        permissions[info["identity"]["ip"]] = info["identity"]["ser"]
    if f"192.168.1.{ip_last_posi}" in permissions:
        print(f"192.168.1.{ip_last_posi} is available to connect to!")
        return f"192.168.1.{ip_last_posi}", permissions[f"192.168.1.{ip_last_posi}"]
    else:
        raise KeyError(f"192.168.1.{ip_last_posi} is NOT available now!")
 
# def set attenuation for all qubit
def set_atte_for(quantum_device:QuantumDevice,atte_value:int,mode:str,target_q:list=['q1']):
    """
        Set the attenuations for RO/XY by the given mode and atte. values.\n
        atte_value: integer multiple of 2,\n
        mode: 'ro' or 'xy',\n
        target_q: ['q1']
    """
    # Check atte value
    if atte_value%2 != 0:
        raise ValueError(f"atte_value={atte_value} is not the multiple of 2!")
    # set atte.
    if mode.lower() == 'ro':
        for q_name in target_q:
            set_readout_attenuation(quantum_device, quantum_device.get_element(q_name), out_att=atte_value, in_att=0)
    elif mode.lower() == 'xy':
        for q_name in target_q:
            set_drive_attenuation(quantum_device, quantum_device.get_element(q_name), out_att=atte_value)
    else:
        raise KeyError (f"The mode='{mode.lower()}' is not 'ro' or 'xy'!")


def reset_offset(flux_callable_map:dict):
    for i in flux_callable_map:
        flux_callable_map[i](0.0)


# def add log message into the sumInfo
def leave_LogMSG(MSG:str,sumInfo_path:str):
    """
    Leave the log message in the sumInfo with the given path.
    """
    with open(sumInfo_path, 'rb') as inp:
        gift = pickle.load(inp)
    gift["Log"] = MSG
    with open(sumInfo_path, 'wb') as file:
        pickle.dump(gift, file)
        print("Log message had been added!")


# set attenuations
def init_system_atte(quantum_device:QuantumDevice,qb_list:list,ro_out_att:int=20,xy_out_att:int=20):
    """
    Attenuation setting includes XY and RO. We don't change it once we set it.
    """
    # atte. setting
    set_atte_for(quantum_device,ro_out_att,'ro',qb_list)
    set_atte_for(quantum_device,xy_out_att,'xy',qb_list) 


# LO debug
def get_connected_modules(cluster: Cluster, filter_fn: Callable) -> dict[int, QcmQrm]:
    def checked_filter_fn(mod: ClusterType) -> bool:
        if filter_fn is not None:
            return filter_fn(mod)
        return True

    return {
        mod.slot_idx: mod for mod in cluster.modules if mod.present() and checked_filter_fn(mod)
    }


def enable_QCMRF_LO(cluster):
    QCM_RFs = get_connected_modules(cluster,lambda mod: mod.is_qcm_type and mod.is_rf_type)
    for slot_idx in QCM_RFs:
        QCM_RFs[slot_idx].out0_lo_en(True)
        QCM_RFs[slot_idx].out1_lo_en(True)

    
    print(f"QCM_RF: {list(QCM_RFs.keys())} had been enabled the LO source successfully!")
        




#TOO_OLD
'''
def CSresults_alignPlot(quantum_device:QuantumDevice, results:dict):
    item_num = len(list(results.keys()))
    fig, ax = plt.subplots(1,item_num,figsize=plt.figaspect(1/item_num), sharey = False)
    for idx, q in enumerate(list(results.keys())):
        fr = results[q].run().quantities_of_interest["fr"].nominal_value
        dh.to_gridded_dataset(results[q].dataset).y0.plot(ax = ax[idx])
        ax[idx].axvline(fr, color = "red", ls = "--")
        ax[idx].set_title(f"{q} resonator")
    
    fig.suptitle(f"Resonator spectroscopy, {quantum_device.cfg_sched_repetitions()} repetitions")
    fig.tight_layout()
    plt.show()
    
def PDresults_alignPlot(quantum_device:QuantumDevice, results:dict, show_mode:str='pha'):
    item_num = len(list(results.keys()))

    fig, ax = plt.subplots(1,item_num,figsize=plt.figaspect(1/item_num), sharey = False)
    for idx, q in enumerate(list(results.keys())):
        if show_mode == 'pha':
            dh.to_gridded_dataset(results[q].dataset).y1.plot(ax = ax[idx])
        else:
            dh.to_gridded_dataset(results[q].dataset).y0.plot(ax = ax[idx])
        ax[idx].axhline(quantum_device.get_element(q).clock_freqs.readout(), color = "red", ls = "--")
        ax[idx].set_title(f"{q} resonator")
        
    fig.suptitle(f"Resonator Dispersive, {quantum_device.cfg_sched_repetitions()} repetitions")
    fig.tight_layout()
    plt.show()

def FD_results_alignPlot(quantum_device:QuantumDevice, results:dict, show_mode:str='pha'):
    item_num = len(list(results.keys()))
    fig, ax = plt.subplots(1,item_num,figsize=plt.figaspect(1/item_num), sharey = False)
    for idx, q in enumerate(list(results.keys())):
        dressed_f = results[q].quantities_of_interest["freq_0"]
        offset = results[q].quantities_of_interest["offset_0"].nominal_value
        if show_mode == 'pha':
            dh.to_gridded_dataset(results[q].dataset).y1.plot(ax = ax[idx])
        else:
            dh.to_gridded_dataset(results[q].dataset).y0.plot(ax = ax[idx])
        ax[idx].axhline(dressed_f, color = "red", ls = "--")
        ax[idx].axvline(offset, color = "red", ls = "--")
        ax[idx].set_title(f"{q} resonator")
        
    fig.suptitle(f"Resonator Flux dependence, {quantum_device.cfg_sched_repetitions()} repetitions")
    fig.tight_layout()
    plt.show()


def two_tone_spec_sched_nco(
    qubit_name: str,
    spec_pulse_amp: float,
    spec_pulse_duration: float,
    spec_pulse_port: str,
    spec_pulse_clock: str,
    spec_pulse_frequencies: np.ndarray,
    repetitions: int = 1,
) -> Schedule:
    """
    Generate a batched schedule for performing fast two-tone spectroscopy using the
    `SetClockFrequency` operation for doing an NCO sweep.

    Parameters
    ----------
    spec_pulse_amp
        Amplitude of the spectroscopy pulse in Volt.
    spec_pulse_duration
        Duration of the spectroscopy pulse in seconds.
    spec_pulse_port
        Location on the device where the spectroscopy pulse should be applied.
    spec_pulse_clock
        Reference clock used to track the spectroscopy frequency.
    spec_pulse_frequencies
        Sample frequencies for the spectroscopy pulse in Hertz.
    repetitions
        The amount of times the Schedule will be repeated.
    """
    sched = Schedule("two-tone", repetitions)
    sched.add_resource(ClockResource(name=spec_pulse_clock, freq=spec_pulse_frequencies.flat[0]))

    for acq_idx, spec_pulse_freq in enumerate(spec_pulse_frequencies):
        sched.add(Reset(qubit_name))
        sched.add(SetClockFrequency(clock=spec_pulse_clock, clock_freq_new=spec_pulse_freq))
        sched.add(
            SquarePulse(
                duration=spec_pulse_duration,
                amp=spec_pulse_amp,
                port=spec_pulse_port,
                clock=spec_pulse_clock,
            )
        )
        sched.add(Measure(qubit_name, acq_index=acq_idx))

    return sched
'''