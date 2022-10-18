#!/usr/bin/python

from pandas import read_csv

def load_and_dump_bare_metal_profiles():
    """
    Loads the bare-metal profile csv file and dumps them to a pandas pickle.
    """
    profiles = read_csv("specs/bare_metal_profiles.csv")

    cols = profiles.iloc[0]
    profiles.columns = cols 
    profiles.drop(0, inplace=True)

    profiles.set_index('CPU name', inplace = True)

    profiles = profiles[profiles['Turbostress repeat'] != 'manual']
    profiles = profiles[profiles['Turbostress repeat'] != 'pending']
    
    profiles.to_pickle("tables/bare_metal_profiles.pkl")

def load_and_dump_cpu_specs():
    """
    Loads the CPU specs csv file and dumps them to a pandas pickle.
    """
    specs = read_csv("specs/cpu_specs.csv")
    specs.set_index('Name', inplace = True)

    specs.to_pickle("tables/cpu_specs.pkl")

if __name__ == '__main__':
    load_and_dump_bare_metal_profiles()
    load_and_dump_cpu_specs()