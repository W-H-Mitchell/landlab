
#!/usr/env/python

"""Landlab component that simulates xxxxxx

maybe it should be called "czuba_network_sediment_transporter"

info about the component here

.. codeauthor:: Jon Allison Katy

Created on Tu May 8, 2018
Last edit ---
"""

# %% Import Libraries
from landlab import Component
from landlab.utils.decorators import use_file_name_or_kwds
import numpy as np
import scipy.constants
import copy

# %% Instantiate Object


class NetworkSedimentTransporter(Component):
    """Network bedload morphodynamic component.

    Landlab component designed to calculate _____.
    info info info

    **Usage:**
    Option 1 - Uniform recharge::
        NetworkSedimentTransporter(grid, 
                             bed_parcels,
                             transport_method = 'WilcockCrow',
                             transporter = asdfasdf
                             discharge,
                             channel_geometry,
                             active_layer_thickness)

    Examples
    ----------
    >>> from landlab import RasterModelGrid
    >>> from landlab.components.landslides import LandslideProbability
    >>> import numpy as np

    Things here...


    """

# AP note: this is where the documentation ends and the component starts...

    # component name
    _name = 'NetworkSedimentTransporter'
    __version__ = '1.0'
    
    # component requires these values to do its calculation, get from driver
    _input_var_names = (
        'BMI things here',
        'soil__thickness',
        )

    #  component creates these output values
    _output_var_names = (
        'thing',
        'thing',
        )

    # units for each parameter and output
    _var_units = {
        'topographic__specific_contributing_area': 'm',
        'topographic__slope': 'tan theta',
        }

    # grid centering of each field and variable
    _var_mapping = {
        'topographic__specific_contributing_area': 'node',
        'topographic__slope': 'node',
        }

    # short description of each field
    _var_doc = {
        'topographic__specific_contributing_area':
            ('specific contributing (upslope area/cell face )' +
             ' that drains to node'),
        }

    # Run Component
    @use_file_name_or_kwds
    def __init__(self, grid, 
                 parcels,
                 discharge,
                 transport_method = 'WilcockCrowe',
                 channel_width,
                 flow_depth,
                 active_layer_thickness,
                 **kwds):
        """
        Parameters
        ----------
        grid: RasterModelGrid
            A raster grid.
        and more here...
        """
        
        self.transport_method = transport_method # self.transport_method makes it a class variable, that can be accessed within any method within this class
        if self.transport_method =="WilcockCrowe":
            self.update_transport_time = self._calc_transport_wilcock_crowe
        
        self.parcels = parcels
        self.grid = grid


        super(NetworkSedimentTransporter, self).__init__(grid, **kwds)
        
        
    def partition_active_and_storage_layers(self, **kwds): # Allison is working on this
        """For each parcel in the network, determines whether it is in the
        active or storage layer during this timestep, then updates node elevations
        """
# %%
        vol_tot =  parcels.calc_aggregate_value(np.sum,'volume',at = 'link')
        
        capacity = 2* np.ones(np.size(element_id)) # REPLACE with real calculation for capacity
        
        for i in range(grid.number_of_links):
            
            if vol_tot[i]>0: #only do this check capacity if parcels are in link
                
                #First In Last Out
                parcel_id_thislink = np.where(parcels.DataFrame.element_id.values == i)[0]
               
                time_arrival_sort = np.flip(np.argsort(parcels.DataFrame.time_arrival_in_link.values[parcel_id_thislink]),0)
                parcel_id_time_sorted = parcel_id_thislink[time_arrival_sort]
                
                cumvol = np.cumsum(parcels.DataFrame.volume.values[parcel_id_time_sorted])                

                idxinactive = np.where(cumvol>capacity[i])
                make_inactive = parcel_id_time_sorted[idxinactive]
                
                parcels.set_value(item_id = parcel_id_thislink,variable = 'active_layer', value = 1)
                parcels.set_value(item_id = make_inactive,variable = 'active_layer', value = 0)
        
        # Update Node Elevations
        findactive = parcels.DataFrame['active_layer']==1 # filter for only parcels in active layer        
        vol_act = parcels.calc_aggregate_value(np.sum,
                                                  'volume',at = 'link',
                                                  filter_array = findactive)
        vol_stor = (vol_tot-vol_act)/(1-Lp)
        # ^ Jon-- what's the rationale behind only calculating new node elevations 
        # using the storage volume (rather than the full sediment volume)?
        # Jon response -- because during transport, that is the sediment defining the immobile
        # substrate that is setting the slope. Parcels that are actively transporting should not
        # affect the slope because they are moving.

        
