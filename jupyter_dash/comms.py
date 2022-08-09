import asyncio
import IPython
from ipykernel.comm import Comm
import nest_asyncio
import time
import sys
import ipykernel
from nbclient.util import just_run
import ipython_blocking

_jupyter_config = {}

_dash_comm = Comm(target_name='jupyter_dash')

_caller = {}


def _send_jupyter_config_comm_request():
    # If running in an ipython kernel,
    # request that the front end extension send us the notebook server base URL
    if IPython.get_ipython() is not None:
        if _dash_comm.kernel is not None:
            _caller["parent"] = _dash_comm.kernel.get_parent()
            _dash_comm.send({
                'type': 'base_url_request'
            })


@_dash_comm.on_msg
def _receive_message(msg):
    prev_parent = _caller.get("parent")
    if prev_parent and prev_parent != _dash_comm.kernel.get_parent():
        _dash_comm.kernel.set_parent([prev_parent["header"]["session"]], prev_parent)
        del _caller["parent"]

    msg_data = msg.get('content').get('data')
    msg_type = msg_data.get('type', None)
    if msg_type == 'base_url_response':
        _jupyter_config.update(msg_data)


def _jupyter_comm_response_received():
    return bool(_jupyter_config)


def _request_jupyter_config(timeout=2):
    # Heavily inspired by implementation of CaptureExecution in the
    if _dash_comm.kernel is None:
        # Not in jupyter setting
        return

    _send_jupyter_config_comm_request()

    # Allow kernel to execute comms until we receive the jupyter configuration comm
    # response
    t0 = time.time()
    ctx = ipython_blocking.CaptureExecution(replay=True)
    with ctx:
        while True:
            if (time.time() - t0) > timeout:
                # give up
                raise EnvironmentError(
                    "Unable to communicate with the jupyter_dash notebook or JupyterLab \n"
                    "extension required to infer Jupyter configuration."
                )
            if _jupyter_comm_response_received():
                break
            ctx.step()
