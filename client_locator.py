import boto3
import yaml

config = yaml.load(open("config.yaml"), Loader=yaml.FullLoader)


class ClientLocator:
    def __init__(self, client):
        self._client = boto3.client(
            client, region_name=config["core"]["server_location"]
        )

    def get_client(self):
        return self._client


class EC2Client(ClientLocator):
    def __init__(self):
        super().__init__("ec2")
