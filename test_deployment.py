import boto3
import paramiko

from loguru import logger
from helpers.vpc import VPC
from helpers.ec2 import EC2
from helpers.ssh import AWSSSH
from client_locator import EC2Client, config
from telethon import TelegramClient

key = paramiko.RSAKey.from_private_key_file(config["core"]["key"])
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
# api_id = config['telegram']['api_id']
# api_hash = config['telegram']['api_hash']

# bot = TelegramClient('aws', api_id, api_hash)
ec2_client = EC2Client().get_client()
vpc = VPC(ec2_client)
ec2 = EC2(ec2_client)
ssh = AWSSSH(client)


def main():
    #    await bot.send_message('billaids', 'Hello!')
    # ssh.exec_cmd(
    #     cmd="du -hcs .",
    #     key=key,
    #     host=config["core"]["server_ip"],
    #     user=config["core"]["username"],
    # )

    # Credential check
    logger.info(boto3.Session().get_credentials().access_key)
    logger.info(boto3.Session().get_credentials().secret_key)

    vpc_check = ec2.check_vpc(config["vpc"]["vpc_name"])
    if vpc_check:
        vpc_id = vpc_check[0]["VpcId"]
        vpc._set_vpc_id_(vpc_id)
    else:
        # Create VPC
        vpc_id = vpc.create_vpc(
            cidr=config["vpc"]["vpc_cidr_block"], vpc_name=config["vpc"]["vpc_name"]
        )

    public_subnet = ec2.check_subnet(config["subnet"]["public"]["tag"])
    private_subnet = ec2.check_subnet(config["subnet"]["private"]["tag"])

    if public_subnet and private_subnet:
        logger.info(public_subnet[0])
        private_subnet_id = private_subnet[0]["SubnetId"]
        public_subnet_id = public_subnet[0]["SubnetId"]

    else:
        # Create Public Subnet
        public_subnet_id = vpc.init_subnet(
            cidr=config["subnet"]["public"]["cidr"],
            tag=config["subnet"]["public"]["tag"],
        )

        # Create Private Subnet
        private_subnet_id = vpc.init_subnet(
            cidr=config["subnet"]["private"]["cidr"],
            tag=config["subnet"]["private"]["tag"],
        )

        # Create Internet Gateway and attach to public subnet
        igw_id = vpc.init_igw()

        # Create NAT Gateway
        nat_gateway_id = vpc.create_nat_gateway(
            subnet_id=public_subnet_id, gateway_tag=config["core"]["nat_gateway_name"]
        )

        # Create public route table
        public_route_table_id = vpc.init_route_table()

        # Create private route table
        private_route_table_id = vpc.init_route_table()

        # Attach IGW to public route table
        vpc.create_igw_route_to_route_table(
            rtb_id=public_route_table_id, igw_id=igw_id, cidrBlock="0.0.0.0/0"
        )

        # Attach public subnet with route table
        vpc.associate_subnet_with_route_table(
            subnet_id=public_subnet_id, rtb_id=public_route_table_id
        )

        # Attach public subnet with route table
        vpc.associate_subnet_with_route_table(
            subnet_id=private_subnet_id, rtb_id=private_route_table_id
        )

        # Allow auto assign IP for public subnet
        vpc.allow_auto_assign_ip_addresses_for_subnet(subnet_id=public_subnet_id)

    public_security_group = ec2.describe_security_groups(
        config["secgroup"]["public"]["name"]
    )
    private_security_group = ec2.describe_security_groups(
        config["secgroup"]["private"]["name"]
    )

    if public_security_group and private_security_group:
        logger.info(private_security_group)
        public_security_group_id = public_security_group["GroupId"]
        private_security_group_id = private_security_group["GroupId"]
    else:
        # Security Gruppen festlegen & Route Tables festlegen
        public_security_group = ec2.create_security_group(
            group_name=config["secgroup"]["public"]["name"],
            description=config["secgroup"]["public"]["description"],
            vpc_id=vpc_id,
        )
        private_security_group = ec2.create_security_group(
            group_name=config["secgroup"]["private"]["name"],
            description=config["secgroup"]["private"]["description"],
            vpc_id=vpc_id,
        )

        public_security_group_id = public_security_group["GroupId"]
        private_security_group_id = private_security_group["GroupId"]

        # Create Tags for security groups
        ec2._client.create_tags(Resources=[public_security_group_id], Tags=[{'Key': 'Name', 'Value': config["secgroup"]["public"]["name"]}])
        ec2._client.create_tags(Resources=[private_security_group_id], Tags=[{'Key': 'Name', 'Value': config["secgroup"]["private"]["name"]}])
        # Add Public IP_permission Rules
        ec2.add_inbound_rule_to_sg(
            public_security_group_id,
            config["secgroup"]["public"]["ip_permissions"]["inbound"],
        )
        ec2.add_inbound_rule_to_sg(
            public_security_group_id,
            config["secgroup"]["public"]["ip_permissions"]["outbound"],
        )

        # Add private IP_permission Rules
        ec2.add_inbound_rule_to_sg(
            private_security_group_id,
            config["secgroup"]["private"]["ip_permissions"]["inbound"],
        )
        ec2.add_inbound_rule_to_sg(
            private_security_group_id,
            config["secgroup"]["private"]["ip_permissions"]["outbound"],
        )

    # Leader erstellen & starten
    ami_id = config["core"]["ami_id"]
    exec_cmd_master = """#!/bin/bash
                sudo curl -fsSL https://get.docker.com | bash
                sudo usermod -aG docker $USER
                docker swarm init
                """

    ec2.launch_ec2_instance(
        image_id=ami_id,
        key_name=config["secgroup"]["public"]["key_pair_name"],
        min_count=1,
        max_count=1,
        security_group_id=public_security_group_id,
        subnet_id=public_subnet_id,
        user_data=exec_cmd_master,
        instance_type=config["core"]["instance_type_master"],
    )

    logger.info(f"Start public EC2 Instance with AMI-Image {ami_id}")

    # # SSH Keys für Zugriff auf Private Worker erstellen

    # # Worker erstellen & starten & SSH Keys hinterlegen

    exec_cmd_worker = """#!/bin/bash
                  sudo curl -fsSL https://get.docker.com | bash
                  sudo usermod -aG docker $USER
                  """

    ec2.launch_ec2_instance(
        image_id=ami_id,
        key_name=config["secgroup"]["public"]["key_pair_name"],
        min_count=3,
        max_count=3,
        security_group_id=private_security_group_id,
        subnet_id=private_subnet_id,
        user_data=exec_cmd_worker,
        instance_type=config["core"]["instance_type_worker"],
    )

    logger.info(f"Start private EC2 Instance with AMI-Image {ami_id}")
    # ssh -i privkey ubuntu@ip docker swarm join-token worker | sed 1,2d | sed 2d

    # TODO: Alle IPs von Worker-Nodes herausfinden und Deploy-Command schreiben


if __name__ == "__main__":
    # with bot:
    #    bot.loop.run_until_complete(main())
    main()
