from logging import NullHandler
from loguru import logger


class EC2:
    def __init__(self, client):
        self._client = client

    def create_key_pair(self, key_name):
        logger.info(f"Create key-pair: {key_name}")
        return self._client.create_key_pair(KeyName=key_name)

    def create_security_group(self, group_name, description, vpc_id):
        logger.info(f"Create security group: {group_name} für VPC {vpc_id}")
        return self._client.create_security_group(
            GroupName=group_name, Description=description, VpcId=vpc_id
        )

    def describe_security_groups(self, tag):
        logger.info("List all Security Groups ...")
        security_groups = self._client.describe_security_groups(
            Filters=[
                {
                    "Name": "tag:Name",
                    "Values": [
                        tag,
                    ],
                },
            ]
        )
        logger.info(security_groups)
        try:
            if security_groups["SecurityGroups"]:
                logger.info(security_groups["SecurityGroups"])
                return security_groups["SecurityGroups"][0]
            else:
                logger.info("No vpcs found")
                return False
        except Exception as e:
            logger.error(e)
            return False

    def add_inbound_rule_to_sg(self, security_group_id, rules):
        logger.info(f"Add inbound rules for security group: {security_group_id}")
        self._client.authorize_security_group_ingress(
            GroupId=security_group_id, IpPermissions=rules
        )

    def launch_ec2_instance(
        self,
        image_id,
        key_name,
        min_count,
        max_count,
        subnet_id,
        security_group_id,
        user_data,
        instance_type,
    ):
        logger.info(f"Start EC2 Instace in subnet {subnet_id}")
        return self._client.run_instances(
            ImageId=image_id,
            KeyName=key_name,
            MinCount=min_count,
            MaxCount=max_count,
            InstanceType=instance_type,
            SecurityGroupIds=[security_group_id],
            SubnetId=subnet_id,
            UserData=user_data,
        )

    def describe_ec2_instances(self):
        logger.info("List all EC2 Instances...")
        return self._client.describe_instances()

    def modify_ec2_instance(self, instance_id):
        logger.info(f"Modify EC2 Instance {instance_id}")
        return self._client.modify_instance_attribute(
            InstanceId=instance_id, DisableApiTermination={"Value": True}
        )

    def init_secgroup(
        self,
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
        public_security_group_response = self._client.create_security_group(
            public_security_group_name, public_security_group_description, vpc_id
        )

        self._public_security_group_id = public_security_group_response["GroupId"]

        # Füge ein- und ausgehende rules hinzu für Public Security Group
        self._client.add_inbound_rule_to_sg(
            self._public_security_group_id, ip_permissions_inbound_public
        )
        self._client.add_outbound_rule_to_sg(
            self._public_security_group_id, ip_permissions_outbound_public
        )

        """ PRIVATE """
        private_security_group_response = self._client.create_security_group(
            private_security_group_name, private_security_group_description, vpc_id
        )
        private_security_group_id = private_security_group_response["GroupId"]

        # Füge ein- und ausgehende rules hinzu für Private Security Group
        self._client.add_inbound_rule_to_sg(
            private_security_group_id, ip_permissions_inbound_private
        )
        self._client.add_outbound_rule_to_sg(
            private_security_group_id, ip_permissions_outbound_private
        )

        logger.info(f"Add in- and outbound rules for {public_security_group_name}")

    def check_vpc(self, tag):
        response = self._client.describe_vpcs(
            Filters=[
                {
                    "Name": "tag:Name",
                    "Values": [
                        tag,
                    ],
                },
            ]
        )
        try:
            if response["Vpcs"]:
                logger.info(response["Vpcs"][0]["Tags"][0]["Value"])
                return response["Vpcs"]
            else:
                logger.info("No vpcs found")
                return False
        except Exception as e:
            logger.error(e)
            return False

    def check_subnet(self, tag):
        subnets = self._client.describe_subnets(
            Filters=[
                {
                    "Name": "tag:Name",
                    "Values": [
                        tag,
                    ],
                },
            ]
        )

        try:
            if subnets["Subnets"]:
                return subnets["Subnets"]
            else:
                return False
        except Exception as e:
            logger.error(e)
            return False

    def check_instances(self, tag):
        tmp_list = []
        instances = self._client.describe_instances(
            Filters=[
                {
                    "Name": "instance.group-id",
                    "Values": [
                        tag,
                    ],
                },
            ]
        )
        logger.info(instances)
        try:
            for i in instances["Reservations"][0]["Instances"]:
                tmp_list.append(i["PrivateIpAddress"])
            return tmp_list
        except Exception as e:
            logger.error(e)
            return False
