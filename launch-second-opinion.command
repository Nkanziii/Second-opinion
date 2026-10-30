#!/bin/bash
# One-click launcher for Second Opinion.
# Double-click this file. It opens the TouchDesigner project, then starts the doctors in loop mode.

cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"

# load conda / python setup if there is one
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" 2>/dev/null
[ -f "$HOME/.bash_profile" ] && source "$HOME/.bash_profile" 2>/dev/null

echo "Opening TouchDesigner..."
open "$ROOT/visuals/persona_cloud.toe"

echo "Waiting 12 seconds for the orbs to load..."
echo "(If the output window is not showing, click the Open button on window1.)"
sleep 12

cd "$ROOT/src" || exit 1
echo "Starting the doctors..."
python3 run_experiment.py --converse --speak --voice --loop

echo
echo "Finished. Press Enter to close this window."
read -r
