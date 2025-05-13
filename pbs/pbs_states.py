# Copyright (C) 2025 J. Taylor Childers
# License MIT [https://opensource.org/licenses/MIT]
JOB_STATE_MAP = {
    "Q": "Queued",
    "R": "Running",
    "H": "Held",
    "W": "Waiting",
    "T": "Transit",
    "E": "Exiting",
    "B": "Begun",
    "S": "Suspended",
    "C": "Completed",
}

def get_full_state_name(state_code):
    """
    Convert a single-letter PBS job state code to its full name.
    
    :param state_code: Single-letter job state code (e.g., "Q")
    :type state_code: str
    :return: Full name of the job state (e.g., "Queued")
    :rtype: str
    """
    return JOB_STATE_MAP.get(state_code, "Unknown")

def get_state_code(full_state_name):
    """
    Convert a full PBS job state name to its single-letter code.
    
    :param full_state_name: Full name of the job state (e.g., "Queued")
    :type full_state_name: str
    :return: Single-letter job state code (e.g., "Q")
    :rtype: str
    """
    for code, name in JOB_STATE_MAP.items():
        if name.lower() == full_state_name.lower():
            return code
    return "Unknown"

# Example usage
if __name__ == "__main__":
    print(get_full_state_name("Q"))  # Should print "Queued"
    print(get_state_code("Queued"))  # Should print "Q"
    print(get_full_state_name("R"))  # Should print "Running"
    print(get_state_code("Running"))  # Should print "R"
    print(get_full_state_name("H"))  # Should print "Held"
    print(get_state_code("Held"))  # Should print "H"
    print(get_full_state_name("Unknown"))  # Should print "Unknown"
    print(get_state_code("Unknown"))  # Should print "Unknown"
