#!/bin/bash
# Reset experiment number to ensure it starts from 1
unset experiment_num
experiment_num=1

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
models=("o3-mini")
pairs=(
  "poly1 Origin1 Destination5"
  "poly2 Origin3 Destination1"
  "poly3 Origin4 Destination4"
  "poly4 Origin2 Destination2"
  "poly5 Origin1 Destination3"
  "poly6 Origin1 Destination4"
  "poly7 Origin5 Destination1"
  "poly8 Origin2 Destination3"
  "poly9 Origin3 Destination3"
)
human_preferences=("\"Find the shortest path\"" "\"Find the smoothest path. This means the line segments do not have sharp angles.\"")
system_msgs=("sys_msg_zero_shot_ours" "sys_msg_zero_shot" "sys_msg_one_shot_easy" "sys_msg_one_shot_hard")

for model in "${models[@]}"; do
  for pair in "${pairs[@]}"; do
    # Extract poly, origin, and destination from the pair string.
    read -r poly origin destination <<< "$pair"
    for human_preference in "${human_preferences[@]}"; do
      for system_msg in "${system_msgs[@]}"; do
        for run in {1..3}; do
          # Build the base command with required arguments.
          poly_num=$(echo "$poly" | grep -o '[0-9]\+')
          origin_num=$(echo "$origin" | grep -o '[0-9]\+')
          dest_num=$(echo "$destination" | grep -o '[0-9]\+')
          combined="${poly_num}${origin_num}${dest_num}"
          if [[ "$human_preference" == *"shortest"* ]]; then
              human_preference_number=1
          elif [[ "$human_preference" == *"smoothest"* ]]; then
              human_preference_number=2
          else
              human_preference_number=0
          fi
          image_filename="flight_plans/${model}/${experiment_num}_${combined}_${system_msg}_${human_preference_number}.$((run-1)).jpg"
          experiment_num=$((experiment_num+1))
          cmd="echo ${experiment_num}"
          cmd+=" --report_file CoT.csv"
          

          
          # Uncomment the following lines to run the actual Python command:
          cmd="python3 main.py $model dataset.kml $poly $origin $destination solution.kml --image_path $image_filename --log --system_message '$system_msg' --human_preference '$human_preference' --report_file CoT.csv"
          echo "Running: $cmd"
          eval "$cmd"
        done
      done
    done
  done
done
