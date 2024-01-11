# User Guide for Aurora CPU Binding Script

## Overview
This script is designed for high-performance computing environments to generate CPU binding lists for multi-core, multi-socket systems. It optimizes the distribution of computational tasks (ranks) across physical and logical cores of a computing node. The output is specifically formatted for use with `mpiexec`, a command used in MPI (Message Passing Interface) environments.

## Usage
The script is executed with one required and one optional argument:
1. `ranks_per_node`: The number of ranks (computational tasks) per node.
2. `shift_amount` (optional): A value to shift the CPU binding range, defaulting to 0 if not provided.

### Command Format
```bash
./get_cpu_bind_aurora <ranks_per_node> [shift_amount]
```

### Examples
1. **Basic Usage**
   - For a node with 4 ranks:
     ```bash
     ./get_cpu_bind_aurora 4
     ```
   - This will output a CPU binding list without any shift.

2. **With Shift Amount**
   - For a node with 4 ranks and a shift amount of 2:
     ```bash
     ./get_cpu_bind_aurora 4 2
     ```
   - This will output a CPU binding list with the specified shift.

### Why Shift the Bindings?
- **Performance Optimization**: In some cases, certain cores may have slightly better performance due to their position on the chip or other factors. Shifting allows you to experiment with different core allocations to optimize performance.
- **Resource Utilization**: It can also be used to avoid using certain cores that might be reserved for other critical system processes.

### Important Notes
- If `ranks_per_node` is less than 1, the script will display a usage message and exit.
- If `ranks_per_node` is 1, the script will output a binding list covering all cores (physical and logical) and then exit.
- If `ranks_per_node` is an odd number, it will be rounded up to the next even number for processing. The script then trims the last group from the CPU binding list. This trimmed output means one less group of cores is utilized, potentially leading to uneven load distribution across the system. It is important to consider this when scheduling jobs in an HPC environment to ensure optimal resource utilization.
- The `shift_amount` must not exceed the maximum allowable shift based on the system's configuration (number of physical cores). If it does, it will be automatically set to zero.

## Output
The script outputs the CPU binding list in the format `--cpu-bind list:<list_of_cpu_ranges>`. This list can be directly used with the `mpiexec` command in MPI job scheduling for setting CPU affinity. The format aligns with the requirements of `mpiexec` for specifying CPU bindings. Users should be mindful of the possible load imbalances number of ranks per node input is odd. The option to shift the bindings provides flexibility for performance optimization and efficient resource utilization.

## Commonly Used Bindings
### 1 Rank per Node
- `--cpu-bind list:0-207`

### 6 Ranks per Node
- `--cpu-bind list:0-16,104-120:17-33,121-137:34-50,138-154:52-68,156-172:69-85,173-189:86-102,190-206`

### 12 Ranks per Node
- `--cpu-bind list:0-7,104-111:8-15,112-119:16-23,120-127:24-31,128-135:32-39,136-143:40-47,144-151:52-59,156-163:60-67,164-171:68-75,172-179:76-83,180-187:84-91,188-195:92-99,196-203`

### 48 Ranks per Node
- `--cpu-bind list:0-1,104-105:2-3,106-107:4-5,108-109:6-7,110-111:8-9,112-113:10-11,114-115:12-13,116-117:14-15,118-119:16-17,120-121:18-19,122-123:20-21,124-125:22-23,126-127:24-25,128-129:26-27,130-131:28-29,132-133:30-31,134-135:32-33,136-137:34-35,138-139:36-37,140-141:38-39,142-143:40-41,144-145:42-43,146-147:44-45,148-149:46-47,150-151:52-53,156-157:54-55,158-159:56-57,160-161:58-59,162-163:60-61,164-165:62-63,166-167:64-65,168-169:66-67,170-171:68-69,172-173:70-71,174-175:72-73,176-177:74-75,178-179:76-77,180-181:78-79,182-183:80-81,184-185:82-83,186-187:84-85,188-189:86-87,190-191:88-89,192-193:90-91,194-195:92-93,196-197:94-95,198-199:96-97,200-201:98-99,202-203`

### 96 Ranks per Node
- `--cpu-bind list:0,104:1,105:2,106:3,107:4,108:5,109:6,110:7,111:8,112:9,113:10,114:11,115:12,116:13,117:14,118:15,119:16,120:17,121:18,122:19,123:20,124:21,125:22,126:23,127:24,128:25,129:26,130:27,131:28,132:29,133:30,134:31,135:32,136:33,137:34,138:35,139:36,140:37,141:38,142:39,143:40,144:41,145:42,146:43,147:44,148:45,149:46,150:47,151:52,156:53,157:54,158:55,159:56,160:57,161:58,162:59,163:60,164:61,165:62,166:63,167:64,168:65,169:66,170:67,171:68,172:69,173:70,174:71,175:72,176:73,177:74,178:75,179:76,180:77,181:78,182:79,183:80,184:81,185:82,186:83,187:84,188:85,189:86,190:87,191:88,192:89,193:90,194:91,195:92,196:93,197:94,198:95,199:96,200:97,201:98,202:99,203`
