#!/bin/bash
# Copyright (C) 2024 Nathan S. Nichols
# License MIT [https://opensource.org/licenses/MIT]

# -----------------------------
# Topology / mapping assumptions
# -----------------------------
# Physical core IDs:
#   Socket 0: 0-51   (but core 0 is disabled -> usable 1-51)
#   Socket 1: 52-103 (but core 52 is disabled -> usable 53-103)
#
# Logical core IDs are: physical_core + 104
#   Socket 0 logical usable: 105-155
#   Socket 1 logical usable: 157-207

cores_per_socket_physical=52
sockets=2

socket0_base=0
socket1_base=52

# Disabled physical cores (one per socket)
disabled_core_socket0=0
disabled_core_socket1=52

# Logical offset (logical = physical + 104)
logical_offset=104

# Usable physical cores per socket (52 - 1 disabled)
usable_physical_per_socket=$((cores_per_socket_physical - 1))

# -----------------------------
# Optional flags
# -----------------------------
# DEFAULT: physical-only
include_logical=0
args=()

for a in "$@"; do
  case "$a" in
    --logical|--include-logical)
      include_logical=1
      ;;
    --no-logical|--physical-only)
      include_logical=0
      ;;
    -*)
      echo "Unknown option: $a"
      echo "Usage: $0 <ranks_per_node> [shift_amount] [--logical]"
      exit 1
      ;;
    *)
      args+=("$a")
      ;;
  esac
done

# Check if number of ranks per node is provided
if [ "${#args[@]}" -lt 1 ]; then
    echo "Usage: $0 <ranks_per_node> [shift_amount] [--logical]"
    exit 1
fi

ranks_per_node=${args[0]}
shift_amount=${args[1]:-0} # Default shift amount is 0 if not provided

# -----------------------------
# ranks_per_node == 1 shortcut
# -----------------------------
if [ "$ranks_per_node" -eq 1 ]; then
    # Usable physical ranges: 1-51 and 53-103
    phys="1-51,53-103"

    if [ "$include_logical" -eq 1 ]; then
        # Logical ranges are physical + 104 => 105-155 and 157-207
        log="105-155,157-207"
        cpu_bind_list="${phys},${log}"
    else
        cpu_bind_list="${phys}"
    fi

    echo "--cpu-bind list:$cpu_bind_list"
    exit 0
fi

# -----------------------------
# Round ranks_per_node up to even
# -----------------------------
was_odd=0
if [ $((ranks_per_node % 2)) -ne 0 ]; then
    ranks_per_node=$((ranks_per_node + 1))
    was_odd=1
fi

ranks_per_socket=$((ranks_per_node / sockets))

# -----------------------------
# Max shift logic (based on usable cores)
# -----------------------------
if [ "$ranks_per_socket" -le "$usable_physical_per_socket" ]; then
    cores_per_rank=$((usable_physical_per_socket / ranks_per_socket))
    if [ "$cores_per_rank" -gt 0 ]; then
        max_shift=$((cores_per_rank - 1))
    else
        max_shift=0
    fi
else
    max_shift=0
fi

if [ "$shift_amount" -gt "$max_shift" ]; then
    # N.B. Uncomment to throw error, otherwise shift_amount is silently set to zero
    #echo "Error: Shift amount ($shift_amount) is greater than the maximum allowable shift ($max_shift)."
    #exit 1
    shift_amount=0
fi

# -----------------------------
# Function to generate CPU ranges for a socket
# -----------------------------
generate_cpu_ranges() {
    local socket_base=$1
    local disabled_core=$2
    local rps=$3
    local cpu_ranges=""

    # First usable physical core on this socket
    local phys_first=$((disabled_core + 1))

    # If ranks spill beyond usable physical, assign 1 rank per usable physical
    if [ "$rps" -gt "$usable_physical_per_socket" ]; then
        for (( i=0; i<usable_physical_per_socket; i++ )); do
            local p=$((phys_first + i))
            cpu_ranges+="$p:"
        done

        # Spill into logical only if explicitly enabled
        if [ "$include_logical" -eq 1 ]; then
            local spill=$((rps - usable_physical_per_socket))
            for (( i=0; i<spill; i++ )); do
                local p=$((phys_first + i))
                local l=$((p + logical_offset))
                cpu_ranges+="$l:"
            done
        fi

        echo "${cpu_ranges%:}"
        return
    fi

    # Normal case: partition usable physical cores among ranks
    local cores_per_rank=$((usable_physical_per_socket / rps))

    for (( rank=0; rank<rps; rank++ )); do
        local physical_start=$((phys_first + rank * cores_per_rank + shift_amount))

        if [ "$cores_per_rank" -gt 1 ]; then
            local physical_end=$((physical_start + cores_per_rank - 1))

            if [ "$include_logical" -eq 1 ]; then
                local logical_start=$((physical_start + logical_offset))
                local logical_end=$((physical_end + logical_offset))
                cpu_ranges+="$physical_start-$physical_end,$logical_start-$logical_end:"
            else
                cpu_ranges+="$physical_start-$physical_end:"
            fi
        else
            if [ "$include_logical" -eq 1 ]; then
                local logical=$((physical_start + logical_offset))
                cpu_ranges+="$physical_start,$logical:"
            else
                cpu_ranges+="$physical_start:"
            fi
        fi
    done

    echo "${cpu_ranges%:}"
}

cpu_ranges_socket0=$(generate_cpu_ranges "$socket0_base" "$disabled_core_socket0" "$ranks_per_socket")
cpu_ranges_socket1=$(generate_cpu_ranges "$socket1_base" "$disabled_core_socket1" "$ranks_per_socket")

cpu_bind_list="${cpu_ranges_socket0}:${cpu_ranges_socket1}"

# Conditionally trim the last group if ranks_per_node was originally odd
if [ "$was_odd" -eq 1 ]; then
    cpu_bind_list="${cpu_bind_list%:*}"
fi

echo "--cpu-bind list:$cpu_bind_list"