# %%
    def adjust_elevation_and_slope(self, seed=0): # Allison is working on this as of July 23, 2018
        """Adjusts slope for each link based on parcel motions from last
        timestep and additions from this timestep.
        """
#%% Clean these up... where to do all of the imports? Ask Katy
        from landlab.components import FlowDirectorSteepest, FlowAccumulator
        
        fd = FlowDirectorSteepest(grid)
        fd.run_one_step()
        fa = FlowAccumulator(grid, flow_director=fd)
        fa.run_one_step()

# %%

        number_of_contributors = np.sum(fd.flow__link_incoming_at_node == 1, axis=1)
        downstream_link_id = fd.link_to_flow_receiving_node[fd.downstream_node_at_link]
        upstream_contributing_links_at_node = np.where(fd.flow__link_incoming_at_node == 1, grid.links_at_node, -1)
        
        # Update the node elevations depending on the quantity of stored sediment
        for l in range(grid.number_of_nodes):
            
            if number_of_contributors[l] > 0: #we don't update head node elevations
                
                upstream_links = upstream_contributing_links_at_node[l]                
                real_upstream_links = upstream_links[upstream_links != BAD_INDEX_VALUE]                
                width_of_upstream_links = grid.at_link['channel_width'][real_upstream_links]                
                length_of_upstream_links = grid.at_link['link_length'][real_upstream_links]
                
                width_of_downstream_link = grid.at_link['channel_width'][downstream_link_id][l]
                length_of_downstream_link = grid.at_link['link_length'][downstream_link_id][l]
                
                if downstream_link_id[l] == BAD_INDEX_VALUE: # I'm sure there's a better way to do this, but...
                    length_of_downstream_link = 0
                
                # IMPROVE: deal with the downstream most link...
                elev_change = 2*vol_stor[downstream_link_id][l]/(np.sum(width_of_upstream_links * length_of_upstream_links)
                    + width_of_downstream_link * length_of_downstream_link)
                
                grid.at_node['topographic__elevation'][l] += elev_change
      
        # Update channel slope
        for l in range(grid.number_of_links):
            
            upstream_node_id = fd.upstream_node_at_link[l]
            downstream_node_id = fd.downstream_node_at_link[l]
            
            chan_slope = ((grid.at_node['topographic__elevation'][upstream_node_id]
                - grid.at_node['topographic__elevation'][downstream_node_id])
                / grid.at_link['link_length'][l])
                            
            if chan_slope < 1e-4:
                chan_slope = 1e-4
                
            grid.at_link['channel_slope'][l] = chan_slope



# %%
    def _calc_transport_wilcock_crowe(self, H_foreachlink): # Allison
        """Method to determine the transport time for each parcel in the active
        layer using a sediment transport equation. 
        
        Note: could have options here (e.g. Wilcock and Crowe, FLVB, MPM, etc)
        """
        
        parcels = self._parcels
        grid = self._grid
        
# %%
        # parcel attribute arrays from ItemCollector
        
        # another way of doing this --> check to see if this is copying. we don't want to be copying
        Darray = parcels.DataFrame.D.values
        
