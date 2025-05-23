

class BOS_ModeHandler:
    def __init__(self, bos_handler):
        self.bos_handler = bos_handler

    def handle_msg(self, client, userdata, msg):
        raise NotImplementedError