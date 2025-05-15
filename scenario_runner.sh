#!/bin/bash
# This script runs main.py with combinations of:
#   model: [claude-3-7, claude-3-5, gpt-4o]
#   poly: [poly1, poly2, poly3]
#   origin: [Origin1, Origin2, Origin3, Origin4, Origin5]
#   destination: [Destination1, Destination2, Destination3, Destination4, Destination5]
#   with and without the --memory flag.
#
# The command format is:
# python3 main.py <model> dataset.kml <poly> <origin> <destination> solution.kml --image_path flight_plans/3.jpg --log [--memory] --report_file results.csv

# Define the arrays for the arguments.
models=("claude-3-7" "gpt-4o" "o3-mini")
polys=("poly1")
# Using capitalized origin and destination values as shown in your example.
origins=("Origin1" "Origin2")
destinations=("Destination1" "Destination2")
# Options for including --memory: one empty string for no flag and "--memory" for including it.
memory_opts=("" "--memory")

# Loop over every combination of parameters.
for model in "${models[@]}"; do
  for poly in "${polys[@]}"; do
    for origin in "${origins[@]}"; do
      for destination in "${destinations[@]}"; do
        for mem in "${memory_opts[@]}"; do
          # Build the base command with required arguments.
          cmd="python3 main.py $model dataset.kml $poly $origin $destination solution.kml --image_path flight_plans/3.jpg --log"
          # If the memory flag is provided, append it.
          if [ -n "$mem" ]; then
            cmd+=" $mem"
          fi
          # Append the final flag.
          cmd+=" --report_file results.csv"
          
          # Display the command before executing (helpful for tracking).
          echo "Running: $cmd"
          
          # Execute the command.
          eval "$cmd"
        done
      done
    done
  done
done