#        Darray = np.array(parcels.DataFrame.D,copy=False) # this gives a copy, but we can set copy to false..?
        Activearray = parcels.DataFrame.active_layer.values
        Rhoarray = parcels.DataFrame.density.values
        Volarray = parcels.DataFrame.volume.values
        Linkarray = parcels.DataFrame.element_id.values #link that the parcel is currently in
        R = (Rhoarray-rho)/rho
        
        # parcel attribute arrays to populate below
        frac_sand_array = np.zeros(np.size(element_id))
        vol_act_array = np.zeros(np.size(element_id))
        Sarray = np.zeros(np.size(element_id)) 
        Harray = np.zeros(np.size(element_id)) 
        Larray = np.zeros(np.size(element_id))
        d_mean_active = np.zeros(np.size(element_id))
        d_mean_active.fill(np.nan)
        Ttimearray = np.zeros(np.size(element_id)) 
        
        # Calculate bed statistics for all of the links
        vol_tot =  parcels.calc_aggregate_value(np.sum,'volume',at = 'link')
        
        findactive = parcels.DataFrame['active_layer']==1 # filter for only parcels in active layer        
        vol_act = parcels.calc_aggregate_value(np.sum,
                                                  'volume',at = 'link',
                                                  filter_array = findactive)
              
        findactivesand = np.logical_and(Darray<0.002,active_layer ==1)        
        vol_act_sand = parcels.calc_aggregate_value(np.sum,
                                                'volume',at = 'link',
                                                filter_array = findactivesand)

        vol_act_sand[np.isnan(vol_act_sand)==True] = 0
        frac_sand = vol_act_sand/vol_act
        frac_sand[np.isnan(frac_sand)== True] = 0
        
        # Calc attributes for each link, map to parcel arrays
        for i in range(grid.number_of_links): 
            
            active_here = np.where(np.logical_and(Linkarray == i,active_layer == 1))[0]
            
            d_act_i = Darray[active_here]
            vol_act_i = Volarray[active_here]
            d_mean_active[Linkarray == i] = np.sum(d_act_i * vol_act_i)/(vol_act[i])
            
            frac_sand_array[Linkarray == i] = frac_sand[i]
            vol_act_array[Linkarray == i] = vol_act[i]
            Sarray[Linkarray == i] = grid.at_link['channel_slope'][i]
            Harray[Linkarray == i] = H[i]
            Larray[Linkarray == i] = grid.at_link['link_length'][i]

        # Wilcock and crowe claculate transport for all parcels (active and inactive)            
        taursg = rho * R * g * d_mean_active * (0.021 + 0.015*np.exp(-20.*frac_sand_array))        
        frac_parcel = vol_act_array/Volarray;        
        b = 0.67 / (1 + np.exp(1.5 - Darray/ d_mean_active))        
        tau = rho * g * Harray * Sarray        
        taur = taursg * (Darray / d_mean_active) **b        
        tautaur = tau / taur
        tautaur_cplx = tautaur.astype(np.complex128) 
        # ^ work around needed b/c np fails with non-integer powers of negative numbers        
        W = 14 * np.power(( 1 - (0.894/np.sqrt(tautaur_cplx))), 4.5)        
        W[tautaur_cplx<1.35] = 0.002 * np.power(tautaur[tautaur_cplx<1.35],7.5)        
        W = W.real

        # assign travel times only where active==1    
        Ttimearray[Activearray==1] = rho**(3/2)*R[Activearray==1]*g*Larray[Activearray==1]*theta/W[Activearray==1]/tau[Activearray==1]**(3/2)/(1-frac_sand_array[Activearray==1])/frac_parcel[Activearray==1]
        Ttimearray[findactivesand==True] = rho**(3/2)*R[findactivesand==True]*g*Larray[findactivesand==True]*theta/W[findactivesand==True]/tau[findactivesand==True]**(3/2)/frac_sand_array[findactivesand==True]
        # ^ why?? if k = 1 ---> if it's sand...?  ASK JON about the logic here...                            
                            
        #del i b tau taur tautaur tautaur_cplzx taursg W findactive findactivesand

        # Assign those things to the grid -- might be useful for plotting later...?
        grid.at_link['sediment_total_volume'] = vol_tot        
        grid.at_link['sediment__active__volume'] = vol_act
        grid.at_link['sediment__active__sand_fraction'] = frac_sand
        
        
