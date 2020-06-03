"""Module to calculate cooling tower make-up water usage"""

import pandas as pd
import numpy as np
import datetime as dt
import pathlib
import matplotlib.pyplot as plt
import psychrolib
import numba


class Tower:
    """
    Create a cooling tower instance.

    Cooling Tower object can calculate total make-up water consumption
    for a year with hourly cooling profile and hourly weather day.

    This is a proof of concept (POC) level. Hopefully expanded to full tool.

    BIG ASSUMPTIONS (for POC)
    constant entering/leaving water temperatures/enthalpies
    sea level conditions
    constant water quality
    cooling tower cooling water flow = cooling demand [btuh] / (500 * (ewt-lwt))
    100% efficient tower
    constant airflow
    3000 btu/h compressor heat for every 12,000 btu/h of cooling req.

    Future dev ideas:
    Take in raw epw files
    chiller efficiency
    """
    EWT = 95
    LWT = 85
    w_entering_h = 62.95  # btu/lb - 95° water
    w_leaving_h = 52.85  # btu/lb - 85° water
    PRESSURE = 14.6959  # psi sea level atmospheric

    def __init__(self, cycles=5, drift=0.002, dt=10):
        self.cycles = cycles
        self.drift = drift
        self.dt = dt
        self.cooling_profile = np.empty(8760)
        self.ambient_db = np.empty(8760)
        self.ambient_dp = np.empty(8760)
        self.ambient_rh = np.empty(8760)
        self.tmy3 = pd.DataFrame()
        self.air_entering_w = np.empty(8760)
        self.air_entering_h = np.empty(8760)
        self.air_leaving_h = np.empty(8760)
        self.air_entering_wb = np.empty(8760)

    def import_cooling_profile(self, file_path, units='btuh'):
        """
        Reads cooling hourly profile (assumes 8760 hrs) from file_path.

        Default units are BTU/Hr.
        """
        self.cooling_profile = np.array(pd.read_csv(file_path, header=0))*5/4  # compressor heat

    @property
    def cooling_water_flow(self):
        """Annual profile for cooling water flow [gpm]"""
        flow = self.cooling_profile / (self.dt * 500)
        return flow

    def import_weather_data(self, file_path):
        """Reads weather hourly data from file path. 8760hrs of DB and Dew Point expected"""
        psychrolib.SetUnitSystem(psychrolib.IP)
        self.tmy3 = pd.read_csv(file_path,
                                skiprows=list(range(18)),
                                header=0,
                                index_col=[0, 1],
                                usecols=[0, 1, 3, 4, 5])
        self.ambient_db = np.array(self.tmy3['Dry Bulb Temperature {C}'])*9/5 + 32
        self.ambient_dp = np.array(self.tmy3['Dew Point Temperature {C}'])*9/5 + 32
        self.ambient_rh = np.array(self.tmy3['Relative Humidity {%}'])/100
        self.air_entering_w = psychrolib.GetHumRatioFromRelHum(self.ambient_db,
                                                               self.ambient_rh,
                                                               self.PRESSURE)
        self.air_entering_h = psychrolib.GetMoistAirEnthalpy(self.ambient_db,
                                                             self.air_entering_h)
        self.air_entering_wb = psychrolib.GetTWetBulbFromTDewPoint(self.ambient_db,
                                                                   self.ambient_dp,
                                                                   self.PRESSURE)

    @property
    def airflow(self):
        max_wb = self.air_entering_wb.max()
        coincident_db = self.ambient_db[self.air_entering_wb.argmax()]
        design_w = psychrolib.GetHumRatioFromTWetBulb(max_wb, coincident_db)
        design_h = psychrolib.GetMoistAirEnthalpy(coincident_db, design_w)

    @property
    def design_wb(self):
        return self.air_entering_wb.max()

    @property
    def design_day(self):
        max_wb_inx = self.air_entering_wb.argmax()
        date, time = self.tmy3.index[max_wb_inx]
        return f'{date[5:]}-{time}'

    def annual_water_make_up_profile(self):
        """Calculates and returns annual make-up water consumption from the tower"""
        return self.cooling_water_flow * 0.008

    @property
    def total_annual_water_make_up(self):
        """Returns the total amount of make-up water consumed over the year"""
        return np.array(self.cooling_water_flow).sum()

    @property
    def peak_water_make_up(self):
        """Returns the peak make-up water consumption and datetime throughout the year"""
        return np.array(self.cooling_water_flow).max(initial=None)

    @property
    def weather_stats(self):
        pass


if __name__ == '__main__':
    inputs = pathlib.Path.cwd().parent.parent / 'inputs'
    cooling_data = inputs / 'cooling_hourly.csv'
    weather = inputs / 'weather_data.csv'

    tower = Tower()
    tower.import_cooling_profile(cooling_data)
    tower.import_weather_data(weather)
