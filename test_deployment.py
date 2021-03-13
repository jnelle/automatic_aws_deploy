import boto3

from loguru import logger
from helpers.vpc import VPC
from helpers.ec2 import EC2
from client_locator import EC2Client, config

ec2_client = EC2Client().get_client()
vpc = VPC(ec2_client)
ec2 = EC2(ec2_client)


def main():
    # Credential check
    logger.info(boto3.Session().get_credentials().access_key)
    logger.info(boto3.Session().get_credentials().secret_key)

    # Create VPC
    vpc.create_vpc(
        cidr=config["vpc"]["vpc_cidr_block"], vpc_name=config["vpc"]["vpc_name"]
    )

    # Create Public Subnet
    public_subnet_id = vpc.init_subnet(
        cidr=config["subnet"]["public_subnet_cidr"],
        tag=config["subnet"]["public_subnet_tag"],
    )

    # Create Private Subnet
    private_subnet_id = vpc.init_subnet(
        cidr=config["subnet"]["private_subnet_cidr"],
        tag=config["subnet"]["private_subnet_tag"],
    )

    # Create Internet Gateway and attach to public subnet
    igw_id = vpc.init_igw()

    # Create NAT Gateway
    nat_gateway_id = vpc.create_nat_gateway()

    # Create public route table
    public_route_table_id = vpc.init_route_table()

    # Create private route table
    private_route_table_id = vpc.init_route_table()

    # Attach IGW to public route table
    vpc.create_igw_route_to_public_route_table(
        rtb_id=public_route_table_id, igw_id=igw_id
    )

    # Attach public subnet with route table
    vpc.associate_subnet_with_route_table(
        subnet_id=public_subnet_id, rtb_id=public_route_table_id
    )

    # Allow auto assign IP for public subnet
    vpc.allow_auto_assign_ip_addresses_for_subnet(subnet_id=public_subnet_id)

    # Security Gruppen festlegen & Route Tables festlegen

    # Leader erstellen & starten

    # SSH Keys für Zugriff auf Private Worker erstellen

    # Worker erstellen & starten & SSH Keys hinterlegen

    exec_cmd_master = """#!/bin/bash
                  sudo curl -fsSL https://get.docker.com | bash
                 sudo usermod -aG docker $USER
                 docker swarm init
                 """

    exec_cmd_worker = """#!/bin/bash
                  sudo curl -fsSL https://get.docker.com | bash
                  sudo usermod -aG docker $USER
                  """

    # ssh -i privkey ubuntu@ip docker swarm join-token worker | sed 1,2d | sed 2d

    # ami_id = OS Image
    ami_id = config["core"]["ami_id"]  # Ubuntu Server 20.04 LTS

    # Starte Master EC2 Instanz
    ec2.launch_ec2_instance(
        ami_id,
        config["core"]["key_pair_name"],
        1,
        1,
        public_security_group_id,
        public_subnet_id,
        exec_cmd_master,
        config["core"]["instance_type_master"],
    )

    logger.info(f"Starte Public EC2 Instanz AMI-Image {ami_id}")

    # TODO: Alle IPs von Worker-Nodes herausfinden und Deploy-Command schreiben
    # Starte 3x Worker EC2 Instanzen
    ec2.launch_ec2_instance(
        ami_id,
        config["core"]["key_pair_name"],
        3,
        3,
        private_security_group_id,
        private_subnet_id,
        config["core"]["instance_type_worker"],
        exec_cmd_worker,
    )

    logger.info(f"Starte Private EC2 Instanz AMI-Image {ami_id}")


if __name__ == "__main__":
    main()
