#!/bin/bash

# Run all simulations - in time of 7000 seconds
# Simulations:
# 1. All correct transactions
# 2. Some nodes sending incorrect transactions
# 3. All nodes has random delay

source env/bin/activate

DATE=$(date +"%y_%m_%d_%s")
SIMULATIONS_DIR=../monitor/simulation_"$DATE"

mkdir -p "$SIMULATIONS_DIR"

############################################
# Run simulation 1
printf "\n"
echo "************************************"
echo "Running simulation 1"
echo "************************************"
printf "\n"

./compose-start.sh
sleep 500
./compose-stop.sh

printf "\n"
echo "************************************"
echo "Simulation 1 stopped"
echo "************************************"
printf "\n"

python3 monitor.py

SIMULATION_DIR=$SIMULATIONS_DIR/simulation_1
mkdir -p "$SIMULATION_DIR"
mkdir -p "$SIMULATION_DIR"/storage
mkdir -p "$SIMULATION_DIR"/result

cp -r ../storage/* "$SIMULATION_DIR"/storage
mv ../monitor/result/* "$SIMULATION_DIR"/result

printf "\n"
echo "************************************"
echo "Simulation 1 finished"
echo "************************************"
printf "\n"

############################################
# Run simulation 2

printf "\n"
echo "************************************"
echo "Running simulation 2"
echo "************************************"
printf "\n"

./compose-start.sh 2 0
sleep 500
./compose-stop.sh

printf "\n"
echo "************************************"
echo "Simulation 2 stopped"
echo "************************************"
printf "\n"

python3 monitor.py

SIMULATION_DIR="$SIMULATIONS_DIR"/simulation_2
mkdir -p "$SIMULATION_DIR"
mkdir -p "$SIMULATION_DIR"/storage
mkdir -p "$SIMULATION_DIR"/result

cp -r ../storage/* "$SIMULATION_DIR"/storage
mv ../monitor/result/* "$SIMULATION_DIR"/result

printf "\n"
echo "************************************"
echo "Simulation 2 finished"
echo "************************************"
printf "\n"

############################################
# Run simulation 3

printf "\n"
echo "************************************"
echo "Running simulation 3"
echo "************************************"
printf "\n"

./compose-start.sh 3 0
sleep 500
./compose-stop.sh

printf "\n"
echo "************************************"
echo "Simulation 3 stopped"
echo "************************************"
printf "\n"

python3 monitor.py

SIMULATION_DIR=$SIMULATIONS_DIR/simulation_3
mkdir -p "$SIMULATION_DIR"
mkdir -p "$SIMULATION_DIR"/storage
mkdir -p "$SIMULATION_DIR"/result

cp -r ../storage/* "$SIMULATION_DIR"/storage
mv ../monitor/result/* "$SIMULATION_DIR"/result

printf "\n"
echo "************************************"
echo "Simulation 3 finished"
echo "************************************"
printf "\n"

############################################
# Run simulation 4

printf "\n"
echo "************************************"
echo "Running simulation 4"
echo "************************************"
printf "\n"

./compose-start.sh 4 0 12
sleep 500
./compose-stop.sh

printf "\n"
echo "************************************"
echo "Simulation 4 stopped"
echo "************************************"
printf "\n"

python3 monitor.py

SIMULATION_DIR=$SIMULATIONS_DIR/simulation_4
mkdir -p "$SIMULATION_DIR"
mkdir -p "$SIMULATION_DIR"/storage
mkdir -p "$SIMULATION_DIR"/result

cp -r ../storage/* "$SIMULATION_DIR"/storage
mv ../monitor/result/* "$SIMULATION_DIR"/result

printf "\n"
echo "************************************"
echo "Simulation 4 finished"
echo "************************************"
printf "\n"
