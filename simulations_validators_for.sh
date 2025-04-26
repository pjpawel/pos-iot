#!/bin/bash

# Run all simulations - in time of 7000 seconds
# Simulations:
# 1. All correct transactions
# 2. Some nodes sending incorrect transactions
# 3. All nodes has random delay

SLEEP_TIME="${1:-500}"
NODE_NUMBER="${2:-19}"

source env/bin/activate

DATE=$(date +"%y_%m_%d_%s")
SIMULATIONS_DIR=../monitor/simulation_"$DATE"

############# SCENARIOS ############
SCENARIOS=(15 16 17 18) #12 1 13 14 15 16 17 18 19
####################################

mkdir -p "$SIMULATIONS_DIR"

for index in "${!SCENARIOS[@]}"; do
    SCENARIO="${SCENARIOS[$index]}"

    printf "\n"
    echo "************************************"
    echo "Running simulation $index. Scenario $SCENARIO"
    echo "************************************"
    printf "\n"

    if [ "$index" -eq 0 ]; then
        ./compose-start.sh "$SCENARIO" 1 "$NODE_NUMBER"
    else
        ./compose-start.sh "$SCENARIO" 0 "$NODE_NUMBER"
    fi

    sleep "$SLEEP_TIME"
    ./compose-stop.sh

    printf "\n"
    echo "************************************"
    echo "Simulation $index stopped"
    echo "************************************"
    printf "\n"

    python3 monitor.py

    SIMULATION_DIR="$SIMULATIONS_DIR/simulation_$index"
    #mkdir -p "$SIMULATION_DIR/storage"
    mkdir -p "$SIMULATION_DIR/result"

    # If you want to copy the storage files, uncomment the following line
    # cp -r ../storage/* "$SIMULATION_DIR/storage"
    mv ../monitor/result/* "$SIMULATION_DIR/result"

    printf "\n"
    echo "************************************"
    echo "Simulation $index finished (Scenario $SCENARIO)"
    echo "************************************"
    printf "\n"
done


#
#############################################
## Run simulation 1
#printf "\n"
#echo "************************************"
#echo "Running simulation 1"
#echo "************************************"
#printf "\n"
#
#./compose-start.sh 12 1 "$NODE_NUMBER"
#sleep "$SLEEP_TIME"
#./compose-stop.sh
#
#printf "\n"
#echo "************************************"
#echo "Simulation 1 stopped"
#echo "************************************"
#printf "\n"
#
#python3 monitor.py
#
#SIMULATION_DIR=$SIMULATIONS_DIR/simulation_1
#mkdir -p "$SIMULATION_DIR"
#mkdir -p "$SIMULATION_DIR"/storage
#mkdir -p "$SIMULATION_DIR"/result
#
##cp -r ../storage/* "$SIMULATION_DIR"/storage
#mv ../monitor/result/* "$SIMULATION_DIR"/result
#
#printf "\n"
#echo "************************************"
#echo "Simulation 1 finished"
#echo "************************************"
#printf "\n"
