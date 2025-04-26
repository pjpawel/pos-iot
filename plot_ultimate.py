import csv
import os
import sys
from enum import StrEnum, auto
from pprint import pprint

import pandas as pd
import matplotlib.pyplot as plt

class Parameter(StrEnum):
    node = auto()
    bad_node = auto()
    delay = auto()
    spectre = auto()

    def plot(self, data: dict[int, list[float]], simulation_dir: str):
        if data == {}:
            raise Exception("No data to plot")
        if self == Parameter.spectre:
            self.plot_error_bar(data, simulation_dir)
            return
        data_values = list(data.values())
        (label, label_pl, cols) = self.get_labels(list(data.keys()))
        y_max = min(6, max([max(x) for x in data_values]))

        plt.figure(figsize=(8, 5))
        plt.boxplot(data_values, labels=cols)
        plt.xlabel(label)
        plt.ylabel("Transaction confirmation time [s]")
        plt.ylim(0, y_max)
        plt.grid(True)
        filepath = os.path.join(simulation_dir, f"{self.name}.png")
        plt.savefig(filepath)
        filepath = os.path.join(simulation_dir, f"{self.name}.pdf")
        plt.savefig(filepath)

        plt.figure(figsize=(8, 5))
        plt.boxplot(data_values, labels=cols)
        plt.xlabel(label_pl)
        plt.ylabel("Czas zatwierdzania transakcji [s]")
        plt.ylim(0, y_max)
        plt.grid(True)
        filepath = os.path.join(simulation_dir, f"{self.name}-pl.png")
        plt.savefig(filepath)
        filepath = os.path.join(simulation_dir, f"{self.name}-pl.pdf")
        plt.savefig(filepath)

    def plot_error_bar(self, data: dict[int, list[float]], simulation_dir: str):
        pprint(data)
        (label, label_pl, cols) = self.get_labels(list(data.keys()))
        x = cols
        y = [line[1] for line in list(data.values())]
        e = [line[2] for line in list(data.values())]
        pprint(x)
        pprint(y)
        pprint(e)

        # plt.figure(figsize=(8, 5))
        # plt.boxplot(data_values, labels=cols)
        # plt.xlabel(label_pl)
        # plt.ylabel("Trust level")
        # #plt.ylim(0, y_max)
        # plt.grid(True)
        # filepath = os.path.join(simulation_dir, f"{self.name}-pl.png")
        # plt.savefig(filepath)
        # filepath = os.path.join(simulation_dir, f"{self.name}-pl.pdf")
        # plt.savefig(filepath)

        plt.errorbar(x, y, yerr=e, linestyle='None', marker='^')
        plt.xlabel(label)
        plt.ylabel("Trust level mean")
        filepath = os.path.join(simulation_dir, f"{self.name}.pdf")
        plt.savefig(filepath)
        filepath = os.path.join(simulation_dir, f"{self.name}.png")
        plt.savefig(filepath)

        plt.errorbar(x, y, yerr=e, linestyle='None', marker='^')
        plt.xlabel(label_pl)
        plt.ylabel("Średni poziom zaufania")
        filepath = os.path.join(simulation_dir, f"{self.name}-pl.pdf")
        plt.savefig(filepath)
        filepath = os.path.join(simulation_dir, f"{self.name}-pl.png")
        plt.savefig(filepath)


    def get_labels(self, keys: list[int]) -> tuple[str, str, list[float]]:
        match self:
            case Parameter.node:
                cols = [2, 4, 6, 8, 10, 15, 20]
                label = "Number of nodes"
                label_pl = "Liczba węzłów"
            case Parameter.bad_node:
                cols = [0, 25, 50, 75, 100]
                label = "Percentage of nodes sending bad transactions [%]"
                label_pl = "Procent węzłów wysyłających złe transakcje [%]"
            case Parameter.delay:
                cols = [0, 50, 100, 150, 200, 250, 300]
                label = "Max delay [ms]"
                label_pl = "Maksymalne opóźnienie [ms]"
            case Parameter.spectre:
                cols = [10, 20, 30, 40, 50, 60, 70, 80, 90]
                label = "Percentage of validators [%]"
                label_pl = "Procent walidatorów [%]"
            case _:
                raise Exception("Unknown parameter")
        #return label, label_pl, [cols[i - 1] for i in keys]
        return label, label_pl, [cols[i] for i in keys]


def main(parameter: Parameter, simulation_dir: str):
    data = {}
    print(f"Processing {simulation_dir}: files: {os.listdir(simulation_dir)}")
    list_dir = os.listdir(simulation_dir)
    list_dir.sort()
    for dir in list_dir:
        base_dir = os.path.join(simulation_dir, dir)
        if not os.path.isdir(base_dir):
            continue
        number = int(dir.split("_")[1])
        print(f"Processing {dir}")
        match parameter:
            case Parameter.spectre:
                filename = "result_trust.csv"
            case _:
                filename = "result_tx.csv"
        path = os.path.join(simulation_dir, dir, "result", filename)
        if not os.path.exists(path):
            print(f"File {path} does not exist")
            continue
            raise Exception(f"File {path} does not exist")

        match parameter:
            case Parameter.spectre:
                with open(path, "r") as file:
                    line = next(csv.reader(file))
                    data[number] = [float(x) for x in line]
            case _:
                with open(path, "r") as file:
                    for line in csv.reader(file):
                        line = [float(x) for x in line]
                        data[number] = line
                        break
                print(
                    f"Summary: \n"
                    f"Mean: {pd.Series(data[number]).mean()} \n"
                    f"Q1: {pd.Series(data[number]).quantile(0.25)} \n"
                    f"Q3: {pd.Series(data[number]).quantile(0.75)} \n"
                    f"Median: {pd.Series(data[number]).median()} \n"
                    f"Min: {pd.Series(data[number]).min()} \n"
                    f"Max: {pd.Series(data[number]).max()} \n"
                )

    parameter.plot(data, simulation_dir)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python plot_ultimate.py <parameter> <path_to_simulation_dir>")
        sys.exit(1)

    print(f"Processing {sys.argv[1]} in {sys.argv[2]}")

    parameter_str = sys.argv[1]
    parameter = getattr(Parameter, parameter_str)
    simulation_dir = sys.argv[2]

    main(parameter, simulation_dir)
