# AWS Network Topology Visualizer

This project provides a Python script that visualizes your AWS network topology, including VPCs, subnets, route tables, network ACLs, network interfaces, and VPC endpoints.

## Description

The AWS Network Topology Visualizer fetches data about your AWS network resources using the boto3 library and creates an interactive visualization using the NetworkX and Pyvis libraries. The resulting HTML file provides a graphical representation of your network topology, allowing for easy exploration and understanding of your AWS network structure.

## Features

- Fetches AWS network data using boto3
- Visualizes VPCs, subnets, route tables, network ACLs, network interfaces, and VPC endpoints
- Provides an interactive HTML output with draggable nodes, zoom, and pan capabilities
- Displays detailed information about each network component on hover

## Prerequisites

- Python 3.6 or higher
- AWS CLI configured with appropriate credentials
- Required Python libraries: boto3, networkx, pyvis

## Installation

1. Clone this repository:
git clone https://github.com/lopmoris/aws-network-visualizer.git
cd aws-network-visualizer

2. Install the required Python libraries:

pip install -r requirements.txt

## Usage

### Running from your local laptop

1. Ensure your AWS CLI is configured with the appropriate credentials:

aws configure

2. Run the script:

python aws_network_visualizer.py output.html

3. Open the generated `output.html` file in a web browser to view the visualization.

### Running from AWS CloudShell

1. Upload the `aws_network_visualizer.py` and `requirements.txt` files to your CloudShell environment.

2. Install the required Python libraries:

pip install -r requirements.txt --user

3. Run the script:

python aws_network_topology_visualizer.py output.html

4. Download the generated `output.html` file from CloudShell to your local machine and open it in a web browser.

## Notes

- Ensure you have the necessary permissions to describe VPCs, subnets, route tables, network ACLs, network interfaces, and VPC endpoints in your AWS account.
- The script uses your default AWS region. To visualize resources in a different region, set the `AWS_DEFAULT_REGION` environment variable before running the script.

## Contributing

Contributions to improve the project are welcome. Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
