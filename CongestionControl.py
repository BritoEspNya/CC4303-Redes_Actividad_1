
class CongestionControl:
    STATES = ["slow start", "congestion avoidance"]
    def __init__(self, MSS: int):
        self.__current_state = self.STATES[0]
        self.__MSS = MSS
        self.__cwnd = MSS
        self.__ssthresh = None

    def get_cwnd(self):
        return self.__cwnd

    def get_MSS_in_cwnd(self):
        return self.__cwnd // self.__MSS
    
    def get_ssthresh(self):
        return self.__ssthresh
    
    def event_ack_received(self):
        if self.__current_state == self.STATES[0]:
            self.__cwnd += self.__MSS
            if self.__ssthresh and self.__cwnd >= self.__ssthresh:
                self.__current_state = self.STATES[1]
        elif self.__current_state == self.STATES[1]:
            self.__cwnd += self.__MSS/self.get_MSS_in_cwnd()

    def event_timeout(self):
        self.__ssthresh = self.__cwnd // 2
        self.__cwnd = self.__MSS
        if self.__current_state == self.STATES[1]:
            self.__current_state = self.STATES[0]

    def is_state_slow_start(self):
        return self.__current_state == self.STATES[0]

    def is_state_congestion_avoidance(self):
        return self.__current_state == self.STATES[1]