#!/usr/bin/python

__author__ = "Cody Hartsook"
__copyright__ = "Cisco (c) 2021 - Cisco Innovation Labs"

__version__ = "1.0"
__status__ = "Development"

from numpy import arange
from pandas import read_csv
from scipy.optimize import curve_fit
from matplotlib import pyplot

datasheet = 'AWS_EC2_Carbon_Footprint_Dataset.csv'

class Compute_Instance_Models():
    def __init__(self) -> None:
        self.cpu_models = {}
        self.mem_models = {}
        self.df = None
        self.__load_instance_metrics()
        self.__create_models()

    def __load_instance_metrics(self):
        dataframe = read_csv(datasheet)
        dataframe.set_index('Instance type', inplace = True)
        self.df = dataframe
 
    # define the true objective function
    def __objective(self, x, a, b, c):
        return a * x + b * x**2 + c

    def __get_cpu_curve_points(self, instance_type):
        x = [0, 10, 50, 100]
        y = [
            float(self.df.loc[instance_type]['PkgWatt @ Idle'].replace(',', '.')),
            float(self.df.loc[instance_type]['PkgWatt @ 10%'].replace(',', '.')),
            float(self.df.loc[instance_type]['PkgWatt @ 50%'].replace(',', '.')),
            float(self.df.loc[instance_type]['PkgWatt @ 100%'].replace(',', '.'))
        ]

        return x, y

    def __get_mem_curve_points(self, instance_type):
        x = [0, 10, 50, 100]
        y = [
            float(self.df.loc[instance_type]['RAMWatt @ Idle'].replace(',', '.')),
            float(self.df.loc[instance_type]['RAMWatt @ 10%'].replace(',', '.')),
            float(self.df.loc[instance_type]['RAMWatt @ 50%'].replace(',', '.')),
            float(self.df.loc[instance_type]['RAMWatt @ 100%'].replace(',', '.'))
        ]

        return x, y

    def __create_models(self):
        cpu_models = {}
        memory_models = {}
        
        for i_type, _ in self.df.iterrows():
            x, y = self.__get_cpu_curve_points(i_type)
            cpu_models[i_type] = (x, y)

            x, y = self.__get_mem_curve_points(i_type)
            memory_models[i_type] = (x, y)

        self.cpu_models = cpu_models
        self.mem_models = memory_models

    def plot_curve_fit(self, instance_type, metric_type):
        if instance_type not in self.cpu_models or instance_type not in self.mem_models:
            print('error: instance type not in loaded models')
            return None

        if metric_type == 'cpu':
            x, y = self.cpu_models[instance_type]
        else:
            x, y = self.mem_models[instance_type]

        popt, _ = curve_fit(self.__objective, x, y)
        a, b, c = popt

        pyplot.scatter(x, y)
        # define a sequence of inputs between the smallest and largest known inputs
        x_line = arange(min(x), max(x), 1)
        # calculate the output for the range
        y_line = self.__objective(x_line, a, b, c)

        # create a line plot for the mapping function
        pyplot.plot(x_line, y_line, '--', color='red')
        pyplot.show()

    def get_line_points(self, instance_type, metric_type):
        if instance_type not in self.cpu_models or instance_type not in self.mem_models:
            print('error: instance type not in loaded models')
            return None

        if metric_type == 'cpu':
            x, y = self.cpu_models[instance_type]
        else:
            x, y = self.mem_models[instance_type]

        popt, _ = curve_fit(self.__objective, x, y)
        a, b, c = popt

        x_line = arange(min(x), max(x), 1)
        # calculate the output for the range
        y_line = self.__objective(x_line, a, b, c)

        return x, y, x_line, y_line

    def estimate_watts(self, instance_type, cpu_load_percent, mem_load_percent):
        if instance_type not in self.cpu_models or instance_type not in self.mem_models:
            raise None

        cpu_load_percent, mem_load_percent = int(cpu_load_percent), int(mem_load_percent)
        if cpu_load_percent > 100:
            cpu_load_percent = 100
        if mem_load_percent > 100:
            mem_load_percent = 100

        x, y = self.cpu_models[instance_type]
        popt, _ = curve_fit(self.__objective, x, y)
        a, b, c = popt
        cpu_watts = self.__objective(cpu_load_percent, a, b, c)
       
        x, y = self.mem_models[instance_type]
        popt, _ = curve_fit(self.__objective, x, y)
        a, b, c = popt
        ram_watts = self.__objective(mem_load_percent, a, b, c)

        usage = {'cpu_watts': cpu_watts, 'mem_watts': ram_watts, 'total_watts':cpu_watts+ram_watts}
        return usage

if __name__ == '__main__':
    m = Compute_Instance_Models()
    
    m.plot_curve_fit('c5.4xlarge', 'cpu')