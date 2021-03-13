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
