import boto3
import paramiko

from loguru import logger
from helpers.vpc import VPC
from helpers.ec2 import EC2
from client_locator import EC2Client, config
from helpers.ssh import AWSSSH

key = paramiko.RSAKey.from_private_key_file(config["core"]["key"])
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

ec2_client = EC2Client().get_client()
vpc = VPC(ec2_client)
ec2 = EC2(ec2_client)
ssh = AWSSSH(client)


def main():
    # ssh.exec_cmd(
    #     cmd="du -hcs .",
    #     key=key,
    #     host=config["core"]["server_ip"],
    #     user=config["core"]["username"],
    # )
    
    # Credential check
    logger.info(boto3.Session().get_credentials().access_key)
    logger.info(boto3.Session().get_credentials().secret_key)

    # Create VPC
    vpc_id = vpc.create_vpc(
        cidr=config["vpc"]["vpc_cidr_block"], vpc_name=config["vpc"]["vpc_name"]
    )

    # Create Public Subnet
    public_subnet_id = vpc.init_subnet(
        cidr=config["subnet"]["public"]["cidr"],
        tag=config["subnet"]["public"]["tag"],
    )

    # Create Private Subnet
    private_subnet_id = vpc.init_subnet(
        cidr=config["subnet"]["private"]["cidr"],
        tag=config["subnet"]["private"]["tag"],
    )

    # Create Internet Gateway and attach to public subnet
    igw_id = vpc.init_igw()

    # Create NAT Gateway
    nat_gateway_id = vpc.create_nat_gateway(public_subnet_id)

    # Create public route table
    public_route_table_id = vpc.init_route_table()

    # Create private route table
    private_route_table_id = vpc.init_route_table()

    # Attach IGW to public route table
    vpc.create_igw_route_to_route_table(
        rtb_id=public_route_table_id, igw_id=igw_id, cidrBlock="0.0.0.0/0"
    )

    # Attach public subnet with route table
    vpc.associate_subnet_with_route_table(
        subnet_id=public_subnet_id, rtb_id=public_route_table_id
    )

    # Attach public subnet with route table
    vpc.associate_subnet_with_route_table(
        subnet_id=private_subnet_id, rtb_id=private_route_table_id
    )

    # Allow auto assign IP for public subnet
    vpc.allow_auto_assign_ip_addresses_for_subnet(subnet_id=public_subnet_id)

    # Security Gruppen festlegen & Route Tables festlegen
    public_security_group = ec2.create_security_group(
        group_name=config["secgroup"]["public"]["name"],
        description=config["secgroup"]["public"]["description"],
        vpc_id=vpc_id,
    )
    private_security_group = ec2.create_security_group(
        group_name=config["secgroup"]["private"]["name"],
        description=config["secgroup"]["private"]["description"],
        vpc_id=vpc_id,
    )

    public_security_group_id = public_security_group["groupID"]
    private_security_group_id = private_security_group["groupID"]
    # Add Public IP_permission Rules
    ec2.add_inbound_rule_to_sg(
        public_security_group_id,
        config["secgroup"]["public"]["ip_permissions"]["inbound"],
    )
    ec2.add_inbound_rule_to_sg(
        public_security_group_id,
        config["secgroup"]["public"]["ip_permissions"]["outbound"],
    )

    # Add Public IP_permission Rules
    ec2.add_inbound_rule_to_sg(
        public_security_group_id,
        config["secgroup"]["private"]["ip_permissions"]["inbound"],
    )
    ec2.add_inbound_rule_to_sg(
        public_security_group_id,
        config["secgroup"]["private"]["ip_permissions"]["outbound"],
    )

    # Leader erstellen & starten
    ami_id = config["core"]["ami_id"]
    exec_cmd_master = """#!/bin/bash
                sudo curl -fsSL https://get.docker.com | bash
                sudo usermod -aG docker $USER
                docker swarm init
                """

    ec2.launch_ec2_instance(
        image_id=ami_id,
        key_name=config["core"]["key"],
        min_count=1,
        max_count=1,
        security_group_id=public_security_group_id,
        subnet_id=public_subnet_id,
        user_data=exec_cmd_master,
        instance_type=config["core"]["instance_type_master"],
    )

    logger.info(f"Starte Public EC2 Instanz AMI-Image {ami_id}")

    # SSH Keys für Zugriff auf Private Worker erstellen

    # Worker erstellen & starten & SSH Keys hinterlegen

    exec_cmd_worker = """#!/bin/bash
                  sudo curl -fsSL https://get.docker.com | bash
                  sudo usermod -aG docker $USER
                  """

    ec2.launch_ec2_instance(
        image_id=ami_id,
        key_name=config["core"]["key"],
        min_count=3,
        max_count=3,
        security_group_id=private_security_group_id,
        subnet_id=private_subnet_id,
        user_data=exec_cmd_master,
        instance_type=config["core"]["instance_type_master"],
    )

    logger.info(f"Starte Private EC2 Instanz AMI-Image {ami_id}")
    # ssh -i privkey ubuntu@ip docker swarm join-token worker | sed 1,2d | sed 2d

    # TODO: Alle IPs von Worker-Nodes herausfinden und Deploy-Command schreiben


if __name__ == "__main__":
    main()
