import paramiko
import time

from loguru import logger
from helpers.vpc import VPC
from helpers.ec2 import EC2
from helpers.ssh import AWSSSH
from client_locator import EC2Client, config

pub_key = paramiko.RSAKey.from_private_key_file(config["core"]["pub_key"])
priv_key = paramiko.RSAKey.from_private_key_file(config["core"]["priv_key"])
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

ec2_client = EC2Client().get_client()
vpc = VPC(ec2_client)
ec2 = EC2(ec2_client)
ssh = AWSSSH(client)


def main():

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

        # Attach nat to private subnet
        time.sleep(15)

        vpc.attach_nat_to_subnet(
            gateway=nat_gateway_id,
            cidr_block="0.0.0.0/0",
            rtb_id=private_route_table_id,
        )

    public_security_group = ec2.describe_security_groups(
        tag=config["secgroup"]["public"]["name"]
    )
    private_security_group = ec2.describe_security_groups(
        tag=config["secgroup"]["private"]["name"]
    )

    if public_security_group and private_security_group:
        public_security_group_id = public_security_group["GroupId"]
        private_security_group_id = private_security_group["GroupId"]
    else:
        # Create Security Groups and Route Tables
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
        ec2.create_tag(
            tag=config["secgroup"]["public"]["name"], 
            secgp=public_security_group_id
        )
        ec2.create_tag(
            secgp=private_security_group_id,
            tag=config["secgroup"]["private"]["name"],
        )

        # Add Public IP_permission Rules

        ec2.add_inbound_rule_to_sg(
            public_security_group_id,
            config["secgroup"]["public"]["ip_permissions"]["inbound"],
        )
        # Allow all inbound traffic from worker nodes
        ec2.add_inbound_rule_all(
            security_group_id=public_security_group_id,
            secname=private_security_group_id,
        )

        # Add private IP_permission Rules
        ec2.add_inbound_rule_to_sg(
            private_security_group_id,
            config["secgroup"]["private"]["ip_permissions"]["inbound"],
        )

    instance_status = ec2.check_instances(private_security_group_id)

    if instance_status:
        logger.info(f"There are already running instances {instance_status}")
    else:
        # Create and start Master
        ami_id = config["core"]["ami_id"]
        exec_cmd_master = """#!/bin/bash
                    wget https://gist.github.com/Billaids/269389687c1bfa13084689d59f8830f2/raw/c270416c9af7909f528d8a25195dd2d7bc05e188/deploy_all.sh -O /home/ubuntu/deploy_all.sh 
                    chmod 755 /home/ubuntu/deploy_all.sh
                    sudo curl -fsSL https://get.docker.com | bash
                    sudo usermod -aG docker ubuntu
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

        # Create and start Worker

        exec_cmd_worker = """#!/bin/bash
                    sudo curl -fsSL https://get.docker.com | bash
                    sudo usermod -aG docker ubuntu
                    """

        ec2.launch_ec2_instance(
            image_id=ami_id,
            key_name=config["secgroup"]["private"]["key_pair_name"],
            min_count=3,
            max_count=3,
            security_group_id=private_security_group_id,
            subnet_id=private_subnet_id,
            user_data=exec_cmd_worker,
            instance_type=config["core"]["instance_type_worker"],
        )

        logger.info(f"Start private EC2 Instance with AMI-Image {ami_id}")

        # high performant aws nodes need some time to startup
        time.sleep(180)

    # ec2.create_priv_key(key_pair_name_private=config["secgroup"]["private"]["key_pair_name"])

    # Get IP-Adresses from running instances
    instance_status_worker = ec2.check_instances(private_security_group_id)
    instance_status_master = ec2.check_instances_master(public_security_group_id)

    # Upload worker node private key to master node
    for x in instance_status_master:
        ssh.upload_sftp(
            localpath=config["core"]["local_path"],
            remotepath=config["core"]["remote_path"],
            host=x,
            user=config["core"]["username"],
            key=pub_key,
        )
        for i in instance_status_worker:
            ssh.config_all(
                ip=i,
                key=pub_key,
                host=x,
                user=config["core"]["username"],
            )


if __name__ == "__main__":
    main()
