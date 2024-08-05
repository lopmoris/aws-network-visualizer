import boto3
from botocore.exceptions import ClientError
import networkx as nx
from pyvis.network import Network
import sys

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

    # Get VPCs
    try:
        vpcs = ec2_client.describe_vpcs()
        topology["vpcs"] = vpcs.get("Vpcs", [])
    except ClientError as e:
        print(f"Error describing VPCs: {e}", file=sys.stderr)

    # Get Subnets
    try:
        subnets = ec2_client.describe_subnets()
        topology["subnets"] = subnets.get("Subnets", [])
    except ClientError as e:
        print(f"Error describing Subnets: {e}", file=sys.stderr)

    # Get Route Tables
    try:
        route_tables = ec2_client.describe_route_tables()
        topology["route_tables"] = route_tables.get("RouteTables", [])
    except ClientError as e:
        print(f"Error describing Route Tables: {e}", file=sys.stderr)

    # Get Network ACLs
    try:
        network_acls = ec2_client.describe_network_acls()
        topology["network_acls"] = network_acls.get("NetworkAcls", [])
    except ClientError as e:
        print(f"Error describing Network ACLs: {e}", file=sys.stderr)

    # Get Network Interfaces
    try:
        network_interfaces = ec2_client.describe_network_interfaces()
        topology["network_interfaces"] = network_interfaces.get("NetworkInterfaces", [])
    except ClientError as e:
        print(f"Error describing Network Interfaces: {e}", file=sys.stderr)

    # Get VPC Endpoints
    try:
        vpc_endpoints = ec2_client.describe_vpc_endpoints()
        topology["vpc_endpoints"] = vpc_endpoints.get("VpcEndpoints", [])
    except ClientError as e:
        print(f"Error describing VPC Endpoints: {e}", file=sys.stderr)

    return topology

def create_graph(topology):
    G = nx.Graph()

    # Add VPCs
    for vpc in topology['vpcs']:
        vpc_id = vpc['VpcId']
        tooltip = f"VPC: {vpc_id}\nCIDR: {vpc['CidrBlock']}\nState: {vpc['State']}\nDHCP Options: {vpc['DhcpOptionsId']}"
        G.add_node(vpc_id, title=tooltip, group='vpc')

    # Add Subnets
    for subnet in topology['subnets']:
        subnet_id = subnet['SubnetId']
        vpc_id = subnet['VpcId']
        tooltip = f"Subnet: {subnet_id}\nCIDR: {subnet['CidrBlock']}\nAZ: {subnet['AvailabilityZone']}\nState: {subnet['State']}"
        G.add_node(subnet_id, title=tooltip, group='subnet')
        G.add_edge(vpc_id, subnet_id)

    # Add Route Tables
    for rt in topology['route_tables']:
        rt_id = rt['RouteTableId']
        vpc_id = rt['VpcId']
        routes = "\n".join([f"Destination: {r.get('DestinationCidrBlock', r.get('DestinationPrefixListId', 'N/A'))}, Target: {r.get('GatewayId', r.get('NatGatewayId', r.get('NetworkInterfaceId', 'N/A')))}" for r in rt['Routes']])
        tooltip = f"Route Table: {rt_id}\nVPC: {vpc_id}\nRoutes:\n{routes}"
        G.add_node(rt_id, title=tooltip, group='route_table')
        G.add_edge(vpc_id, rt_id)
        for assoc in rt.get('Associations', []):
            if 'SubnetId' in assoc:
                G.add_edge(rt_id, assoc['SubnetId'])

    # Add Network ACLs
    for nacl in topology['network_acls']:
        nacl_id = nacl['NetworkAclId']
        vpc_id = nacl['VpcId']
        tooltip = f"Network ACL: {nacl_id}\nVPC: {vpc_id}"
        G.add_node(nacl_id, title=tooltip, group='nacl')
        G.add_edge(vpc_id, nacl_id)
        for assoc in nacl.get('Associations', []):
            if 'SubnetId' in assoc:
                G.add_edge(nacl_id, assoc['SubnetId'])

    # Add Network Interfaces
    for eni in topology['network_interfaces']:
        eni_id = eni['NetworkInterfaceId']
        subnet_id = eni['SubnetId']
        private_ips = ", ".join([ip['PrivateIpAddress'] for ip in eni['PrivateIpAddresses']])
        public_ip = eni.get('Association', {}).get('PublicIp', 'N/A')
        tooltip = f"ENI: {eni_id}\nSubnet: {subnet_id}\nPrivate IPs: {private_ips}\nPublic IP: {public_ip}\nStatus: {eni['Status']}"
        G.add_node(eni_id, title=tooltip, group='eni')
        G.add_edge(subnet_id, eni_id)

    # Add VPC Endpoints
    for endpoint in topology['vpc_endpoints']:
        endpoint_id = endpoint['VpcEndpointId']
        vpc_id = endpoint['VpcId']
        tooltip = f"VPC Endpoint: {endpoint_id}\nType: {endpoint['VpcEndpointType']}\nService: {endpoint['ServiceName']}\nState: {endpoint['State']}"
        G.add_node(endpoint_id, title=tooltip, group='endpoint')
        G.add_edge(vpc_id, endpoint_id)

    return G

def visualize_graph(G, output_file):
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
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
        node['size'] = 20
        node['color'] = group_colors.get(node['group'], '#FFFFFF')

    net.toggle_physics(True)
    net.show_buttons(filter_=['physics'])
    net.save_graph(output_file)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python aws_network_topology_visualizer.py <output_html_file>")
        sys.exit(1)

    output_file = sys.argv[1]

    topology = get_network_topology()
    G = create_graph(topology)
    visualize_graph(G, output_file)
    print(f"Graph visualization saved to {output_file}")
