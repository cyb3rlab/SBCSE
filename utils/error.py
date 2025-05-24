class RCPError(Exception):
    def __init__(self, errorcode):
        self.errorcode = errorcode
        super().__init__("RCPError: "+self.errorcode)

class RCPTimeOut(Exception):
    def __init__(self):
        super().__init__("RCPTimeOut")

class ROBCollision(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)