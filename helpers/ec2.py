from loguru import logger


class EC2:
    def __init__(self, client):
        self._client = client

    def create_key_pair(self, key_name):
        logger.info(f"Erstelle Key-Paar: {key_name}")
        return self._client.create_key_pair(KeyName=key_name)

    def create_security_group(self, group_name, description, vpc_id):
        logger.info(f"Erstelle Security Group: {group_name} für VPC {vpc_id}")
        return self._client.create_security_group(
            GroupName=group_name, Description=description, VpcId=vpc_id
        )

    def describe_security_groups(self):
        logger.info("Liste alle Security Groups auf...")
        return self._client.describe_security_groups()

    def add_inbound_rule_to_sg(self, security_group_id, rules):
        logger.info(
            "Füge eingehende Regeln für die Security Group: {security_group_id} hinzu"
        )
        self._client.authorize_security_group_ingress(
            GroupId=security_group_id, IpPermissions=rules
        )

    def add_outbound_rule_to_sg(self, security_group_id, rules):
        logger.info(
            "Füge eingehende Regeln für die Security Group: {security_group_id} hinzu"
        )
        self._client.authorize_security_group_egress(
            GroupId=security_group_id, IpPermissions=rules
        )

    def launch_ec2_instance(
        self,
        image_id,
        key_name,
        min_count,
        max_count,
        user_data,
        instance_type,
    ):
        logger.info(f"Starte EC2 Instanz im Subnet {self._subnet_id}")
        return self._client.run_instances(
            ImageId=image_id,
            KeyName=key_name,
            MinCount=min_count,
            MaxCount=max_count,
            InstanceType=instance_type,
            SecurityGroupIds=[self._security_group_id],
            SubnetId=self._subnet_id,
            UserData=user_data,
        )

    def describe_ec2_instances(self):
        logger.info("Liste alle EC2 Instanzen auf...")
        return self._client.describe_instances()

    def modify_ec2_instance(self, instance_id):
        logger.info(f"Ändere EC2 Instanz {instance_id}")
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

        logger.info(
            f"Ein- und Ausgehende Regeln wurden hinzugefügt für {public_security_group_name}"
        )
