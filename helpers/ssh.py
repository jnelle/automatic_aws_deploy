import time

from loguru import logger


class AWSSSH:
    def __init__(self, client):
        self._ssh = client

    def exec_cmd(self, cmd, key, host, user):
        try:
            self._ssh.connect(
                hostname=host,
                username=user,
                pkey=key,
            )
            stdin, stdout, stderr = self._ssh.exec_command(cmd)
            logger.info(stdout.read().decode("utf-8"))

            # https://stackoverflow.com/a/61963615
            time.sleep(0.5)

            self._ssh.close()

        except Exception as e:
            logger.error(e)

    def config_all(self, key, host, user, ip):
        self.exec_cmd(
            cmd=f"bash deploy_all.sh {ip}",
            key=key,
            host=host,
            user=user,
        )

    def upload_sftp(self, localpath, remotepath, host, user, key):
        try:
            self._ssh.connect(hostname=host, username=user, pkey=key)
            sftp = self._ssh.open_sftp()
            # https://docs.paramiko.org/en/stable/api/sftp.html#paramiko.sftp_client.SFTPClient.put
            sftp.put(localpath, remotepath, confirm=True)
            time.sleep(1)
            logger.info(f"Successfully uploaded file {localpath}")
            self._ssh.close()

        except Exception as e:
            logger.error(e)
