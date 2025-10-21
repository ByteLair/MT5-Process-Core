#!/bin/bash
# Script para monitorar uso de CPU e memória durante grid search

echo "=== Monitorando Grid Search ==="
echo "Pressione Ctrl+C para parar"
echo ""

while true; do
    # CPU usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)

    # Memory usage
    mem_info=$(free -h | grep Mem)
    mem_used=$(echo $mem_info | awk '{print $3}')
    mem_total=$(echo $mem_info | awk '{print $2}')

    # Python processes
    python_procs=$(ps aux | grep -E "python.*train_informer_gridsearch" | grep -v grep | wc -l)

    # Clear line and print
    echo -ne "\r[$(date +%H:%M:%S)] CPU: ${cpu_usage}% | RAM: ${mem_used}/${mem_total} | Python workers: ${python_procs}    "

    sleep 2
done
