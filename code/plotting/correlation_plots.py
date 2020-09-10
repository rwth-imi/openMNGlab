# -*- coding: utf-8 -*-
import numpy as np
import functools

import plotly.graph_objects as go
import ipywidgets as widgets
from ipywidgets import interact, interact_manual, interactive, fixed
from .conversion import *

def big_plot(dapsys, sigs_dict, amplitudes_list, freq):
    '''
    Plot whole recording divided by pulses. Color APs and template with special. 
    
    Parameters
    -------
    dapsys: DapsysImporter | dapsys importer instance. 
    amplitudes_list: list | Seg2seg amplitudes from dapsys.get_raw_signal_split_by_stimuli() function.
    freq: float | Uniform difference between two neighboring datapoints within the file that we're using (e.g. 0.1). 
    sigs_dict: list | Dict from conversion.convert_signals_to_dict()
    
    Returns
    -------
    g: go.FigureWidget | Widget instance based on dapsys info. 
    '''     
    sigs_dict_filter = [d for d in sigs_dict if d['segment_idx']==0 or d['name']=='Threshold']
    traces_signals = find_traces_amplitudes(sigs_dict_filter)

    trace_main = go.Scatter(line=dict(color="gray", width=1), 
                            x=np.arange(0, len(amplitudes_list[0]), freq), 
                            y=amplitudes_list[0], name = 'Regular')
    
    g=go.FigureWidget(data=traces_signals+[trace_main],
                      layout=go.Layout(title=dict(text='Segment 1'),
                                       xaxis=dict(title='Latency (ms)'),
                                       yaxis=dict(title='Amplitude', range=[-10, 10]),
                                       barmode='overlay'))  
    
    return g 

def update_big_plot(change, g, amplitudes_list, segments_main, freq, sigs_dict):
    '''
    Observer for big_plot() function.
    
    Parameters
    -------
    change: traitlets.utils.bunch.Bunch | Necessary for widgets to work? 
    g: go.FigureWidget | from huge_plot()
    amplitudes_list: list | Seg2seg amplitudes from dapsys.get_raw_signal_split_by_stimuli() function.
    segments_main: widgets.IntSlider | slider from widgets
    freq: float | Uniform difference between two neighboring datapoints within the file that we're using (e.g. 0.1). 
    sigs_dict: list | Dict from conversion.convert_signals_to_dict()
    '''      
    with g.batch_update():
            
        idx = segments_main.value-1
        g.data = []
        g.add_scatter(x=np.arange(0, len(amplitudes_list[idx]), freq), y=amplitudes_list[idx], mode='lines', 
                          name=f'Regular', line=dict(color="gray", width=1))
        
        sigs_dict_filter = [d for d in sigs_dict if d['segment_idx']==idx or d['name']=='Threshold']
        for i, scatter in enumerate(find_traces_amplitudes(sigs_dict_filter)):
            g.add_scatter(x=scatter['x'], y=scatter['y'], mode='lines', name=scatter['name'], 
                          fillcolor=scatter['fillcolor'], line=dict(color=scatter['fillcolor']))
            
        g.layout.barmode = 'overlay'
        g.layout.title.text = f'Segment {idx+1}'

def histo_signal_plot(dapsys, tap_corrs, real_corrs, freq, taps, trck_dict):
    '''
    Plot histograms and APs simultaneously.  
    
    Parameters
    -------
    dapsys: DapsysImporter | dapsys importer instance. 
    tap_corrs: list | list of correlations between template and manually found APs.
    real_corrs: list | list of correlations between template and correct APs. 
    freq: float | Uniform difference between two neighboring datapoints within the file that we're using (e.g. 0.1). 
    trck_dict: dict | From Dapsys.extract_segment_idxs_times().
    
    Returns
    -------
    [fig1, fig2] list | list of two figures, one for histogram and one for signals.  
    '''     
    fig1 = go.FigureWidget()
    fig1.add_trace(go.Histogram(x=tap_corrs, name = 'Above-threshold', marker_color='green', legendgroup='a'))
    fig1.add_trace(go.Histogram(x=real_corrs, name = 'Correct', marker_color='gold', legendgroup='b'))
    fig1.update_traces(opacity=0.6)
    fig1.add_trace(go.Box(x=tap_corrs, name='Above-threshold', yaxis='y2', marker_color='green', legendgroup='a', showlegend=False) )
    fig1.add_trace(go.Box(x=real_corrs, name='Correct', yaxis='y2', marker_color='gold', legendgroup='b', showlegend=False) )
    
    fig1.layout = dict(xaxis=dict(domain=[0, 1], title='Correlation'), yaxis=dict(domain=[0, 0.8], title='Count'), 
                       xaxis2=dict(domain=[0, 1]), yaxis2=dict(domain=[0.8, 1]),
                       legend_title_text='Signal type:', barmode='overlay', margin=dict(t=50), bargap=0,
                          title_text='Correct vs threshold signals')
    
    traces_full = find_traces_amplitudes(convert_signals_to_dict(taps, dapsys.main_pulses, freq, full_scale=False, template=dapsys.template, trck_dict=trck_dict))
    template_dict = find_traces_amplitudes([convert_template_to_dict(dapsys.template, freq)])
    
    fig2 = go.FigureWidget()
    for scatter in traces_full+template_dict:
        fig2.add_trace(scatter)
    
    fig2.layout = dict(barmode='overlay', xaxis=dict(title='Time (ms)', range=[0, 3-freq]),
                         width=900, height=500, title=dict(text='Template and threshold spikes'), 
                         yaxis=dict(title='Amplitude', range=[-10, 10]))
    
    return [fig1, fig2]

