"""Retain original failed/unknown fixtures; supervise explicit online preparation.

This uses the same trusted/cooperative observation limits as the build backend.
No caller's existing directory, environment, account, or service is discovered.
"""
from pathlib import Path
import os
import shutil
import signal
import subprocess
import tempfile
import time
from .build_runtime import BuildTree
from .runtime import Rejected, atomic


class BuildFixture:
    def __init__(self, prefix, parent=None):
        self.path = Path(tempfile.mkdtemp(prefix=prefix, dir=parent)).resolve()
        self.verified = False

    def __enter__(self):
        return self

    def safe_to_remove(self):
        # Call only after successful verification of every observed tree and cleanup.
        self.verified = True

    def __exit__(self, kind, value, traceback):
        if kind is None and self.verified:
            shutil.rmtree(self.path)
        else:
            # Keep original Git pointers, policy paths, cache and active-state identity.
            print('RETAINED: original synthetic execution directory:', self.path)


def run_preparation(argv, cwd, env, log, checkpoint, timeout=600):
    """No ambient environment; observed children must stop before cache sealing."""
    process = None; tree = None; stopped = False; reason = None
    began = time.monotonic()
    atomic(checkpoint, {'status':'STARTING','tree_stopped':False})
    try:
        with log.open('wb') as output:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=output,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            tree = BuildTree(process.pid)
            atomic(checkpoint, {'status':'RUNNING','pid':process.pid,'tree_stopped':False})
            while True:
                tree.live()
                if time.monotonic()-began >= timeout: reason='TIMEOUT'; break
                if process.poll() is not None: break
                time.sleep(.02)
            drain = time.monotonic()+3
            while reason is None and tree.live() and time.monotonic()<drain:
                if time.monotonic()-began >= timeout: reason='TIMEOUT'; break
                time.sleep(.02)
            if process.poll() is not None and tree.live(): reason=reason or 'BACKGROUND_PROCESS'
            stopped=tree.stop()
            process.wait(timeout=5)
            if not stopped: reason='PROCESS_UNKNOWN'
        result={'exit':process.returncode,'reason':reason,'tree_stopped':stopped,
                'observed_detached':tree.detached,'observed_process_peak':tree.peak}
        atomic(checkpoint, {'status':'SUCCEEDED' if process.returncode==0 and reason is None else 'FAILED' if stopped else 'UNKNOWN', **result})
        return result
    except BaseException:
        # Even on observer/host failure, only the still-live owned Popen group is
        # stopped best-effort; unknown state and its original files stay private.
        if process is not None and process.poll() is None:
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait(timeout=5)
        if tree:
            try: stopped=tree.stop()
            except Exception: stopped=False
        atomic(checkpoint, {'status':'UNKNOWN','tree_stopped':stopped})
        raise
