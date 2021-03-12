import boto3

from loguru import logger
from helpers.vpc import VPC
from helpers.ec2 import EC2
from client_locator import EC2Client, config


def main():
    # Credential check
    logger.info(boto3.Session().get_credentials().access_key)
    logger.info(boto3.Session().get_credentials().secret_key)

    # Erstelle VPC
    ec2_client = EC2Client().get_client()
    vpc = VPC(ec2_client)

    vpc_response = vpc.create_vpc(config["core"]["cidr_block"])

    if "pending" in vpc_response["Vpc"]["State"]:
        logger.info(f"VPC erstellt: {vpc_response}")
    else:
        logger.error(f"Fehler aufgetreten")

    # Tag zu VPC hinzufügen
    vpc_name = config["core"]["vpc_name_one"]
    vpc_id = vpc_response["Vpc"]["VpcId"]
    vpc.add_name_tag(vpc_id, vpc_name)

    logger.info(f"Füge {vpc_name} zu {vpc_id} hinzu")

    # Erstelle IGW
    igw_response = vpc.create_internet_gateway()

    igw_id = igw_response["InternetGateway"]["InternetGatewayId"]

    vpc.attach_igw_to_vpc(vpc_id, igw_id)

    # Erstelle public subnet
    public_subnet_response = vpc.create_subnet(
        vpc_id, config["core"]["public_subnet_cidr"]
    )

    public_subnet_id = public_subnet_response["Subnet"]["SubnetId"]

    logger.info(f"Subnet wurde erstellt für VPC: {vpc_id} : {public_subnet_response}")

    # Tagge Public Subnet
    vpc.add_name_tag(public_subnet_id, config["core"]["public_subnet_tag"])

    # Erstelle public route table
    public_route_table_response = vpc.create_public_route_table(vpc_id)

    rtb_id = public_route_table_response["RouteTable"]["RouteTableId"]

    # Füge IGW zu public route table hinzu
    vpc.create_igw_route_to_public_route_table(rtb_id, igw_id)

    # Verknüpfe Public Subnet mit Route Table
    vpc.associate_subnet_with_route_table(public_subnet_id, rtb_id)

    # Erlaube public ip addresse für subnet
    vpc.allow_auto_assign_ip_addresses_for_subnet(public_subnet_id)

    # Erstelle Private Subnet
    private_subnet_response = vpc.create_subnet(
        vpc_id, config["core"]["private_subnet_cidr"]
    )
    private_subnet_id = private_subnet_response["Subnet"]["SubnetId"]

    logger.info(f"Private subnet {private_subnet_id} für VPC {vpc_id} wurde erstellt")

    # Tagge private subnet
    vpc.add_name_tag(private_subnet_id, "Boto3-Private-Subnet")

    ec2 = EC2(ec2_client)

    # Erstelle Security Groups
    """ PUBLIC """
    public_security_group_name = config["core"]["public_security_group_name"]
    public_security_group_description = config["core"][
        "public_security_group_description"
    ]
    public_security_group_response = ec2.create_security_group(
        public_security_group_name, public_security_group_description, vpc_id
    )

    public_security_group_id = public_security_group_response["GroupId"]

    # Füge ein- und ausgehende rules hinzu für Public Security Group
    ec2.add_inbound_rule_to_sg(
        public_security_group_id, config["core"]["ip_permissions_inbound_public"]
    )
    ec2.add_outbound_rule_to_sg(
        public_security_group_id, config["core"]["ip_permissions_outbound_public"]
    )

    """ PRIVATE """
    private_security_group_name = config["core"]["private_security_group_name"]
    private_security_group_description = config["core"][
        "private_security_group_description"
    ]
    private_security_group_response = ec2.create_security_group(
        private_security_group_name, private_security_group_description, vpc_id
    )
    private_security_group_id = private_security_group_response["GroupId"]

    # Füge ein- und ausgehende rules hinzu für Private Security Group
    ec2.add_inbound_rule_to_sg(
        private_security_group_id, config["core"]["ip_permissions_inbound_private"]
    )
    ec2.add_outbound_rule_to_sg(
        private_security_group_id, config["core"]["ip_permissions_outbound_private"]
    )

    logger.info(
        f"Ein- und Ausgehende Regeln wurden hinzugefügt für {public_security_group_name}"
    )

    exec_cmd_master = """#!/bin/bash
                 sudo apt update && sudo apt upgrade -y
                 sudo curl -fsSL https://get.docker.com | bash
                 sudo usermod -aG docker $USER
                 """

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
        """""",
    )

    logger.info(f"Starte Private EC2 Instanz AMI-Image {ami_id}")


if __name__ == "__main__":
    main()
