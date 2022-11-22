"""
Utility function to record last shimming results
"""
import time
import os
import json
import queue
from functools import wraps


HERE = os.path.dirname(os.path.abspath(__file__))
SHIMMING_PARAMETERS = "shim.par"
TIME_FORMAT = r"%Y-%m-%dT%H:%M:%S.%f"


def shimming(f):
    """Decorator to record shimming data."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        spinsolve_instance = args[0]

        # performing shimming
        result = f(*args, **kwargs)
        params_path = os.path.join(result, SHIMMING_PARAMETERS)

        # extracting and saving shimming parameters
        spinsolve_instance.last_shimming_results = (
            spinsolve_instance.spectrum.extract_parameters(params_path)
        )

        # appending path
        spinsolve_instance.last_shimming_results.update(path=params_path)

        # loading and saving timestamp
        shimming_time = time.strptime(
            spinsolve_instance.last_shimming_results["CurrentTime"], TIME_FORMAT
        )
        spinsolve_instance.last_shimming_results.update(
            timestamp=time.mktime(shimming_time)
        )

        # emptying data folder queue, as shimming doesn't need processing
        try:
            spinsolve_instance.data_folder_queue.get_nowait()
        except queue.Empty:
            pass

        # saving to json
        with open(os.path.join(HERE, "shimming.json"), "w") as fobj:
            json.dump(spinsolve_instance.last_shimming_results, fobj)

        return result

    return wrapper
