import boto3

from loguru import logger
from .vpc import VPC
from .ec2 import EC2
from client_locator import EC2Client, config


def init_vpc(vpc_cidr, vpc_name):

    return vpc_id


def init_igw(vpc_id):
    # Erstelle IGW
    igw_response = vpc.create_internet_gateway()

    igw_id = igw_response["InternetGateway"]["InternetGatewayId"]

    vpc.attach_igw_to_vpc(vpc_id, igw_id)


def init_subnets(
    vpc_id,
    igw_id,
    private_subnet_cidr,
    public_subnet_tag,
    public_subnet_cidr,
    private_subnet_tag,
):
    # Erstelle public subnet
    public_subnet_response = vpc.create_subnet(vpc_id, private_subnet_cidr)

    public_subnet_id = public_subnet_response["Subnet"]["SubnetId"]

    logger.info(f"Subnet wurde erstellt für VPC: {vpc_id} : {public_subnet_response}")

    # Tagge Public Subnet
    vpc.add_name_tag(public_subnet_id, public_subnet_tag)

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
    private_subnet_response = vpc.create_subnet(vpc_id, public_subnet_cidr)
    private_subnet_id = private_subnet_response["Subnet"]["SubnetId"]

    logger.info(f"Private subnet {private_subnet_id} für VPC {vpc_id} wurde erstellt")

    # Tagge private subnet
    vpc.add_name_tag(private_subnet_id, private_subnet_tag)


def init_secgroup(
    public_security_group_name,
    public_security_group_description,
    vpc_id,
    ip_permissions_inbound_public,
    ip_permissions_outbound_public,
    private_security_group_name,
    private_security_group_description,
    ip_permissions_inbound_private,
    ip_permissions_outbound_private,
):

    # Erstelle Security Groups
    """ PUBLIC """
    public_security_group_response = ec2.create_security_group(
        public_security_group_name, public_security_group_description, vpc_id
    )

    public_security_group_id = public_security_group_response["GroupId"]

    # Füge ein- und ausgehende rules hinzu für Public Security Group
    ec2.add_inbound_rule_to_sg(public_security_group_id, ip_permissions_inbound_public)
    ec2.add_outbound_rule_to_sg(
        public_security_group_id, ip_permissions_outbound_public
    )

    """ PRIVATE """
    private_security_group_response = ec2.create_security_group(
        private_security_group_name, private_security_group_description, vpc_id
    )
    private_security_group_id = private_security_group_response["GroupId"]

    # Füge ein- und ausgehende rules hinzu für Private Security Group
    ec2.add_inbound_rule_to_sg(
        private_security_group_id, ip_permissions_inbound_private
    )
    ec2.add_outbound_rule_to_sg(
        private_security_group_id, ip_permissions_outbound_private
    )

    logger.info(
        f"Ein- und Ausgehende Regeln wurden hinzugefügt für {public_security_group_name}"
    )


def create_priv_key(key_pair_name_private):
    key_pair_private_response = ec2.create_key_pair(key_pair_name_private)
    logger.info(f"Key: {key_pair_private_response}")
    f = open("privkey", "w")
    f.write(key_pair_private_response)
    f.close()
