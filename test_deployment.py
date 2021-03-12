import boto3

from loguru import logger
from helpers.helpers import *
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


    # Ein VPC erstellen
    vpc.create_vpc(config["core"]["cidr_block"], config["core"]["vpc_name_one"])


    # Public Subnet erstellen
    

    # Private Subnet erstellen


    # Erstelle public route table

    boto3.create_public_route_table(vpc_id)

    # Internet Gateway im Public Subnet erstellen und öffentliche IP festlegen
    igw_id = init_igw(vpc)


    # NAT Gateway erstellen


    # Security Gruppen festlegen & Root Tables festlegen



    # Leader erstellen & starten



    # SSH Keys für Zugriff auf Private Worker erstellen



    # Worker erstellen & starten & SSH Keys hinterlegen

    init_subnets(
        igw_id,
        config["core"]["public_subnet_cidr"],
        config["core"]["public_subnet_tag"],
        config["core"]["private_subnet_cidr"],
        config["subnet"]["private_subnet_tag"],
    )

    private_subnet_id = init_secgroup(
        config["core"]["public_security_group_name"],
        config["core"]["public_security_group_description"],
        vpc_id,
        config["core"]["ip_permissions_inbound_public"],
        config["core"]["ip_permissions_outbound_public"],
        config["core"]["private_security_group_name"],
        config["core"]["private_security_group_description"],
        config["core"]["ip_permissions_inbound_private"],
        config["core"]["ip_permissions_outbound_private"],
    )

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

    create_priv_key(config["core"]["key_pair_name_private"])

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
