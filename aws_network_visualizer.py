import boto3
from botocore.exceptions import ClientError
import networkx as nx
from pyvis.network import Network
import sys
import os
import base64

def get_aws_client(service_name):
    try:
        return boto3.client(service_name)
    except Exception as e:
        print(f"Error creating {service_name} client: {str(e)}", file=sys.stderr)
        return None

def get_network_topology():
    topology = {
        "vpcs": [],
        "subnets": [],
        "route_tables": [],
        "network_acls": [],
        "network_interfaces": [],
        "vpc_endpoints": []
    }

    ec2_client = get_aws_client('ec2')
    if not ec2_client:
        return topology

    try:
        topology["vpcs"] = ec2_client.describe_vpcs().get("Vpcs", [])
        topology["subnets"] = ec2_client.describe_subnets().get("Subnets", [])
        topology["route_tables"] = ec2_client.describe_route_tables().get("RouteTables", [])
        topology["network_acls"] = ec2_client.describe_network_acls().get("NetworkAcls", [])
        topology["network_interfaces"] = ec2_client.describe_network_interfaces().get("NetworkInterfaces", [])
        topology["vpc_endpoints"] = ec2_client.describe_vpc_endpoints().get("VpcEndpoints", [])
    except ClientError as e:
        print(f"Error fetching network data: {e}", file=sys.stderr)

    return topology

def create_graph(topology):
    G = nx.Graph()

    icon_paths = {
        'vpc': 'icons/vpc-icon.png',
        'subnet': 'icons/subnet-icon.png',
        'route_table': 'icons/route-table-icon.png',
        'nacl': 'icons/nacl-icon.png',
        'eni': 'icons/eni-icon.png',
        'endpoint': 'icons/endpoint-icon.png'
    }

    def get_base64_encoded_image(image_path):
        with open(image_path, "rb") as image_file:
            return f"data:image/png;base64,{base64.b64encode(image_file.read()).decode('utf-8')}"

    for vpc in topology['vpcs']:
        vpc_id = vpc['VpcId']
        G.add_node(vpc_id, title=f"VPC: {vpc_id}\nCIDR: {vpc['CidrBlock']}", group='vpc', image=get_base64_encoded_image(icon_paths['vpc']))

    for subnet in topology['subnets']:
        subnet_id = subnet['SubnetId']
        vpc_id = subnet['VpcId']
        G.add_node(subnet_id, title=f"Subnet: {subnet_id}\nCIDR: {subnet['CidrBlock']}", group='subnet', image=get_base64_encoded_image(icon_paths['subnet']))
        G.add_edge(vpc_id, subnet_id)

    for rt in topology['route_tables']:
        rt_id = rt['RouteTableId']
        vpc_id = rt['VpcId']
        routes = "\n".join([f"Destination: {r.get('DestinationCidrBlock', 'N/A')}, Target: {r.get('GatewayId', r.get('NatGatewayId', r.get('NetworkInterfaceId', 'N/A')))}" for r in rt['Routes']])
        G.add_node(rt_id, title=f"Route Table: {rt_id}\nRoutes:\n{routes}", group='route_table', image=get_base64_encoded_image(icon_paths['route_table']))
        G.add_edge(vpc_id, rt_id)

    for nacl in topology['network_acls']:
        nacl_id = nacl['NetworkAclId']
        vpc_id = nacl['VpcId']
        G.add_node(nacl_id, title=f"Network ACL: {nacl_id}", group='nacl', image=get_base64_encoded_image(icon_paths['nacl']))
        G.add_edge(vpc_id, nacl_id)

    for eni in topology['network_interfaces']:
        eni_id = eni['NetworkInterfaceId']
        subnet_id = eni['SubnetId']
        G.add_node(eni_id, title=f"ENI: {eni_id}\nPrivate IP: {eni['PrivateIpAddress']}", group='eni', image=get_base64_encoded_image(icon_paths['eni']))
        G.add_edge(subnet_id, eni_id)

    for endpoint in topology['vpc_endpoints']:
        endpoint_id = endpoint['VpcEndpointId']
        vpc_id = endpoint['VpcId']
        G.add_node(endpoint_id, title=f"VPC Endpoint: {endpoint_id}\nType: {endpoint['VpcEndpointType']}", group='endpoint', image=get_base64_encoded_image(icon_paths['endpoint']))
        G.add_edge(vpc_id, endpoint_id)

    return G

def visualize_graph(G, output_file):
    net = Network(height="100%", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)

    # Customize node appearances
    group_colors = {
        'vpc': '#FF9900',
        'subnet': '#1EC9E8',
        'route_table': '#FF5252',
        'nacl': '#7B35BA',
        'eni': '#9CCC65',
        'endpoint': '#FB8C00'
    }

    for node in net.nodes:
        node['size'] = 90
        node['color'] = group_colors.get(node['group'], '#FFFFFF')
        node['shape'] = 'image'

    net.set_options("""
    var options = {
      "nodes": {
        "borderWidth": 2,
        "borderWidthSelected": 4,
        "size": 90,
        "color": {
          "border": "#222222",
          "background": "#ffffff"
        },
        "font": {"color": "#ffffff"}
      },
      "edges": {
        "color": {"inherit": true},
        "smooth": false
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -2000,
          "centralGravity": 0.3,
          "springLength": 95,
          "springConstant": 0.04,
          "damping": 0.09,
          "avoidOverlap": 0.1
        },
        "maxVelocity": 50,
        "minVelocity": 0.1,
        "solver": "barnesHut",
        "stabilization": {
          "enabled": true,
          "iterations": 1000,
          "updateInterval": 100,
          "onlyDynamicEdges": false,
          "fit": true
        },
        "timestep": 0.5,
        "adaptiveTimestep": true
      }
    }
    """)

    net.save_graph(output_file)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python aws_network_topology_visualizer.py <output_html_file>")
        sys.exit(1)

    output_file = sys.argv[1]

    if not os.path.exists('icons'):
        print("Error: 'icons' directory not found. Please create it and add the necessary PNG icons.")
        sys.exit(1)

    topology = get_network_topology()
    G = create_graph(topology)
    visualize_graph(G, output_file)
    print(f"Graph visualization saved to {output_file}")
