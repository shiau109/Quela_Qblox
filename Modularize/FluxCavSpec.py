from numpy import array, linspace, pi
from utils.tutorial_utils import show_args
from qcodes.parameters import ManualParameter
from Modularize.support import QDmanager, Data_manager
from quantify_scheduler.gettables import ScheduleGettable
from quantify_core.measurement.control import MeasurementControl
from Modularize.support import init_meas, init_system_atte, shut_down
from Modularize.support.Pulse_schedule_library import One_tone_sche, pulse_preview
from utils.tutorial_analysis_classes import ResonatorFluxSpectroscopyAnalysis

def FluxCav_spec(QD_agent:QDmanager,meas_ctrl:MeasurementControl,flux_ctrl:dict,ro_span_Hz:int=3e6,flux_span:float=0.3,n_avg:int=500,f_points:int=30,flux_points:int=40,run:bool=True,q:str='q1',Experi_info:dict={}):

    sche_func = One_tone_sche
        
    analysis_result = {}
    qubit_info = QD_agent.quantum_device.get_element(q)
    ro_f_center = qubit_info.clock_freqs.readout()
    # avoid frequency conflicts 
    from numpy import NaN
    qubit_info.clock_freqs.readout(NaN)

    ro_f_samples = linspace(ro_f_center-ro_span_Hz,ro_f_center+ro_span_Hz,f_points)
    flux_samples = linspace(-flux_span,flux_span,flux_points)
    freq = ManualParameter(name="freq", unit="Hz", label="Frequency")
    freq.batched = True
    
    spec_sched_kwargs = dict(   
        frequencies=freq,
        q=q,
        R_amp={str(q):qubit_info.measure.pulse_amp()},
        R_duration={str(q):qubit_info.measure.pulse_duration()},
        R_integration={str(q):qubit_info.measure.integration_time()},
        R_inte_delay=qubit_info.measure.acq_delay(),
        powerDep=False,
    )
    exp_kwargs= dict(sweep_F=['start '+'%E' %ro_f_samples[0],'end '+'%E' %ro_f_samples[-1]],
                     Flux=['start '+'%E' %flux_samples[0],'end '+'%E' %flux_samples[-1]])
    
    if run:
        gettable = ScheduleGettable(
            QD_agent.quantum_device,
            schedule_function=sche_func, 
            schedule_kwargs=spec_sched_kwargs,
            real_imag=False,
            batched=True,
        )
        QD_agent.quantum_device.cfg_sched_repetitions(n_avg)
        meas_ctrl.gettables(gettable)
        meas_ctrl.settables([freq,flux_ctrl[q]])
        meas_ctrl.setpoints_grid((ro_f_samples,flux_samples))
        
        
        
        rfs_ds = meas_ctrl.run("One-tone-Flux")
        # Save the raw data into netCDF
        Data_manager().save_raw_data(QD_agent=QD_agent,ds=rfs_ds,qb=q,exp_type='FD')
        analysis_result[q] = ResonatorFluxSpectroscopyAnalysis(tuid=rfs_ds.attrs["tuid"], dataset=rfs_ds).run()
        show_args(exp_kwargs, title="One_tone_FluxDep_kwargs: Meas.qubit="+q)
        if Experi_info != {}:
            show_args(Experi_info(q))
        
        # reset flux bias
        flux_ctrl[q](0.0)
        qubit_info.clock_freqs.readout(ro_f_center)
        
    else:
        n_s = 2
        sweep_para= array(ro_f_samples[:n_s])
        spec_sched_kwargs['frequencies']= sweep_para.reshape(sweep_para.shape or (1,))
        pulse_preview(QD_agent.quantum_device,sche_func,spec_sched_kwargs)

        show_args(exp_kwargs, title="One_tone_FluxDep_kwargs: Meas.qubit="+q)
        if Experi_info != {}:
            show_args(Experi_info(q))
    return analysis_result

def update_flux_info_in_results_for(QD_agent:QDmanager,qb:str,FD_results:dict):
    qubit = QD_agent.quantum_device.get_element(qb)
    qubit.clock_freqs.readout(FD_results[qb].quantities_of_interest["freq_0"])
    QD_agent.Fluxmanager.save_sweetspotBias_for(target_q=qb,bias=FD_results[qb].quantities_of_interest["offset_0"].nominal_value)
    QD_agent.Fluxmanager.save_period_for(target_q=qb, period=2*pi/FD_results[qb].quantities_of_interest["frequency"].nominal_value)
    QD_agent.Fluxmanager.save_tuneawayBias_for(target_q=qb,mode='auto')
    QD_agent.Fluxmanager.save_cavFittingParas_for(target_q=qb,
        f=FD_results[qb].quantities_of_interest["frequency"].nominal_value,
        amp=FD_results[qb].quantities_of_interest["amplitude"].nominal_value,
        phi=FD_results[qb].quantities_of_interest["shift"].nominal_value,
        offset=FD_results[qb].quantities_of_interest["offset"].nominal_value
    )


def fluxCavity_executor(QD_agent:QDmanager,meas_ctrl:MeasurementControl,specific_qubits:str,run:bool=True,flux_span:float=0.4,ro_span_Hz=3e6):
    
    if run:
        print(f"{specific_qubits} are under the measurement ...")
        init_system_atte(QD_agent.quantum_device,list([specific_qubits]),ro_out_att=QD_agent.Notewriter.get_DigiAtteFor(specific_qubits,'ro'))
        FD_results = FluxCav_spec(QD_agent,meas_ctrl,Fctrl,ro_span_Hz=ro_span_Hz,q=specific_qubits,flux_span=flux_span)[specific_qubits]
        if FD_results == {}:
            print(f"Flux dependence error qubit: {specific_qubits}")
        
    else:
        init_system_atte(QD_agent.quantum_device,list(Fctrl.keys()),ro_out_att=QD_agent.Notewriter.get_DigiAtteFor(specific_qubits,'ro'))
        FD_results = FluxCav_spec(QD_agent,meas_ctrl,Fctrl,ro_span_Hz=ro_span_Hz,q=specific_qubits,flux_span=flux_span,run=False)

    return FD_results

if __name__ == "__main__":
    
    """ Fill in """
    execution = True
    update = True
    ro_elements = ['q4']
    QD_path = 'Modularize/QD_backup/2024_3_28/DR2#171_SumInfo.pkl'

    """ Preparations """
    QD_agent, cluster, meas_ctrl, ic, Fctrl = init_meas(QuantumDevice_path=QD_path,mode='l')


    """ Running """
    FD_results = {}
    for qubit in ro_elements:
        FD_results[qubit] = fluxCavity_executor(QD_agent,meas_ctrl,qubit,run=execution)
        if execution:
            if update:
                update_flux_info_in_results_for(QD_agent,qubit,FD_results)
        else:
            break

    
    """ Storing """
    if update and execution:
        QD_agent.refresh_log("after FluxDep")
        QD_agent.QD_keeper()


    """ Close """
    print('Flux dependence done!')
    shut_down(cluster,Fctrl)