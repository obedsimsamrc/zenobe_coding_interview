"""
Zenobe Coding Interview
Obed Sims
Email - obedsims97@yahoo.com
"""
import pandas as pd
from pyomo.environ import NonNegativeReals, ConcreteModel, Binary, Constraint, Var, Param, RangeSet, maximize, Set
from pyomo.opt import SolverStatus, TerminationCondition, SolverFactory
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class Battery(ConcreteModel):

    def __init__(self, battery_capacity: float | int,
                 discharge_power: float | int,
                 charge_power: float | int,
                 charging_eff: float,
                 discharging_eff: float,
                 import_grid_lim: float | int,
                 export_grid_lim: float | int,
                 import_rate: pd.DataFrame,
                 export_rate: pd.DataFrame,
                 time_horizon: int,
                 min_soc: float | int,
                 max_soc: float | int,
                 init_charge: float | int,
                 ):

        ConcreteModel.__init__(self)

        self.battery_cap = battery_capacity
        self.dis_p = discharge_power
        self.charge_p = charge_power
        self.charge_eff = charging_eff
        self.discharge_eff = discharging_eff
        self.import_grid_lim = import_grid_lim
        self.export_grid_lim = export_grid_lim
        self.min_soc = min_soc
        self.max_soc = max_soc
        self.init_charge = init_charge

        # Duration of a market dispatch time interval

        self.M = 24 / time_horizon  # 1 = 1 hour, 0.5 = 30min, 0.25 = 15 min

        #######################################################################################################
        # Sets
        #######################################################################################################
        self.time_horizon = time_horizon
        self.time_horizon_range = Set(initialize=import_rate.index)
        # self.day = RangeSet(import_rate.index.get_level_values(0)[1], import_rate.index.get_level_values(0)[-1])

        #######################################################################################################
        # Params
        #######################################################################################################
        self.import_rate = Param(self.time_horizon_range, initialize=import_rate.to_dict())
        self.export_rate = Param(self.time_horizon_range, initialize=export_rate.to_dict())

        #######################################################################################################
        # Variables
        #######################################################################################################

        self.LevelofEnergy = Var(self.time_horizon_range, domain=NonNegativeReals)
        # battery charge (MW)
        self.charge = Var(self.time_horizon_range, domain=NonNegativeReals, name="Charge (MW)")
        # battery discharge (MW)
        self.discharge = Var(self.time_horizon_range, domain=NonNegativeReals, name="Discharge (MW)")

        # Boolean Variables
        self.charge_bool = Var(self.time_horizon_range, within=Binary)  # Bool for charging
        self.discharge_bool = Var(self.time_horizon_range, within=Binary)  # Bool for discharging

    def add_objective_function(self):

        @self.Objective(sense=maximize)
        def obj_function(model):
            return sum(model.M * (model.export_rate[i] * model.discharge[i]) - model.M * (model.import_rate[i] * model.charge[i])
                       for i in model.time_horizon_range)

    def add_max_cycles_constraint(self, max_daily_cycles: float | int, max_discharge: float | int = None):
        """
        :param max_daily_cycles:
        :param max_discharge:
        :return:
        """

        @self.Constraint()
        def max_daily_discharge_constraint(model):
            # Maximum discharge throughput constraint. The sum of all discharge flow within a day cannot exceed this
            # Vary according to time horizon
            # Base assumption is that the time horizon is at least 24 hours
            if max_discharge:
                return model.M * sum(model.discharge[i] for i in model.time_horizon_range) <= max_discharge
            return model.M * sum(model.discharge[i] for i in model.time_horizon_range) <= max_daily_cycles * self.battery_cap

    def add_storage_constraints(self):
        """
        This function adds all the general storage constraints
        :return:
        """

        # Grid import constraint
        @self.Constraint(self.time_horizon_range)
        def grid_import_constraint(model, i):
            return model.charge[i] <= model.import_grid_lim

        # Grid export constraint
        @self.Constraint(self.time_horizon_range)
        def grid_export_constraint(model, i):
            return model.discharge[i] <= model.export_grid_lim

        # Boolean variables state that charging and discharging can only occur independently
        @self.Constraint(self.time_horizon_range)
        def power_bool_constraint(model, i):
            return model.discharge_bool[i] + model.charge_bool[i] <= 1

        @self.Constraint(self.time_horizon_range)
        def max_charging_power_1(model, i):
            return model.charge[i] <= model.charge_p * model.charge_bool[i]

        @self.Constraint(self.time_horizon_range)
        def max_charging_power_2(model, i):
            return model.charge[i] <= model.charge_p * (1 - model.discharge_bool[i])

        # The discharging power must be within the battery power rating
        @self.Constraint(self.time_horizon_range)
        def max_discharging_power_1(model, i):
            return model.discharge[i] <= model.dis_p * model.discharge_bool[i]

        @self.Constraint(self.time_horizon_range)
        def max_discharging_power_2(model, i):
            return model.discharge[i] <= model.dis_p * (1 - model.charge_bool[i])

        @self.Constraint(self.time_horizon_range)
        def min_soc_constraint(model, i):
            return model.LevelofEnergy[i] >= model.battery_cap * model.min_soc

        @self.Constraint(self.time_horizon_range)
        def max_soc_constraint(model, i):
            return model.LevelofEnergy[i] <= model.battery_cap * model.max_soc

        @self.Constraint(self.time_horizon_range)
        def soc_balance_constraint(model, i):
            # Initial soc set at 50%
            if i == 1:
                return model.LevelofEnergy[i] == model.init_charge + \
                    model.M * (model.charge_eff * model.charge[i] - model.discharge[i] / model.discharge_eff)
            return model.LevelofEnergy[i] == model.LevelofEnergy[i - 1] + \
                model.M * (model.charge_eff * model.charge[i] - model.discharge[i] / model.discharge_eff)

    def solve_problem(self, solver_selection, day_count, mip_rel_gap, time_limit):

        # Solve the optimization problem
        executable = None

        if solver_selection == "cbc":
            if day_count == 1:
                executable = os.path.join(os.getcwd(), "solvers", "cbc.exe").replace("\\", "/")
                # Check if the executable exists and is executable
                if not os.path.exists(executable):
                    print(f"Solver executable {executable} does not exist.")
                elif not os.access(executable, os.X_OK):
                    print(f"Solver executable {executable} is not executable.")
            solver = SolverFactory("cbc",
                                   executable=executable,
                                   options={
                                       'ratio': mip_rel_gap,
                                       'sec': time_limit,
                                   })
        if solver_selection == "cplex":
            if day_count == 0:
                executable = os.path.join(os.getcwd(), "solvers", "cplex.exe").replace("\\", "/")
                # Check if the executable exists and is executable
                if not os.path.exists(executable):
                    print(f"Solver executable {executable} does not exist.")
                elif not os.access(executable, os.X_OK):
                    print(f"Solver executable {executable} is not executable.")
            solver = SolverFactory("cplex",
                                   executable=executable,
                                   options={
                                       'mip tolerances mipgap': mip_rel_gap,
                                       'timelimit': time_limit,
                                   })

        results = solver.solve(self, tee=False)

        # Show a warning if an optimal solution was not found
        if (results.solver.status == SolverStatus.ok) and (results.solver.termination_condition ==
                                                           TerminationCondition.optimal):
            # print("this is feasible and optimal")
            pass
        else:
            # something else is wrong
            logging.info("Status = %s" % results.solver.termination_condition)
            # print(str(results.solver))

    def collect_opt_results(self):

        record_list = []
        SOC_tracker = []

        for i in self.time_horizon_range:
            record = {"DC Charging power (MW)": self.charge[i].value,
                      "DC Discharging power (MW)": self.discharge[i].value,
                      "Charge Bool": self.charge_bool[i].value,
                      "Discharge Bool": self.discharge_bool[i].value,
                      "State of Energy (MWh)": self.LevelofEnergy[i].value,
                      "State of Charge (%)": (self.LevelofEnergy[i].value / self.battery_cap) * 100,
                      "Depth of Discharge (%)": (1 - self.LevelofEnergy[i].value / self.battery_cap) * 100,
                      "Import Price (£/MWh)": self.import_rate[i],
                      "Export Price (£/MWh)": self.export_rate[i],
                      "Import Cost (£)": self.M * self.import_rate[i] * self.charge[i].value,
                      "Export Value (£)": self.M * self.export_rate[i] * self.discharge[i].value,
                      "Trading Profits (£)": self.M * ((self.export_rate[i] * self.discharge[i].value) -
                                                       (self.import_rate[i] * self.charge[i].value)),
                      }

            record_list.append(record)
            SOC_tracker.append(record["State of Energy (MWh)"])

        return record_list, SOC_tracker
