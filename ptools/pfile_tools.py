"""Some tools to process NAFC custom pfiles

References
----------

Any reference available?
http://www...

"""

__author__ = 'Frederic.Cyr@dfo-mpo.gc.ca'
__version__ = '0.1'

## to do:
# - option for dataFrame with z as columns
# - export multiple dataframe into a netCDF or H5
# - From header, xtract lat, lon, station, line, trip, ship and other attributes (meteo?)

import re
import pandas as pd
import pfiles_basics
import numpy as np
import time as tt
import netCDF4 as nc
import os
from sys import version_info


def pfile_variables(filename):
    """Returns the variables (columns) conmtained in a given pfile

    """

    eoh = pfiles_basics.eoh()

    # read line by line until finding eoh
    tmp = []
    with open(filename, 'r') as td:
        for line in td:
        
            if re.match(eoh, line): # end-of-header            
                break
            else:
                tmp.append(line)

    # Read columns & remove last line of header
    columns = tmp[-1]

    # clean columns
    columns = re.sub('\n','', columns)
    columns = columns.strip()
    columns = re.sub(' +',' ', columns)
    columns = columns.split(' ')

    return columns
        

def pfile_header(filename):
    """Returns the header of a given pfile

    """

    eoh = pfiles_basics.eoh()

    # Read header
    header = []
    with open(filename, 'r') as td:
        for line in td:
        
            if re.match(eoh, line): # end-of-header            
                break
            else:
                header.append(line)

    return header

def pfile_to_dataframe(filename):
    """Reads a pfile given in 'filename' as returns a Pandas.DataFrame with
       columns being the variables

    """

    eoh = pfiles_basics.eoh()
    in_header = True

    # Read header
    header = []
    data = []
    with open(filename, 'r') as td:
        for line in td:
        
            if re.match(eoh, line): # end-of-header            
                in_header = False
                continue # ignore line
            elif in_header: # read header
                header.append(line)
            else: # read data
                line = re.sub('\n','', line)
                line = line.strip()
                line = re.sub(' +',' ', line)
                data.append(line.split(' '))

    # Read columns & remove last line of header
    columns = header[-1]
    header = header[:-1]           

    # clean columns
    columns = re.sub('\n','', columns)
    columns = columns.strip()
    columns = re.sub(' +',' ', columns)

    # to dataFrame       
    df = pd.DataFrame(data, columns=columns.split(' '), dtype=float)

    return df

def bin_pressure_from_dataframe(df, Pbin, var):
    """Extract variable 'var' from dataframe generated by pfile_to_dataframe and digitize it to Pbin

  """
    P = np.array(df['pres'])
    Ibtm = np.argmax(P)
    digitized = np.digitize(P[0:Ibtm], Pbin) 

    if var in df.columns: # This if part should be put in a function.
        X = df[var]
        X = np.array([X[0:Ibtm][digitized == i].mean() for i in range(0, len(Pbin))])
        X = X.reshape(len(X),1)
    else:
        X = Pbin*np.nan
        X = X.reshape(len(X),1)

    return X


