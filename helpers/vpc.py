from loguru import logger


class VPC:
    def __init__(self, client):
        self._client = client
        """ :type : pyboto3.ec2 """

    def create_vpc(self, cidr):
        logger.info("Erstelle VPC...")
        return self._client.create_vpc(CidrBlock=cidr)

    def add_name_tag(self, resource_id, resource_name):
        logger.info(f"Füge {resource_name} tag zu {resource_id} hinzu")
        return self._client.create_tags(
            Resources=[resource_id], Tags=[{"Key": "Name", "Value": resource_name}]
        )

    def create_internet_gateway(self):
        logger.info("Erstelle Internet Gateway...")
        return self._client.create_internet_gateway()

    def attach_igw_to_vpc(self, vpc_id, igw_id):
        logger.info(f"Verknüpfe Internetgateway: {igw_id} zu VPC: {vpc_id}")
        return self._client.attach_internet_gateway(
            InternetGatewayId=igw_id, VpcId=vpc_id
        )

    def create_subnet(self, vpc_id, cidr_block):
        logger.info(f"Erstelle Subnet für VPC: {vpc_id} mit CIDR: {cidr_block}")
        return self._client.create_subnet(VpcId=vpc_id, CidrBlock=cidr_block)

    def create_public_route_table(self, vpc_id):
        logger.info(f"Erstelle Public Route Table für VPC: {vpc_id}")
        return self._client.create_route_table(VpcId=vpc_id)

    def create_igw_route_to_public_route_table(self, rtb_id, igw_id):
        logger.info(f"Füge route für IGW: {igw_id} zu Route Table: {rtb_id} hinzu")
        return self._client.create_route(
            RouteTableId=rtb_id, GatewayId=igw_id, DestinationCidrBlock="0.0.0.0/0"
        )

    def associate_subnet_with_route_table(self, subnet_id, rtb_id):
        logger.info(f"Associating subnet {subnet_id} with Route Table {rtb_id}")
        return self._client.associate_route_table(
            SubnetId=subnet_id, RouteTableId=rtb_id
        )

    def allow_auto_assign_ip_addresses_for_subnet(self, subnet_id):
        return self._client.modify_subnet_attribute(
            SubnetId=subnet_id, MapPublicIpOnLaunch={"Value": True}
        )
