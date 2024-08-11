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
        'subnet_public': 'icons/subnet-public-icon.png',
        'subnet_private': 'icons/subnet-private-icon.png',
        'route_table': 'icons/route-table-icon.png',
        'nacl': 'icons/nacl-icon.png',
        'eni': 'icons/eni-icon.png',
        'endpoint': 'icons/endpoint-icon.png'
    }

    def get_base64_encoded_image(image_path):
        with open(image_path, "rb") as image_file:
            return f"data:image/png;base64,{base64.b64encode(image_file.read()).decode('utf-8')}"

    def get_resource_name(resource, key='Tags'):
        tags = resource.get(key, [])
        for tag in tags:
            if tag['Key'] == 'Name':
                return tag['Value']
        return None

    # Identify public subnets
    public_subnets = set()
    main_route_tables = {}
    for rt in topology['route_tables']:
        vpc_id = rt['VpcId']
        is_main = any(assoc.get('Main', False) for assoc in rt.get('Associations', []))
        has_igw = any(route.get('GatewayId', '').startswith('igw-') for route in rt.get('Routes', []))
        
        if is_main:
            main_route_tables[vpc_id] = {'route_table_id': rt['RouteTableId'], 'has_igw': has_igw}
        
        if has_igw:
            for assoc in rt.get('Associations', []):
                if 'SubnetId' in assoc:
                    public_subnets.add(assoc['SubnetId'])

    for vpc in topology['vpcs']:
        vpc_id = vpc['VpcId']
        vpc_name = get_resource_name(vpc) or vpc_id
        G.add_node(vpc_id, title=f"VPC: {vpc_name}\nID: {vpc_id}\nCIDR: {vpc['CidrBlock']}", 
                   group='vpc', image=get_base64_encoded_image(icon_paths['vpc']), size=25, label=vpc_name)

    for subnet in topology['subnets']:
        subnet_id = subnet['SubnetId']
        vpc_id = subnet['VpcId']
        subnet_name = get_resource_name(subnet) or subnet_id
        
        # Check if subnet is public (either by specific route table or VPC's main route table)
        is_public = subnet_id in public_subnets or (vpc_id in main_route_tables and main_route_tables[vpc_id]['has_igw'])
        
        subnet_type = 'subnet_public' if is_public else 'subnet_private'
        G.add_node(subnet_id, title=f"Subnet: {subnet_name}\nID: {subnet_id}\nCIDR: {subnet['CidrBlock']}\nType: {'Public' if is_public else 'Private'}", 
                   group=subnet_type, image=get_base64_encoded_image(icon_paths[subnet_type]), size=25, label=subnet_name)
        G.add_edge(vpc_id, subnet_id)

    for rt in topology['route_tables']:
        rt_id = rt['RouteTableId']
        vpc_id = rt['VpcId']
        rt_name = get_resource_name(rt) or rt_id
        routes = "\n".join([f"Destination: {r.get('DestinationCidrBlock', 'N/A')}, Target: {r.get('GatewayId', r.get('NatGatewayId', r.get('NetworkInterfaceId', 'N/A')))}" for r in rt['Routes']])
        G.add_node(rt_id, title=f"Route Table: {rt_name}\nID: {rt_id}\nRoutes:\n{routes}", 
                   group='route_table', image=get_base64_encoded_image(icon_paths['route_table']), size=20, label=rt_name)
        
        is_main = any(assoc.get('Main', False) for assoc in rt.get('Associations', []))
        if is_main:
            G.add_edge(rt_id, vpc_id)
        for assoc in rt.get('Associations', []):
            if 'SubnetId' in assoc:
                G.add_edge(rt_id, assoc['SubnetId'])

    for nacl in topology['network_acls']:
        nacl_id = nacl['NetworkAclId']
        vpc_id = nacl['VpcId']
        nacl_name = get_resource_name(nacl) or nacl_id
        G.add_node(nacl_id, title=f"Network ACL: {nacl_name}\nID: {nacl_id}", 
                   group='nacl', image=get_base64_encoded_image(icon_paths['nacl']), size=20, label=nacl_name)
        G.add_edge(vpc_id, nacl_id)
        for assoc in nacl.get('Associations', []):
            if 'SubnetId' in assoc:
                G.add_edge(nacl_id, assoc['SubnetId'])

    for eni in topology['network_interfaces']:
        eni_id = eni['NetworkInterfaceId']
        subnet_id = eni['SubnetId']
        eni_name = get_resource_name(eni, key='TagSet') or eni_id
        G.add_node(eni_id, title=f"ENI: {eni_name}\nID: {eni_id}\nPrivate IP: {eni['PrivateIpAddress']}", 
                   group='eni', image=get_base64_encoded_image(icon_paths['eni']), size=20, label=eni_name)
        G.add_edge(subnet_id, eni_id)

    for endpoint in topology['vpc_endpoints']:
        endpoint_id = endpoint['VpcEndpointId']
        vpc_id = endpoint['VpcId']
        endpoint_name = get_resource_name(endpoint) or endpoint_id
        G.add_node(endpoint_id, title=f"VPC Endpoint: {endpoint_name}\nID: {endpoint_id}\nType: {endpoint['VpcEndpointType']}", 
                   group='endpoint', image=get_base64_encoded_image(icon_paths['endpoint']), size=20, label=endpoint_name)
        G.add_edge(vpc_id, endpoint_id)
        if 'SubnetIds' in endpoint:
            for subnet_id in endpoint['SubnetIds']:
                G.add_edge(endpoint_id, subnet_id)

    return G

def visualize_graph(G, output_file):
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)

    # Customize node appearances
    group_colors = {
        'vpc': '#FF9900',
        'subnet_public': '#1EC9E8',
        'subnet_private': '#A4D4FF',
        'route_table': '#FF5252',
        'nacl': '#7B35BA',
        'eni': '#9CCC65',
        'endpoint': '#FB8C00'
    }

    for node in net.nodes:
        node['color'] = group_colors.get(node['group'], '#FFFFFF')
        node['shape'] = 'image'

    net.set_options("""
    var options = {
      "nodes": {
        "borderWidth": 2,
        "borderWidthSelected": 4,
        "color": {
          "border": "#222222",
          "background": "#ffffff"
        },
        "font": {"color": "#ffffff", "size": 12},
        "label": "label"
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
