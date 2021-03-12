from loguru import logger


class VPC:
    def __init__(self, client):
        self._client = client
        self._vpc_id = ""
        """ :type : pyboto3.ec2 """

    def create_vpc(self, cidr, vpc_name):
        logger.info("Erstelle VPC...")
        self._vpc_name = vpc_name

        # Erstelle VPC
        vpc_response = self._client.create_vpc(cidr)

        if "pending" in vpc_response["Vpc"]["State"]:
            logger.info(f"VPC erstellt: {vpc_response}")
        else:
            logger.error(f"Fehler aufgetreten: {vpc_response}")

        # Tag zu VPC hinzufügen
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

    def create_subnet(self, cidr_block):
        logger.info(f"Erstelle Subnet für VPC: {self._vpc_id} mit CIDR: {cidr_block}")
        return self._client.create_subnet(VpcId=self._vpc_id, CidrBlock=cidr_block)

    def create_public_route_table(self):
        logger.info(f"Erstelle Public Route Table für VPC: {self._vpc_id}")
        return self._client.create_route_table(VpcId=self._vpc_id)

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
        # Erstelle IGW
        igw_response = self._client.create_internet_gateway()
        igw_id = igw_response["InternetGateway"]["InternetGatewayId"]
        self._client.attach_igw_to_vpc(self._vpc_id, igw_id)
        return igw_id

    def init_subnets(
        self,
        igw_id,
        private_subnet_cidr,
        public_subnet_tag,
        public_subnet_cidr,
        private_subnet_tag,
    ):
        # Erstelle public subnet
        public_subnet_response = self._client.create_subnet(
            self._vpc_id, private_subnet_cidr
        )

        public_subnet_id = public_subnet_response["Subnet"]["SubnetId"]

        logger.info(
            f"Subnet wurde erstellt für VPC: {self._vpc_id} : {public_subnet_response}"
        )

        # Tagge Public Subnet
        self._client.add_name_tag(public_subnet_id, public_subnet_tag)

        # Erstelle public route table
        public_route_table_response = self._client.create_public_route_table(
            self._vpc_id
        )

        rtb_id = public_route_table_response["RouteTable"]["RouteTableId"]

        # Füge IGW zu public route table hinzu
        self._client.create_igw_route_to_public_route_table(rtb_id, igw_id)

        # Verknüpfe Public Subnet mit Route Table
        self._client.associate_subnet_with_route_table(public_subnet_id, rtb_id)

        # Erlaube public ip addresse für subnet
        self._client.allow_auto_assign_ip_addresses_for_subnet(public_subnet_id)

        # Erstelle Private Subnet
        private_subnet_response = self._client.create_subnet(
            self._vpc_id, private_subnet_cidr
        )
        private_subnet_id = private_subnet_response["Subnet"]["SubnetId"]

        logger.info(
            f"Private subnet {private_subnet_id} für VPC {self._vpc_id} wurde erstellt"
        )

        # Tagge private subnet
        self._client.add_name_tag(private_subnet_id, private_subnet_tag)

        return private_subnet_id

    def create_priv_key(key_pair_name_private):
        key_pair_private_response = self._client.create_key_pair(key_pair_name_private)
        logger.info(f"Key: {key_pair_private_response}")
        f = open("privkey", "w")
        f.write(key_pair_private_response)
        f.close()
