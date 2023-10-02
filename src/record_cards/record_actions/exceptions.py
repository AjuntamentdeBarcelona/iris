class RecordClaimException(Exception):
    message = None
    must_be_comment = False

    def __init__(self, message, must_be_comment=False, public_api_message=None):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)
        self.message = message
        self.must_be_comment = must_be_comment
        self.public_api_message = public_api_message
