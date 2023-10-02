from integrations.services.RestClient.integrate import ApiConnectClient


class MarioService(ApiConnectClient):
    service_name = 'Mario'
    url_pa = ''

    def __init__(self):
        super().__init__(self.service_name)

    def search(self, search):
        """
        _____________________________________________________________________
        Description:
        This function makes a post request to RAT

        Arguments:
        record_id ---> string
        rat_code ---> string (IRAI,IRTI, etc.)
        user_department ---> string
        user_id ---> string
        date ---> string (date of the post request)
        created_at ---> datetime

        Returns:
        200 OK
        201 Created
        401 Unauthorized
        403 Forbidden
        404 Not Found
        ______________________________________________________________________
        """
        self.logger.info(f"MARIO WS|SENDING REQUEST|{search}")
        data = self.get_ac(extension='api', params={'tematica': search})
        self.logger.info(f"MARIO WS|REQUEST SENT")
        return data
