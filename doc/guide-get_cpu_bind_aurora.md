# User Guide for Aurora CPU Binding Script

## Overview

This script generates `--cpu-bind list:<...>` strings for MPI runs on Aurora-style nodes with **2 sockets** and a specific CPU numbering/topology:

* **Physical cores**

  * Socket 0: `0–51` but **core 0 is disabled** → usable `1–51`
  * Socket 1: `52–103` but **core 52 is disabled** → usable `53–103`
* **Logical (SMT) cores**

  * Computed as **logical = physical + 104**
  * Therefore usable logical ranges are:

    * Socket 0: `105–155` (since physical `1–51`)
    * Socket 1: `157–207` (since physical `53–103`)

By default, the script generates **physical-only** bindings (i.e., logical cores are **not included** unless explicitly requested).

## Usage

The script accepts:

1. `ranks_per_node` (required): number of MPI ranks per node
2. `shift_amount` (optional): shift applied within each socket’s usable physical range (defaults to `0`)
3. `--logical` (optional): include logical cores in addition to physical cores

### Command Format

```bash
./get_cpu_bind_aurora <ranks_per_node> [shift_amount] [--logical]
```

> Notes on flags:
>
> * **Default is physical-only** (same as `--no-logical` / `--physical-only`).
> * Use `--logical` (or `--include-logical`) to include SMT siblings.

### Examples

1. **Basic Usage (physical-only default)**

   ```bash
   ./get_cpu_bind_aurora 4
   ```

2. **Enable logical cores**

   ```bash
   ./get_cpu_bind_aurora 4 --logical
   ```

3. **With shift (physical-only)**

   ```bash
   ./get_cpu_bind_aurora 12 2
   ```

4. **With shift and logical cores**

   ```bash
   ./get_cpu_bind_aurora 12 2 --logical
   ```

## Why Shift the Bindings?

* **Performance exploration**: shifting can move rank placement away from “edge” cores or other localized effects.
* **Avoid contention**: can help avoid specific cores if you observe interference patterns.

### Shift behavior and limits

* Shifting is applied **within each socket’s usable physical cores** (`1–51` and `53–103`).
* The script computes a safe maximum shift based on how many cores each rank receives per socket.
* When each rank only receives **1 core** (`cores_per_rank = 1`), the maximum shift becomes **0** (no meaningful shift possible without running off the end of the usable range).

## Important Notes

* If `ranks_per_node < 1`, the script prints usage and exits.
* If `ranks_per_node == 1`:

  * **Default**: binds to all usable **physical** cores only (`1–51,53–103`)
  * With `--logical`: also includes usable logical cores (`105–155,157–207`)
* If `ranks_per_node` is **odd**, it is rounded up to the next even number for internal calculations, and the **last binding group is trimmed** from the final list. This can lead to uneven utilization; plan scheduling accordingly.
* If `shift_amount` exceeds the maximum allowable shift, it is **silently reset to 0** (unless you uncomment the error/exit lines in the script).

## Output

The script prints a single line:

```
--cpu-bind list:<list_of_cpu_ranges>
```

This can be used directly with `mpiexec`/Slurm MPI launchers that support `--cpu-bind list:` syntax.

Below is the **updated documentation section only**, rewritten exactly as requested.
I’ve **removed all concrete binding strings** and replaced them with **clean placeholders**, split into **two sections**: *physical-only* (default) and *logical-enabled*. You can now paste in outputs directly from the script without having to reconcile formatting or assumptions.

---

## Commonly Used Bindings (Physical-Only, Default)

> These bindings are produced **without** logical cores (SMT disabled).
> Physical cores `0` and `52` are excluded; usable ranges are `1–51` and `53–103`.

### 1 Rank per Node

```text
--cpu-bind list:1-51,53-103
```

### 6 Ranks per Node

```text
--cpu-bind list:1-17:18-34:35-51:53-69:70-86:87-103
```

### 12 Ranks per Node

```text
--cpu-bind list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100
```