def pfiles_to_netcdf(infiles, nc_outfile, zbin=1): # pfiles_to_pannel
    """Given a list of pfiles stored in 'infiles', create a netCDF files with attributes

    Input params:
        - infiles: list of files (e.g. '2017pfiles.lis'**)
        - outfile: output file (e.g. 'AZMP2017.nc')
        - zbin: vertical averaging in final file (zbin=1 is default)

        ** '$ ls *.p2017 > 2017pfiles.list' would generate the appropriate file list in Linux
  """
    # Check if outfile already exist
    if os.path.exists(nc_outfile):

        print nc_outfile + ' already exists!' 

        py3 = version_info[0] > 2 #creates boolean value for test that Python major version > 2

        response_isnt_good = True
        while response_isnt_good:
            if py3:
                response = input(" -> Do you want to remove it? (yes/no?): ")
            else:
                response = raw_input(" -> Do you want to remove it? (yes/no?): ")

            if response == 'yes':
                os.remove(nc_outfile)
                print ' -> ' + nc_outfile + ' removed!' 
                response_isnt_good = False
            elif response == 'no':
                print ' -> Nothing to be done then (an error will be raised)'
                break
            else:
                print ' -> Please answer "yes" or "no"'

    # Generate the list
    filelist = np.genfromtxt(infiles, dtype=str)

    ##### ------- Initialize NetCDF ------- #####
    # File name + global attributes
    nc_out = nc.Dataset(nc_outfile, 'w')

    nc_out.Conventions = 'CF-1.6'
    nc_out.title = 'AZMP netCDF file'
    nc_out.institution = 'Northwest Atlantic Fisheries Centre, Fisheries and Oceans Canada'
    nc_out.source = 'https://github.com/AZMP-NL/AZMP_python_toolbox'
    #nc_out.references = 'a-certain-repo.ca'
    nc_out.description = 'A test by Frederic.Cyr@dfo-mpo.gc.ca'
    #nc_out.tripID = ''
    creation_date = tt.ctime(tt.time())
    nc.history = 'Created ' + creation_date+ ' from NACF Pfiles'
    ## nc_out.history = """
    ##     Should extract info like this from header:
    ##     [2017-10-15 13:18] Some seabird cleaning
    ##     [2017-10-20 15:22] transfer to pfiles
    ##     [2013-10-22 15:18] creating netCDFNetCDF
    ## """
    nc_out.comment = 'Just a trial at the moment, no disctribution!'

    # Create dimensions
    time = nc_out.createDimension('time', None)
    level = nc_out.createDimension('level', None)

    # Create coordinate variables
    times = nc_out.createVariable('time', np.float64, ('time',))
    levels = nc_out.createVariable('level', np.int32, ('level',))

    # Create 1D variables
    latitudes = nc_out.createVariable('latitude', np.float32, ('time'), zlib=True)
    longitudes = nc_out.createVariable('longitude', np.float32, ('time'), zlib=True)
    cast_IDs = nc_out.createVariable('trip ID', np.float32, ('time'), zlib=True)
    stations = nc_out.createVariable('station name', str, ('time'), zlib=True)
    instruments = nc_out.createVariable('instrument', str, ('time'), zlib=True)
    sounder_depths = nc_out.createVariable('sounder depth', np.float32, ('time'), zlib=True)

    # Create 2D variables
    temp = nc_out.createVariable('temperature', np.float32, ('time', 'level'), zlib=True, fill_value=-9999)
    sal = nc_out.createVariable('salinity', np.float32, ('time', 'level'), zlib=True, fill_value=-9999)
    cond = nc_out.createVariable('conductivity', np.float32, ('time', 'level'), zlib=True, fill_value=-9999)
    sigt = nc_out.createVariable('sigma-t', np.float32, ('time', 'level'), zlib=True, fill_value=-9999)
    o2 = nc_out.createVariable('oxygen concentration', np.float32, ('time', 'level'), zlib=True, fill_value=-9999)
    fluo = nc_out.createVariable('fluorescence', np.float32, ('time', 'level'), zlib=True, fill_value=-9999)
    par = nc_out.createVariable('irradiance', np.float32, ('time', 'level'), zlib=True, fill_value=-9999)

    # Variable Attributes
    latitudes.units = 'degree_north'
    longitudes.units = 'degree_east'
    times.units = 'hours since 1900-01-01 00:00:00'
    times.calendar = 'gregorian'
    levels.units = 'dbar'
    levels.standard_name = "pressure"
    #levels.valid_range = np.array((0.0, 5000.0))
    levels.valid_min = 0
    temp.units = 'Celsius'
    temp.long_name = "Water Temperature" # (may be use to label plots)
    temp.standard_name = "sea_water_temperature"
    sal.long_name = "Practical Salinity"
    sal.standard_name = "sea_water_salinity"
    sal.units = "1"
    sal.valid_min = 0
    sigt.standard_name = "sigma_t"
    sigt.long_name = "Sigma-t"
    sigt.units = "Kg m-3"
    o2.long_name = "Dissolved Oxygen Concentration" ;
    o2.standard_name = "oxygen_concentration" ;
    o2.units = "mg L-1" ;
    cond.long_name = "Water Conductivity" ;
    cond.standard_name = "sea_water_conductivity" ;
    cond.units = "S m-1" ;
    fluo.long_name = "Chl-a Fluorescence" ;
    fluo.standard_name = "concentration_of_chlorophyll_in_sea_water" ;
    fluo.units = "mg m-3" ;
    par.long_name = "Irradiance" ;
    par.standard_name = "irradiance" ;
    par.units = "umol photons m-2 s-1" ;
    ##### ------------------------------------- #####

    for idx, fname in enumerate(filelist):

        print fname

        # get header & cast info
        header = pfile_header(fname)
        cast_info = header[1]
        cast_info = re.sub('\n','', cast_info)
        cast_info = re.sub(' +',' ', cast_info)
        cast_info = cast_info.split(' ')

        cast_id = np.int(cast_info[0])
        cast_lat = np.float(cast_info[1]) + np.float(cast_info[2])/60.0
        cast_lon = np.sign(np.float(cast_info[3])) * (np.abs(np.float(cast_info[3])) + np.float(cast_info[4])/60.0)
        cast_time = pd.Timestamp(cast_info[5] + ' ' + cast_info[6])
        cast_sounder = np.int(cast_info[7])
        cast_type = cast_info[8]
        cast_station = cast_info[11]


        # Fill cast info
        latitudes[idx] = cast_lat
        longitudes[idx] = cast_lon
        cast_IDs[idx] = cast_id
        stations[idx] = cast_station
        instruments[idx] = cast_type
        sounder_depths[idx] =cast_sounder

        # get data
        df = pfile_to_dataframe(fname)

       ## ----- Fill wanted variables one by one ----- ##
        # Find pressure
        if 'pres' in df.columns:
            P = np.array(df['pres'])
            Pbin = np.arange(1, np.max(P), zbin) 
        else:
            print 'Problem with file, no pressure channel found [skip]'
            continue

        # Fill dimension
        times[idx] = nc.date2num(cast_time, units = times.units, calendar = times.calendar)
        if len(Pbin) > len(levels): # update depth if this cast is deeper than present max depth
            levels[:] = Pbin

        # Fill nc file with variables
        temp[idx,:] = np.transpose(bin_pressure_from_dataframe(df, Pbin, 'temp'))
        sal[idx,:] = np.transpose(bin_pressure_from_dataframe(df, Pbin, 'sal'))
        cond[idx,:] = np.transpose(bin_pressure_from_dataframe(df, Pbin, 'cond'))
        sigt[idx,:] = np.transpose(bin_pressure_from_dataframe(df, Pbin, 'sigt'))
        fluo[idx,:] = np.transpose(bin_pressure_from_dataframe(df, Pbin, 'flor'))
        o2[idx,:] = np.transpose(bin_pressure_from_dataframe(df, Pbin, 'oxy'))
        par[idx,:] = np.transpose(bin_pressure_from_dataframe(df, Pbin, 'par'))
    # -------------------------------------------------------- #    
    print 'Done!'
    
    nc_out.close()

    return None

