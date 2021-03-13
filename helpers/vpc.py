from loguru import logger


class VPC:
    def __init__(self, client):
        self._client = client
        """ :type : pyboto3.ec2 """

    def _set_vpc_id_(self, vpc_name):
        self._vpc_id = vpc_name

    def create_vpc(self, cidr, vpc_name):
        logger.info("Create VPC...")
        self._vpc_name = vpc_name

        # Create VPC
        vpc_response = self._client.create_vpc(CidrBlock=cidr)

        if "pending" in vpc_response["Vpc"]["State"]:
            logger.info(f'Created VPC: {vpc_response["Vpc"]["VpcId"]}')
        else:
            logger.error(f"An error occured: {vpc_response}")

        # Add Tag to VPC
        self._vpc_id = vpc_response["Vpc"]["VpcId"]
        self._client.create_tags(
            Resources=[self._vpc_id], Tags=[{"Key": "Name", "Value": self._vpc_name}]
        )

        logger.info(f"Add tag {vpc_name} to {self._vpc_id}")
        return self._vpc_id

    def init_subnet(self, cidr, tag):

        subnet_response = self._client.create_subnet(VpcId=self._vpc_id, CidrBlock=cidr)

        logger.info(f"Create Subnet for VPC: {self._vpc_id} with CIDR: {cidr}")

        subnet_id = subnet_response["Subnet"]["SubnetId"]

        # Tag Subnet
        self._client.create_tags(
            Resources=[subnet_id], Tags=[{"Key": "Name", "Value": tag}]
        )

        return subnet_id

    def init_route_table(self):
        route_table_response = self._client.create_route_table(VpcId=self._vpc_id)
        rtb_id = route_table_response["RouteTable"]["RouteTableId"]
        logger.info(f"Create Route Table for VPC: {self._vpc_id}")

        return rtb_id

    def create_igw_route_to_route_table(self, rtb_id, igw_id, cidrBlock):
        logger.info(f"Attach route from IGW: {igw_id} to Route Table: {rtb_id}")
        return self._client.create_route(
            RouteTableId=rtb_id, GatewayId=igw_id, DestinationCidrBlock=cidrBlock
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
        logger.info(f"Internetgateway: {igw_id} was created")
        self._client.attach_internet_gateway(
            InternetGatewayId=igw_id, VpcId=self._vpc_id
        )
        logger.info(f"Attach Internetgateway: {igw_id} to VPC: {self._vpc_id}")

        return igw_id

    def create_nat_gateway(self, subnet_id, gateway_tag):

        # Allocate Elastic IP
        eip_for_nat_gateway = self._client.allocate_address(Domain="vpc")
        allocation_id = eip_for_nat_gateway["AllocationId"]

        # Create Nat Gateway
        gateway_id = self._client.create_nat_gateway(
            SubnetId=subnet_id, AllocationId=allocation_id
        )

        logger.info(f'Created Nat Gateway: {gateway_id["NatGateway"]["NatGatewayId"]}')

        return gateway_id["NatGateway"]["NatGatewayId"]

    # def create_priv_key(key_pair_name_private):
    #     key_pair_private_response = self._client.create_key_pair(key_pair_name_private)
    #     logger.info(f"Key: {key_pair_private_response}")
    #     f = open("privkey", "w")
    #     f.write(key_pair_private_response)
    #     f.close()
