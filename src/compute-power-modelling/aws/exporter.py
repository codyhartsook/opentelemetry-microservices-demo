#!/usr/bin/python

__author__ = "Cody Hartsook"
__copyright__ = "Cisco (c) 2022 - Cisco Innovation Labs"

__version__ = "1.0"
__status__ = "Development"

from model import Compute_Instance_Models
from prometheus_client import start_http_server, Gauge
from prometheus_api_client import PrometheusConnect
from kubernetes import client, config
import ipaddress
import re
import time
from os import getenv

prometheus_host = getenv('PROMETHEUS_HOST', 'localhost:9090')
prometheus_url = f'http://{prometheus_host}/'

class AWSEnergyPrometheusExporter(Compute_Instance_Models):
    def __init__(self, polling_interval_seconds=30, metric_name='node_power_usage'):
        Compute_Instance_Models.__init__(self)
        self.polling_interval_seconds = polling_interval_seconds
        self.exporter = Gauge(metric_name, 'latest node power usage in watts', ['node', 'resource'])
        self.__connect_to_prometheus()

    def __connect_to_prometheus(self, max_retries=3, retry_interval=5):

        for _ in range(max_retries):
            try:
                prom_client = PrometheusConnect(prometheus_url)
                ok = prom_client.check_prometheus_connection()
                if ok:
                    self.prom_client = prom_client
                    print('Connected to prometheus at {}'.format(prometheus_url))
                    return
            except:
                pass

            print('Retrying connection to Prometheus')
            time.sleep(retry_interval)
            continue
            
        raise Exception('Could not connect to Prometheus at {}'.format(prometheus_url))

    def run_metrics_loop(self):
        """Metrics fetching loop"""

        while True:
            self.fetch()
            time.sleep(self.polling_interval_seconds)

    def fetch(self):
        # get node cpu and memory usage from prometheus
        cluster_nodes_load = {}
        self.set_node_cpu_metrics_from_prometheus(cluster_nodes_load)
        self.set_node_memory_metrics_from_prometheus(cluster_nodes_load)
        self.set_node_machine_metadata(cluster_nodes_load)

        for node, metrics in cluster_nodes_load.items():
            # apply model to get power usage
            estimate = self.estimate_watts(metrics['machine_type'], metrics['cpu_load'], metrics['mem_load'])
            if estimate is None:
                print(f'Error: Could not estimate power usage.')
                return

            # export metrics to prometheus
            print(f'estimated power usage for {node} is {estimate} watts')
            node_addr = node.split(':')[0]

            self.exporter.labels(node=node_addr, resource='cpu').set(estimate['cpu_watts'])
            self.exporter.labels(node=node_addr, resource='mem').set(estimate['mem_watts'])

    def set_node_cpu_metrics_from_prometheus(self, instances):
        print('Fetching node metrics from prometheus at {}'.format(prometheus_url))

        # fetch instances from prometheus
        if len(instances) == 0:
            node_loads = self.prom_client.custom_query(query="node_load5")
            for node in node_loads:
                instances[node['metric']['instance']] = {}
        
        # fetch cpu load per instance
        for instance in instances:
            q = f'avg(node_load1{{instance="{instance}",job="node-exporter"}}) / count(count(node_cpu_seconds_total{{instance="{instance}",job="node-exporter"}}) by (cpu)) * 100'
            
            node_cpu_data = self.prom_client.custom_query(query=q)
            instances[instance]['cpu_load'] = float(node_cpu_data[0]['value'][1])

    def set_node_memory_metrics_from_prometheus(self, instances):
        for instance in instances:
            q = f'100 - (avg(node_memory_MemAvailable_bytes{{job="node-exporter", instance="{instance}"}}) / avg(node_memory_MemTotal_bytes{{job="node-exporter", instance="{instance}"}}) * 100)'

            node_mem_data = self.prom_client.custom_query(query=q)
            instances[instance]['mem_load'] = float(node_mem_data[0]['value'][1])

    def set_node_machine_metadata(self, instances):
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
            
        v1 = client.CoreV1Api()
        nodes = v1.list_node().items

        print('instances: {}'.format(instances))

        addr_mapping = {i.split(':')[0]:i for i in instances}
        for node in nodes:
            machine_type = self.extract_node_instance_type(node)
            if machine_type is None:
                print(f'Error: Could not find machine type for node {node.metadata.name}')
                continue

            region = self.extract_node_region(node)

            #ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', node.metadata.name.replace('-', '.'))
            ip = self.match_prom_ip_with_k8s_ip(node, addr_mapping)
            if ip is None:
                print(f'Error: Could not find IP for node {node.metadata.name}, {addr_mapping}')
                continue

            instances[addr_mapping[ip]]['machine_type'] = machine_type
            instances[addr_mapping[ip]]['region'] = region


    def match_prom_ip_with_k8s_ip(self, node, prom_reported_ips):
        # exact match between k8s node ip and prometheus reported ip
        ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', node.metadata.name.replace('-', '.'))
        if len(ip) == 0:
            return None

        if ip[0] in prom_reported_ips:
            return ip[0]

        # try to match prometheus reported ip with k8s node ip by subnet
        node_ip = ipaddress.ip_network(ip[0]+'/24', False) 
        for prom_ip in prom_reported_ips:
            if ipaddress.ip_address(prom_ip) in node_ip:
                return prom_ip

        return None

    def extract_node_instance_type(self, node):
        if 'node.kubernetes.io/instance-type' in node.metadata.labels:
            return node.metadata.labels['node.kubernetes.io/instance-type']
        elif 'beta.kubernetes.io/instance-type' in node.metadata.labels:
            return node.metadata.labels['beta.kubernetes.io/instance-type']
        return None

    def extract_node_region(self, node):
        if 'topology.kubernetes.io/region' in node.metadata.labels:
            return node.metadata.labels['topology.kubernetes.io/region']

        return ''
        
def main():
    polling_interval_seconds = int(getenv("POLLING_INTERVAL_SECONDS", "30"))
    exporter_port = int(getenv("EXPORTER_PORT", "9877"))
    metric_name = getenv("METRIC_NAME", "node_power_usage")

    power_metrics = AWSEnergyPrometheusExporter(
        metric_name=metric_name,
        polling_interval_seconds=polling_interval_seconds
    )

    start_http_server(exporter_port)
    power_metrics.run_metrics_loop()

if __name__ == '__main__':
    main()