def histo_signal_plot_update(_, out_mod, slider_mod,
                             dapsys, freq, trck_dict, 
                             fig1, fig2, tap_corrs, taps):
    '''
    Observer for histo_signal_plot() function. 
    
    Parameters
    -------
    out_mod: widgets.Output() | Widget output. 
    slider_mod: widgets.FloatSlider | Widget slider. 
    dapsys: DapsysImporter | dapsys importer instance. 
    freq: float | Uniform difference between two neighboring datapoints within the file that we're using (e.g. 0.1). 
    trck_dict: dict | From Dapsys.extract_segment_idxs_times().
    fig1, fig2: go.FigureWidget() | figures from histo_signal_plot().
    tap_corrs: list | list of correlations between template and manually found APs.
    taps: List[ActionPotential] | dapsys.get_threshold_action_potentials
    '''    
    with out_mod:
        
        correlation_boundary = slider_mod.value 
        fig2.data = []
        print(f'Correlation threshold: {correlation_boundary}')
        fig1.data[0].x = fig1.data[2].x = [val for val in tap_corrs if val > correlation_boundary]
        
        with fig2.batch_update():
            filtered_traces = filter_traces(convert_signals_to_dict(taps, dapsys.main_pulses, freq, full_scale=False, template=dapsys.template, trck_dict=trck_dict), correlation_boundary)
            traces_full = find_traces_amplitudes(filtered_traces)
            
            template_dict = find_traces_amplitudes([convert_template_to_dict(dapsys.template, freq)])
            for scatter in traces_full+template_dict:
                fig2.add_trace(scatter)




def reaction_plot_threshold(thresh_df):
    '''
    Plot APs in time-correlation manner.  
    
    Parameters
	----------
    thresh_df: df | Dataframe generated based on dict_to_df(). 

    Returns
	-------
    gg: go.FigureWidget | Plotly Figure 
                      x axis : Time/Latency, y axis : Correlation,
                      darker the color, later the APs
    '''     
    idxs = thresh_df.segment_id.unique()
    cols = colors.get_colors(plt.cm.plasma, len(idxs))
    traces = []
    
    for segment_idx in idxs:
        sub_df = thresh_df[thresh_df['segment_id']==segment_idx]
        traces.append(go.Scatter(x=sub_df['Time (s)'], y=sub_df['Correlation'], 
                                 name=f'Segment: {segment_idx+1} | No of spikes: {len(sub_df)}', 
                                 opacity = 0.20, mode = 'markers', marker=dict(color=cols[segment_idx])))

    gg = go.FigureWidget(data=traces, layout=go.Layout(title=dict(text=f'Threshold signals correlation'), barmode='overlay',
                            xaxis=dict(title='Time (s)', range=[-0.02, 4.02]), 
                            yaxis=dict(title='Correlation', range=[-0.02, 1.02]))
                           )

    gg.data[0].opacity = 1
    return gg

def delay_plot_set_active_segment(_, out_act, g, segment_slider_act, mapping, idxs):
    '''
    Observer for reaction_plot_threshold(). 
    
    Parameters
	----------
    out_act: widgets.Output() | Widget output. 
    g: go.FigureWidget | From reaction_plot_threshold() function
    segment_slider_act: widgets.FloatSlider | Widget slider. 
    mapping: dict | Dictionary with APs in form of keys being segment_idx and values being cumulative integers (spike enumerator).  
    idxs: list | unique segments. 
    '''     
    with out_act:
        active_segment = segment_slider_act.value-1
        active_segment = mapping[active_segment]
        g.data[active_segment].opacity = 1

        for idx in range(0, len(idxs)):
            if idx == active_segment or idx==len(g.data):
                continue
            else:
                g.data[idx].opacity = 0.20

def delay_plot_set_all_segments_active(_, out_act, g, idxs):
    '''
    Observer for reaction_plot_threshold(). 
    
    Parameters
	----------
    out_act: widgets.Output() | Widget output. 
    g: go.FigureWidget | From reaction_plot_threshold() function
    idxs: list | unique segments. 
    '''  
    with out_act:
        for idx in range(0, len(idxs)):
            g.data[idx].opacity = 1
            
def save_excel(_, out_act, thresh_df, text_act):
    '''
    Save correlations of APs in excel file. 
    
    Parameters
	----------
    out_act: widgets.Output() | Widget output. 
    thresh_df: df | Dataframe generated based on dict_to_df(). 
    text_act: String | name/path of the excel file to be saved. 
    '''     
    with out_act: 
        display(HTML(f'<i>Saving .. {text_act.value}.xlsx</i>'))
        saving_df = deepcopy(thresh_df)
        saving_df['segment_id'] = saving_df['segment_id'] + 1
        saving_df.to_excel(f'{text_act.value}.xlsx', engine='xlsxwriter', index=False)
        display(HTML('<i>File successfully saved!</i>'))