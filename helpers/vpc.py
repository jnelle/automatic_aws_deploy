from loguru import logger


class VPC:
    def __init__(self, client):
        self._client = client
        self._vpc_id = ""
        """ :type : pyboto3.ec2 """

    def create_vpc(self, cidr, vpc_name):
        logger.info("Erstelle VPC...")
        self._vpc_name = vpc_name

        # Create VPC
        vpc_response = self._client.create_vpc(cidr)

        if "pending" in vpc_response["Vpc"]["State"]:
            logger.info(f"VPC erstellt: {vpc_response}")
        else:
            logger.error(f"Fehler aufgetreten: {vpc_response}")

        # Add Tag to VPC
        self._vpc_id = vpc_response["Vpc"]["VpcId"]
        self._client.add_name_tag(self._vpc_id, vpc_name)

        logger.info(f"Füge {vpc_name} zu {self._vpc_id} hinzu")

    def add_name_tag(self):
        logger.info(f"Füge {self._vpc_name} tag zu {self._vpc_id} hinzu")
        return self._client.create_tags(
            Resources=[self._vpc_id], Tags=[{"Key": "Name", "Value": self._vpc_name}]
        )

    def attach_igw_to_vpc(self, igw_id):
        logger.info(f"Verknüpfe Internetgateway: {igw_id} zu VPC: {self._vpc_id}")
        return self._client.attach_internet_gateway(
            InternetGatewayId=igw_id, VpcId=self._vpc_id
        )

    def init_subnet(self, cidr, tag):

        subnet_response = self._client.create_subnet(self._vpc_id, cidr)

        logger.info(f"Erstelle Subnet für VPC: {self._vpc_id} mit CIDR: {cidr}")

        subnet_id = subnet_response["Subnet"]["SubnetId"]

        # Tag Subnet
        self._client.add_name_tag(subnet_id, tag)

        return subnet_id

    def init_route_table(self):
        route_table_response = self._client.create_route_table(self._vpc_id)
        rtb_id = route_table_response["RouteTable"]["RouteTableId"]
        logger.info(f"Erstelle Route Table für VPC: {self._vpc_id}")

        return rtb_id

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

    def init_igw(self):

        # Create IGW
        igw_response = self._client.create_internet_gateway()
        igw_id = igw_response["InternetGateway"]["InternetGatewayId"]
        self._client.attach_igw_to_vpc(self._vpc_id, igw_id)

        return igw_id

    def create_nat_gateway(self, subnet_id):

        # Allocate Elastic IP
        eip_for_nat_gateway = self._client.allocate_address(Domain="vpc")
        allocation_id = eip_for_nat_gateway["AllocationId"]

        # Create Nat Gateway
        gateway_id = self._client.create_nat_gateway(
            SubnetId=subnet_id, AllocationId=allocation_id
        )

        return gateway_id["NatGateway"]["NatGatewayId"]

    # def create_priv_key(key_pair_name_private):
    #     key_pair_private_response = self._client.create_key_pair(key_pair_name_private)
    #     logger.info(f"Key: {key_pair_private_response}")
    #     f = open("privkey", "w")
    #     f.write(key_pair_private_response)
    #     f.close()
