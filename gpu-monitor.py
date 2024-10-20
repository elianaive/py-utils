import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pynvml
import psutil
import threading
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import subprocess
import re
import matplotlib.dates as mdates
import datetime

class GPUMonitor:
    def __init__(self, master):
        self.master = master
        master.title("Enhanced GPU Resource Monitor")
        master.geometry("1200x1200")

        pynvml.nvmlInit()
        self.handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # Assuming single GPU system

        self.data = {
            'time': [],
            'gpu_util': [],
            'mem_util': [],
            'power': [],
            'temp': [],
            'mem_used': [],
            'mem_free': [],
            'cuda_util': [],
            'mem_bandwidth': [],
            'pcie_bandwidth': [],
            'flops_per_watt': [],
            'throttling': []
        }

        self.max_clock_speed = self.get_max_clock_speed()

        self.create_widgets()
        self.update_thread = threading.Thread(target=self.update_stats, daemon=True)
        self.update_thread.start()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # Overview Tab
        overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(overview_frame, text="Overview")

        # System Info frame
        system_frame = ttk.Labelframe(overview_frame, text="System Information", bootstyle="info")
        system_frame.pack(fill=X, pady=(0, 10), padx=5)

        self.system_info_label = ttk.Label(system_frame, text="Loading system information...")
        self.system_info_label.pack(padx=5, pady=5, anchor='w')

        self.cuda_version_label = ttk.Label(system_frame, text="CUDA Version: ")
        self.cuda_version_label.pack(padx=5, pady=2, anchor='w')

        self.ecc_memory_label = ttk.Label(system_frame, text="ECC Memory: ")
        self.ecc_memory_label.pack(padx=5, pady=2, anchor='w')

        self.overall_health_label = ttk.Label(system_frame, text="Overall GPU Health: ")
        self.overall_health_label.pack(padx=5, pady=2, anchor='w')

        # Overview frame
        overview_inner_frame = ttk.Labelframe(overview_frame, text="GPU Overview", bootstyle="info")
        overview_inner_frame.pack(fill=X, pady=(0, 10), padx=5)

        self.memory_label = ttk.Label(overview_inner_frame, text="Memory Usage: ")
        self.memory_label.grid(row=0, column=0, sticky='w', padx=5, pady=2)

        self.utilization_label = ttk.Label(overview_inner_frame, text="GPU Utilization: ")
        self.utilization_label.grid(row=0, column=1, sticky='w', padx=5, pady=2)

        self.power_label = ttk.Label(overview_inner_frame, text="Power Usage: ")
        self.power_label.grid(row=1, column=0, sticky='w', padx=5, pady=2)

        self.temp_label = ttk.Label(overview_inner_frame, text="Temperature: ")
        self.temp_label.grid(row=1, column=1, sticky='w', padx=5, pady=2)

        self.clock_label = ttk.Label(overview_inner_frame, text="GPU Clock: ")
        self.clock_label.grid(row=2, column=0, sticky='w', padx=5, pady=2)

        self.memory_clock_label = ttk.Label(overview_inner_frame, text="Memory Clock: ")
        self.memory_clock_label.grid(row=2, column=1, sticky='w', padx=5, pady=2)

        self.cuda_util_label = ttk.Label(overview_inner_frame, text="CUDA Core Utilization: ")
        self.cuda_util_label.grid(row=3, column=0, sticky='w', padx=5, pady=2)

        self.mem_bandwidth_label = ttk.Label(overview_inner_frame, text="Memory Bandwidth: ")
        self.mem_bandwidth_label.grid(row=3, column=1, sticky='w', padx=5, pady=2)

        self.pcie_bandwidth_label = ttk.Label(overview_inner_frame, text="PCIe Bandwidth: ")
        self.pcie_bandwidth_label.grid(row=4, column=0, sticky='w', padx=5, pady=2)

        self.power_efficiency_label = ttk.Label(overview_inner_frame, text="Power Efficiency: ")
        self.power_efficiency_label.grid(row=4, column=1, sticky='w', padx=5, pady=2)

        self.gpu_warnings_label = ttk.Label(overview_inner_frame, text="GPU Warnings: ")
        self.gpu_warnings_label.grid(row=5, column=0, columnspan=2, sticky='w', padx=5, pady=2)

        # Top Tasks frame
        tasks_frame = ttk.Labelframe(overview_frame, text="Top 5 GPU Tasks", bootstyle="info")
        tasks_frame.pack(fill=X, pady=(0, 10), padx=5)

        self.tasks_tree = ttk.Treeview(tasks_frame, columns=('pid', 'name', 'type', 'gpu_memory'), show='headings', height=5, bootstyle="info")
        self.tasks_tree.heading('pid', text='PID')
        self.tasks_tree.heading('name', text='Name')
        self.tasks_tree.heading('type', text='Type')
        self.tasks_tree.heading('gpu_memory', text='GPU Memory')
        self.tasks_tree.pack(fill=X, padx=5, pady=5)

        # Graphs frame
        self.graphs_frame = ttk.Labelframe(overview_frame, text="Performance Graphs", bootstyle="info")
        self.graphs_frame.pack(fill=BOTH, expand=YES, pady=(0, 5), padx=5)

        self.fig = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graphs_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=YES, padx=5, pady=5)

        # All Tasks Tab
        all_tasks_frame = ttk.Frame(self.notebook)
        self.notebook.add(all_tasks_frame, text="All Tasks")

        self.all_tasks_tree = ttk.Treeview(all_tasks_frame, columns=('pid', 'name', 'type', 'gpu_memory'), show='headings', bootstyle="info")
        self.all_tasks_tree.heading('pid', text='PID')
        self.all_tasks_tree.heading('name', text='Name')
        self.all_tasks_tree.heading('type', text='Type')
        self.all_tasks_tree.heading('gpu_memory', text='GPU Memory')
        self.all_tasks_tree.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # Adjust graph layout when window is resized
        self.graphs_frame.bind("<Configure>", self.on_resize)
        time.sleep(1)
        self.update_graph()
        self.fig.autofmt_xdate()
        self.canvas.draw()
        #self.fig.tight_layout()

    def on_resize(self, event):
        # Update graph size when window is resized
        self.update_graph()

    def update_stats(self):
        while True:
            try:
                gpu_info = self.get_gpu_info()
                process_info = self.get_process_info()
                system_info = self.get_system_info()

                # Update system info
                self.system_info_label.config(text=system_info)
                
                # Update CUDA version
                try:
                    cuda_version = pynvml.nvmlSystemGetCudaDriverVersion()
                    cuda_version_str = f"{cuda_version // 1000}.{(cuda_version % 1000) // 10}"
                    self.cuda_version_label.config(text=f"CUDA Version: {cuda_version_str}")
                except pynvml.NVMLError as e:
                    print(f"Error getting CUDA version: {e}")
                    self.cuda_version_label.config(text="CUDA Version: Unknown")

                # Check ECC memory status if supported, otherwise show alternative info
                try:
                    ecc_mode = pynvml.nvmlDeviceGetEccMode(self.handle)
                    ecc_status = "Enabled" if ecc_mode[0] == pynvml.NVML_FEATURE_ENABLED else "Disabled"
                    self.ecc_memory_label.config(text=f"ECC Memory: {ecc_status}")
                except pynvml.NVMLError as e:
                    if str(e) == "Not Supported":
                        # ECC not supported, show memory type instead
                        try:
                            mem_info = pynvml.nvmlDeviceGetMemoryInfo(self.handle)
                            total_memory = mem_info.total / (1024**3)  # Convert to GB
                            self.ecc_memory_label.config(text=f"GPU Memory: {total_memory:.2f} GB")
                        except pynvml.NVMLError as mem_error:
                            print(f"Error getting memory info: {mem_error}")
                            self.ecc_memory_label.config(text="GPU Memory: Unknown")
                    else:
                        print(f"Error getting ECC memory status: {e}")
                        self.ecc_memory_label.config(text="ECC Memory: Unknown")

                # Determine overall health
                overall_health = self.determine_overall_health(gpu_info)
                self.overall_health_label.config(text=f"Overall GPU Health: {overall_health}")

                # Update labels with health status
                self.memory_label.config(text=f"Memory Usage: {gpu_info['memory_used']}/{gpu_info['memory_total']} MB ({gpu_info['memory_percent']}%) - {self.get_status(gpu_info['memory_percent'], [80, 95])}")
                self.utilization_label.config(text=f"GPU Utilization: {gpu_info['gpu_util']}% - {self.get_status(gpu_info['gpu_util'], [80, 95])}")
                self.power_label.config(text=f"Power Usage: {gpu_info['power_draw']}W / {gpu_info['power_limit']}W - {self.get_status(gpu_info['power_draw'] / gpu_info['power_limit'] * 100, [80, 95])}")
                self.temp_label.config(text=f"Temperature: {gpu_info['temperature']}°C - {self.get_status(gpu_info['temperature'], [70, 80])}")
                
                # Update GPU clock label
                clock_status = self.get_status(gpu_info['gpu_clock_percent'], [30, 10], reverse=True)
                clock_text = f"GPU Clock: {gpu_info['gpu_clock']} MHz ({gpu_info['gpu_clock_percent']:.1f}% of max)"
                if clock_status != "Critical":
                    clock_text += f" - {clock_status}"
                else:
                    clock_text += " - Idle"
                self.clock_label.config(text=clock_text)
                
                self.memory_clock_label.config(text=f"Memory Clock: {gpu_info['memory_clock']} MHz")
                self.cuda_util_label.config(text=f"CUDA Core Utilization: {gpu_info['cuda_util']}% - {self.get_status(gpu_info['cuda_util'], [80, 95])}")
                self.mem_bandwidth_label.config(text=f"Memory Bandwidth: {gpu_info['mem_bandwidth']:.2f} GB/s")
                self.pcie_bandwidth_label.config(text=f"PCIe Bandwidth: {gpu_info['pcie_bandwidth']:.2f} GB/s - {self.get_status(gpu_info['pcie_bandwidth'], [10, 5], reverse=True)}")
                self.power_efficiency_label.config(text=f"Power Efficiency: {gpu_info['flops_per_watt']:.2f} GFLOPS/W")

                # Update GPU warnings
                warnings = self.get_gpu_warnings(gpu_info)
                self.gpu_warnings_label.config(text=f"GPU Warnings: {', '.join(warnings) if warnings else 'None'}")

                # Update data for graphs
                current_time = time.time()
                self.data['time'].append(current_time)
                self.data['gpu_util'].append(gpu_info['gpu_util'])
                self.data['mem_util'].append(gpu_info['memory_percent'])
                self.data['power'].append(gpu_info['power_draw'])
                self.data['temp'].append(gpu_info['temperature'])
                self.data['mem_used'].append(gpu_info['memory_used'])
                self.data['mem_free'].append(gpu_info['memory_total'] - gpu_info['memory_used'])
                self.data['cuda_util'].append(gpu_info['cuda_util'])
                self.data['mem_bandwidth'].append(gpu_info['mem_bandwidth'])
                self.data['pcie_bandwidth'].append(gpu_info['pcie_bandwidth'])
                self.data['flops_per_watt'].append(gpu_info['flops_per_watt'])
                self.data['throttling'].append(1 if gpu_info['is_throttling'] else 0)

                # Keep only last 5 minutes of data
                for key in self.data:
                    self.data[key] = self.data[key][-300:]

                self.update_graph()
                self.update_top_tasks(process_info)
                self.update_all_tasks(process_info)

            except Exception as e:
                print(f"Unexpected error in update_stats: {e}")
                import traceback
                traceback.print_exc()

            time.sleep(1)  # Update every second

    def get_gpu_info(self):
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total,utilization.gpu,power.draw,power.limit,temperature.gpu,clocks.sm,clocks.mem,utilization.memory,pcie.link.gen.current,pcie.link.width.current', '--format=csv,noheader,nounits'], capture_output=True, text=True, check=True)
            values = result.stdout.strip().split(', ')
            
            if len(values) != 11:
                raise ValueError(f"Expected 11 values from nvidia-smi, got {len(values)}")

            memory_used = int(values[0])
            memory_total = int(values[1])
            memory_percent = round((memory_used / memory_total) * 100, 2)

            # Calculate memory bandwidth (simplified estimation)
            mem_clock = int(values[7])  # MHz
            mem_width = 384  # Assuming a 384-bit memory interface, adjust as needed
            mem_bandwidth = (mem_clock * 2 * mem_width) / 8 / 1000  # GB/s

            # Calculate PCIe bandwidth (simplified estimation)
            pcie_gen = int(values[9])
            pcie_width = int(values[10])
            pcie_bandwidth = pcie_gen * pcie_width * 0.985  # GB/s

            # Estimate FLOPS (very rough estimation, adjust based on your GPU model)
            cuda_cores = 10496  # Example for RTX 3090, adjust for your GPU
            gpu_clock = int(values[6])  # MHz
            flops = (cuda_cores * gpu_clock * 2) / 1e6  # GFLOPS

            # Calculate FLOPS/Watt
            power_draw = float(values[3])
            flops_per_watt = flops / power_draw if power_draw > 0 else 0

            # Calculate GPU clock percentage
            gpu_clock_percent = (gpu_clock / self.max_clock_speed) * 100 if self.max_clock_speed > 0 else 0

            return {
                'memory_used': memory_used,
                'memory_total': memory_total,
                'memory_percent': memory_percent,
                'gpu_util': int(values[2]),
                'power_draw': float(values[3]),
                'power_limit': float(values[4]),
                'temperature': int(values[5]),
                'gpu_clock': gpu_clock,
                'gpu_clock_percent': gpu_clock_percent,
                'memory_clock': int(values[7]),
                'cuda_util': int(values[2]),  # Assuming CUDA utilization is same as GPU utilization
                'mem_util': int(values[8]),  # Memory controller utilization
                'mem_bandwidth': round(mem_bandwidth, 2),
                'pcie_bandwidth': round(pcie_bandwidth, 2),
                'flops_per_watt': round(flops_per_watt, 2),
                'is_throttling': int(values[5]) > 80  # Assuming throttling occurs above 80°C
            }
        except subprocess.CalledProcessError as e:
            print(f"Error running nvidia-smi: {e}")
            print(f"nvidia-smi output: {e.output}")
        except ValueError as e:
            print(f"Error parsing nvidia-smi output: {e}")
        except Exception as e:
            print(f"Unexpected error in get_gpu_info: {e}")
        
        # Return default values if any error occurs
        return {
            'memory_used': 0,
            'memory_total': 1,
            'memory_percent': 0,
            'gpu_util': 0,
            'power_draw': 0,
            'power_limit': 1,
            'temperature': 0,
            'gpu_clock': 0,
            'gpu_clock_percent': 0,
            'memory_clock': 0,
            'cuda_util': 0,
            'mem_util': 0,
            'mem_bandwidth': 0,
            'pcie_bandwidth': 0,
            'flops_per_watt': 0,
            'is_throttling': False
        }

    def get_process_info(self):
        try:
            result = subprocess.run(['nvidia-smi', '-q', '-d', 'PIDS'], capture_output=True, text=True, check=True)
            output = result.stdout

            processes = []
            current_process = {}
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith("Process ID"):
                    if current_process:
                        processes.append(current_process)
                    current_process = {'pid': int(line.split()[-1])}
                elif line.startswith("Type"):
                    current_process['type'] = line.split()[-1]
                elif line.startswith("Name"):
                    current_process['name'] = ' '.join(line.split()[2:])
                elif line.startswith("Used GPU Memory"):
                    mem_str = line.split(':')[-1].strip()
                    if mem_str == 'N/A':
                        current_process['gpu_memory'] = 'N/A'
                    else:
                        match = re.search(r'\d+', mem_str)
                        if match:
                            current_process['gpu_memory'] = int(match.group())
                        else:
                            current_process['gpu_memory'] = 'N/A'

            if current_process:
                processes.append(current_process)

            return processes
        except subprocess.CalledProcessError as e:
            print(f"Error running nvidia-smi for process info: {e}")
            print(f"nvidia-smi output: {e.output}")
        except Exception as e:
            print(f"Unexpected error in get_process_info: {e}")
        
        return []
    
    def get_max_clock_speed(self):
        try:
            # Get the maximum clock speed of the GPU
            max_clock = pynvml.nvmlDeviceGetMaxClockInfo(self.handle, pynvml.NVML_CLOCK_GRAPHICS)
            return max_clock
        except pynvml.NVMLError as e:
            print(f"Error getting max clock speed: {e}")
            return 1500  # Default to a common max clock speed if unable to fetch

    def get_system_info(self):
        try:
            gpu_name = pynvml.nvmlDeviceGetName(self.handle)
            driver_version = pynvml.nvmlSystemGetDriverVersion()
            cuda_version = pynvml.nvmlSystemGetCudaDriverVersion()

            # Handle potential bytes objects
            gpu_name = gpu_name.decode('utf-8') if isinstance(gpu_name, bytes) else gpu_name
            driver_version = driver_version.decode('utf-8') if isinstance(driver_version, bytes) else driver_version

            # CUDA version is typically returned as an integer
            cuda_version_major = cuda_version // 1000
            cuda_version_minor = (cuda_version % 1000) // 10

            return f"GPU: {gpu_name} | Driver: {driver_version} | CUDA: {cuda_version_major}.{cuda_version_minor}"
        except pynvml.NVMLError as e:
            print(f"NVML Error in get_system_info: {e}")
        except Exception as e:
            print(f"Unexpected error in get_system_info: {e}")
        
        return "Unable to retrieve system information"

    def get_status(self, value, thresholds, reverse=False):
        if isinstance(value, (int, float)):
            if reverse:
                if value > thresholds[0]:
                    return "OK"
                elif value > thresholds[1]:
                    return "Warning"
                else:
                    return "Critical"
            else:
                if value < thresholds[0]:
                    return "OK"
                elif value < thresholds[1]:
                    return "Warning"
                else:
                    return "Critical"
        return "Unknown"

    def determine_overall_health(self, gpu_info):
        critical_count = 0
        warning_count = 0
        
        checks = [
            (gpu_info['temperature'], [70, 80]),
            (gpu_info['memory_percent'], [80, 95]),
            (gpu_info['power_draw'] / gpu_info['power_limit'] * 100, [80, 95]),
            (gpu_info['gpu_clock_percent'], [30, 10], True),  # Changed from absolute clock to percentage
            (gpu_info['pcie_bandwidth'], [10, 5], True)
        ]
        
        for value, thresholds, *args in checks:
            status = self.get_status(value, thresholds, *args)
            if status == "Critical" and not (value == checks[3][0] and value < checks[3][1][1]):  # Don't count low GPU clock as critical
                critical_count += 1
            elif status == "Warning":
                warning_count += 1
        
        if critical_count > 0:
            return "Poor"
        elif warning_count > 1:
            return "Fair"
        else:
            return "Good"

    def get_gpu_warnings(self, gpu_info):
        warnings = []
        if gpu_info['temperature'] > 80:
            warnings.append("High temperature")
        if gpu_info['memory_percent'] > 95:
            warnings.append("High memory usage")
        if gpu_info['power_draw'] / gpu_info['power_limit'] > 0.95:
            warnings.append("High power usage")
        if gpu_info['gpu_clock_percent'] < 10 and gpu_info['gpu_util'] > 50:
            warnings.append("Low GPU clock while under load")
        if gpu_info['pcie_bandwidth'] < 5:
            warnings.append("Low PCIe bandwidth")
        return warnings

    def update_graph(self):
        self.fig.clear()

        # Get the current size of the graphs frame
        width = self.graphs_frame.winfo_width()
        height = self.graphs_frame.winfo_height()

        # Update the figure size
        self.fig.set_size_inches(width / self.fig.dpi, height / self.fig.dpi)

        # Set the background color to match the cyborg theme
        self.fig.patch.set_facecolor('#060606')

        # Create a 3x2 grid of subplots
        gs = self.fig.add_gridspec(3, 2, wspace=0.3, hspace=0.4)

        # Common style for all subplots
        plot_style = {
            'facecolor': '#222222',
        }

        ax1 = self.fig.add_subplot(gs[0, 0], **plot_style)
        ax2 = self.fig.add_subplot(gs[0, 1], **plot_style)
        ax3 = self.fig.add_subplot(gs[1, 0], **plot_style)
        ax4 = self.fig.add_subplot(gs[1, 1], **plot_style)
        ax5 = self.fig.add_subplot(gs[2, 0], **plot_style)
        ax6 = self.fig.add_subplot(gs[2, 1], **plot_style)

        # Convert timestamp to datetime
        times = [datetime.datetime.fromtimestamp(t) for t in self.data['time']]

        ax1.plot(times, self.data['gpu_util'], '-', color='#00bc8c')
        ax1.plot(times, self.data['cuda_util'], '-', color='#3498db')
        ax1.set_ylim(0, 100)
        ax1.set_ylabel('Utilization %', color='#ffffff')
        ax1.set_title('GPU Utilization', color='#ffffff')

        ax2.plot(times, self.data['power'], '-', color='#e74c3c')
        ax2.set_ylabel('Power (W)', color='#ffffff')
        ax2.set_title('Power Usage', color='#ffffff')

        ax3.plot(times, self.data['mem_bandwidth'], '-', color='#f39c12')
        ax3.set_ylabel('GB/s', color='#ffffff')
        ax3.set_title('Memory Bandwidth', color='#ffffff')

        ax4.plot(times, self.data['pcie_bandwidth'], '-', color='#2ecc71')
        ax4.set_ylabel('GB/s', color='#ffffff')
        ax4.set_title('PCIe Bandwidth', color='#ffffff')

        ax5.plot(times, self.data['flops_per_watt'], '-', color='#9b59b6')
        ax5.set_ylabel('GFLOPS/W', color='#ffffff')
        ax5.set_title('Power Efficiency', color='#ffffff')

        ax6.plot(times, self.data['temp'], '-', color='#e67e22')
        ax6.set_ylabel('Temperature (°C)', color='#ffffff')
        ax6.set_title('GPU Temperature', color='#ffffff')

        # Add throttling indicator
        ax6_twin = ax6.twinx()
        ax6_twin.fill_between(times, self.data['throttling'], alpha=0.3, color='red')
        ax6_twin.set_ylim(0, 1)
        ax6_twin.set_yticks([])

        for ax in [ax1, ax2, ax3, ax4, ax5, ax6, ax6_twin]:
            ax.tick_params(colors='#ffffff')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            for spine in ax.spines.values():
                spine.set_edgecolor('#444444')
                spine.set_linewidth(0.5)

        #self.fig.tight_layout()
        self.fig.autofmt_xdate()
        self.canvas.draw()

    def update_top_tasks(self, processes):
        self.tasks_tree.delete(*self.tasks_tree.get_children())
        sorted_processes = sorted(processes, 
                                  key=lambda x: int(x['gpu_memory']) if x['gpu_memory'] != 'N/A' else -1, 
                                  reverse=True)
        for process in sorted_processes[:5]:
            self.tasks_tree.insert('', 'end', values=(
                process['pid'],
                process['name'],
                process['type'],
                process['gpu_memory']
            ))

    def update_all_tasks(self, processes):
        self.all_tasks_tree.delete(*self.all_tasks_tree.get_children())
        for process in processes:
            self.all_tasks_tree.insert('', 'end', values=(
                process['pid'],
                process['name'],
                process['type'],
                process['gpu_memory']
            ))

    def __del__(self):
        pynvml.nvmlShutdown()

if __name__ == "__main__":
    root = ttk.Window(themename="cyborg")
    gpu_monitor = GPUMonitor(root)
    root.mainloop()