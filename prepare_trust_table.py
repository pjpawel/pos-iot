import csv
import sys
import os




def main(simulation_dir: str):
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
        path = os.path.join(simulation_dir, dir, "result", "result_trust.csv")
        if not os.path.exists(path):
            continue
            raise Exception(f"File {path} does not exist")

        with open(path, "r") as file:
            for line in csv.reader(file):
                line = [float(x) for x in line]
                data[number] = line
                break

    with open(os.path.join(simulation_dir, "result_trust.tex"), "w") as file:
        file.write("\\begin{center}\n")
        file.write("\\begin{tabular}{|c|c|c|c|c|}\n")
        file.write("\\hline\n")
        #[trust_median, trust_mean, trust_std, trust_q1, trust_q3, trust_max, trust_min]
        file.write("Number & Median & Mean & Std & Q1 & Q3 & Max & Min \\\\\n")
        for number, line in data.items():
            file.write("\\hline\n")
            file.write(f"{number} & " + " & ".join([str(x) for x in line]) + "\\\\\n")
        file.write("\\hline\n")
        file.write("\\end{tabular}\n")
        file.write("\\end{center}\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python prepare_trust_table.py <path_to_simulation_dir>")
        sys.exit(1)

    simulation_dir = sys.argv[1]
    main(simulation_dir)