# %%
    def move_parcel_downstream(self, i):    # Jon
        """Method to update parcel location for each parcel in the active 
        layer. 
        """
# %%
 
# imports from Katy's "Navigating Flow Networks"       
        
# import numpy
import numpy as np

# import necessary landlab components
from landlab import RasterModelGrid
from landlab.components import FlowDirectorSteepest, FlowAccumulator


from landlab import BAD_INDEX_VALUE

# import landlab plotting functionality
from landlab.plot.drainage_plot import drainage_plot

        
fd = FlowDirectorSteepest(grid)
fd.run_one_step()
fa = FlowAccumulator(grid, flow_director=fd)
fa.run_one_step()

# %%        
        # we need to make sure we are pointing to the array rather than making copies
        current_link = parcels.DataFrame.element_id.values # same as Linkarray, this will be updated below        
        location_in_link = parcels.DataFrame.location_in_link.values # updated below
        # Ttimearray -- needs to be brought in here            
        #^ Ttimearray is the time to move through the entire length of a link
            
        # However, a parcel is not always at the US end of a link, so need to determine 
        # how much time it takes for that parcel to move out of the current link based on its
        # current location ...
        time_to_exit_current_link = Ttimearray*(1-location_in_link)
        running_travel_time_in_dt = time_to_exit_current_link
            
        
        for p in range(parcels.number_of_items):
            #^ loop through all parcels, this loop could probably be removed in future refinements
                   
            # ... and compare to the timestep dt
            # loop through until you find the link the parcel will reside in after dt
            while running_travel_time_in_dt[p] <= dt :
                # determine downstream link
                downstream_link_id = fd.link_to_flow_receiving_node[fd.downstream_node_at_link[element_id[p]]]
                                
                if downstream_link_id == -1 : #parcel has exited the network
                    # I think we should then remove this parcel from the parcel item collector
                    # if so, we manipulate the exiting parcel here, but may want to note something about its exit
                    # such as output volume and output time into a separate outlet array
                    # ADD CODE FOR THIS HERE, right now these parcel will just cycle through not actually leaving the system
                    break # break out of while loop
                
                current_link[p] = downstream_link_id
                location_in_link[p] = 0 # place parcel at upstream end of DS link
                # ARRIVAL TIME in this link ("current_link") is equal to "t" running time + "running_travel_time_in_dt"
                   
                # movement in DS link is at the same velocity as in US link
                # perhaps modify in future or ensure this type of travel is kept to a minimum by
                # dt < travel time
                time_to_exit_current_link[p] = time_to_exit_current_link[p] / grid.at_link['link_length'][element_id[p]] * grid.at_link['link_length'][current_link[p]]
                running_travel_time_in_dt[p] = running_travel_time_in_dt[p] + time_to_exit_current_link[p]
                
                # TRACK RUNNING TRAVEL DISTANCE HERE SIMILAR TO RUNNING TRAVEL TIME

            time_in_link_before_dt = time_to_exit_current_link[p] - (running_travel_time_in_dt[p] - dt)
            #^ if in same link, this equals dt    
                
            # update location in current link
            location_in_link[p] = location_in_link[p] + (time_in_link_before_dt / time_to_exit_current_link[p])

            # update parcel attributes
            parcels.DataFrame.location_in_link.values[p] = location_in_link[p]
            parcels.DataFrame.element_id.values[p] = current_link[p]
            parcels.DataFrame.active_layer.values[p] = 1 # reset to 1 (active) to be recomputed/determined at next timestep
           
            # USE RUNNING TRAVEL DISTANCE TO UPDATE D AND VOL DUE TO ABRASION HERE            
            
