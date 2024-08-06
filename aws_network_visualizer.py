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

    # Fetch data for each resource type
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

    # Define AWS icon paths (PNG format)
    icon_paths = {
        'vpc': 'icons/vpc-icon.png',
        'subnet': 'icons/subnet-icon.png',
        'route_table': 'icons/route-table-icon.png',
        'nacl': 'icons/nacl-icon.png',
        'eni': 'icons/eni-icon.png',
        'endpoint': 'icons/endpoint-icon.png'
    }

    # Helper function to encode image to base64
    def get_base64_encoded_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    # Add nodes and edges
    for vpc in topology['vpcs']:
        vpc_id = vpc['VpcId']
        G.add_node(vpc_id, title=f"VPC: {vpc_id}\nCIDR: {vpc['CidrBlock']}", group='vpc', shape='image', image=get_base64_encoded_image(icon_paths['vpc']))

    for subnet in topology['subnets']:
        subnet_id = subnet['SubnetId']
        vpc_id = subnet['VpcId']
        G.add_node(subnet_id, title=f"Subnet: {subnet_id}\nCIDR: {subnet['CidrBlock']}", group='subnet', shape='image', image=get_base64_encoded_image(icon_paths['subnet']))
        G.add_edge(vpc_id, subnet_id)

    for rt in topology['route_tables']:
        rt_id = rt['RouteTableId']
        vpc_id = rt['VpcId']
        routes = "\n".join([f"Destination: {r.get('DestinationCidrBlock', 'N/A')}, Target: {r.get('GatewayId', r.get('NatGatewayId', r.get('NetworkInterfaceId', 'N/A')))}" for r in rt['Routes']])
        G.add_node(rt_id, title=f"Route Table: {rt_id}\nRoutes:\n{routes}", group='route_table', shape='image', image=get_base64_encoded_image(icon_paths['route_table']))
        G.add_edge(vpc_id, rt_id)

    for nacl in topology['network_acls']:
        nacl_id = nacl['NetworkAclId']
        vpc_id = nacl['VpcId']
        G.add_node(nacl_id, title=f"Network ACL: {nacl_id}", group='nacl', shape='image', image=get_base64_encoded_image(icon_paths['nacl']))
        G.add_edge(vpc_id, nacl_id)

    for eni in topology['network_interfaces']:
        eni_id = eni['NetworkInterfaceId']
        subnet_id = eni['SubnetId']
        G.add_node(eni_id, title=f"ENI: {eni_id}\nPrivate IP: {eni['PrivateIpAddress']}", group='eni', shape='image', image=get_base64_encoded_image(icon_paths['eni']))
        G.add_edge(subnet_id, eni_id)

    for endpoint in topology['vpc_endpoints']:
        endpoint_id = endpoint['VpcEndpointId']
        vpc_id = endpoint['VpcId']
        G.add_node(endpoint_id, title=f"VPC Endpoint: {endpoint_id}\nType: {endpoint['VpcEndpointType']}", group='endpoint', shape='image', image=get_base64_encoded_image(icon_paths['endpoint']))
        G.add_edge(vpc_id, endpoint_id)

    return G

def visualize_graph(G, output_file):
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)

    net.set_options("""
    var options = {
      "nodes": {
        "borderWidth": 2,
        "size": 30,
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
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.01,
          "springLength": 200,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": {"iterations": 150}
      }
    }
    """)

    net.save_graph(output_file)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python aws_network_topology_visualizer.py <output_html_file>")
        sys.exit(1)

    output_file = sys.argv[1]

    # Ensure the icons directory exists
    if not os.path.exists('icons'):
        print("Error: 'icons' directory not found. Please create it and add the necessary PNG icons.")
        sys.exit(1)

    topology = get_network_topology()
    G = create_graph(topology)
    visualize_graph(G, output_file)
    print(f"Graph visualization saved to {output_file}")