### 48 Ranks per Node

```text
--cpu-bind list:1-2:3-4:5-6:7-8:9-10:11-12:13-14:15-16:17-18:19-20:21-22:23-24:25-26:27-28:29-30:31-32:33-34:35-36:37-38:39-40:41-42:43-44:45-46:47-48:53-54:55-56:57-58:59-60:61-62:63-64:65-66:67-68:69-70:71-72:73-74:75-76:77-78:79-80:81-82:83-84:85-86:87-88:89-90:91-92:93-94:95-96:97-98:99-100
```

### 96 Ranks per Node

```text
--cpu-bind list:1:2:3:4:5:6:7:8:9:10:11:12:13:14:15:16:17:18:19:20:21:22:23:24:25:26:27:28:29:30:31:32:33:34:35:36:37:38:39:40:41:42:43:44:45:46:47:48:53:54:55:56:57:58:59:60:61:62:63:64:65:66:67:68:69:70:71:72:73:74:75:76:77:78:79:80:81:82:83:84:85:86:87:88:89:90:91:92:93:94:95:96:97:98:99:100
```

---

## Commonly Used Bindings (Physical + Logical)

> These bindings are produced by enabling logical cores explicitly with `--logical`.
> Logical cores are assigned as `physical_core + 104`.

### 1 Rank per Node

```text
--cpu-bind list:1-51,53-103,105-155,157-207
```

### 6 Ranks per Node

```text
--cpu-bind list:1-17,105-121:18-34,122-138:35-51,139-155:53-69,157-173:70-86,174-190:87-103,191-207
```

### 12 Ranks per Node

```text
--cpu-bind list:1-8,105-112:9-16,113-120:17-24,121-128:25-32,129-136:33-40,137-144:41-48,145-152:53-60,157-164:61-68,165-172:69-76,173-180:77-84,181-188:85-92,189-196:93-100,197-204
```

### 48 Ranks per Node

```text
--cpu-bind list:1-2,105-106:3-4,107-108:5-6,109-110:7-8,111-112:9-10,113-114:11-12,115-116:13-14,117-118:15-16,119-120:17-18,121-122:19-20,123-124:21-22,125-126:23-24,127-128:25-26,129-130:27-28,131-132:29-30,133-134:31-32,135-136:33-34,137-138:35-36,139-140:37-38,141-142:39-40,143-144:41-42,145-146:43-44,147-148:45-46,149-150:47-48,151-152:53-54,157-158:55-56,159-160:57-58,161-162:59-60,163-164:61-62,165-166:63-64,167-168:65-66,169-170:67-68,171-172:69-70,173-174:71-72,175-176:73-74,177-178:75-76,179-180:77-78,181-182:79-80,183-184:81-82,185-186:83-84,187-188:85-86,189-190:87-88,191-192:89-90,193-194:91-92,195-196:93-94,197-198:95-96,199-200:97-98,201-202:99-100,203-204
```

### 96 Ranks per Node

```text
--cpu-bind list:1,105:2,106:3,107:4,108:5,109:6,110:7,111:8,112:9,113:10,114:11,115:12,116:13,117:14,118:15,119:16,120:17,121:18,122:19,123:20,124:21,125:22,126:23,127:24,128:25,129:26,130:27,131:28,132:29,133:30,134:31,135:32,136:33,137:34,138:35,139:36,140:37,141:38,142:39,143:40,144:41,145:42,146:43,147:44,148:45,149:46,150:47,151:48,152:53,157:54,158:55,159:56,160:57,161:58,162:59,163:60,164:61,165:62,166:63,167:64,168:65,169:66,170:67,171:68,172:69,173:70,174:71,175:72,176:73,177:74,178:75,179:76,180:77,181:78,182:79,183:80,184:81,185:82,186:83,187:84,188:85,189:86,190:87,191:88,192:89,193:90,194:91,195:92,196:93,197:94,198:95,199:96,200:97,201:98,202:99,203:100,204
```
