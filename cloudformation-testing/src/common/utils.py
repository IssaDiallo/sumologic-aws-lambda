import json
import os
import subprocess
import sys


def get_normalized_path(path):
    return os.path.realpath(os.path.abspath(os.path.expanduser(path)))


def check_if_valid_file(file_path):
    if not os.path.isfile(file_path):
        raise Exception("Provided path %s is not a valid file path." % file_path)
    return True


def get_absolute_path(relative_path, compare_file_path):
    if not os.path.isabs(relative_path):
        absolute_path = os.path.join(os.path.dirname(compare_file_path), relative_path)
        absolute_path = os.path.abspath(absolute_path)
        return absolute_path
    return relative_path


def load_json_file(file_full_path):
    """
    Load the given Test JSON file.
    """
    content = {}
    if check_if_valid_file(file_full_path):
        with open(file_full_path, 'r') as fp:
            content = fp.read()
    return json.loads(content)


def _run(command, input=None, check=False, **kwargs):
    if sys.version_info >= (3, 5):
        return subprocess.run(command, capture_output=True)
    if input is not None:
        if 'stdin' in kwargs:
            raise ValueError('stdin and input arguments may not both be used.')
        kwargs['stdin'] = subprocess.PIPE

    process = subprocess.Popen(command, **kwargs)
    try:
        stdout, stderr = process.communicate(input)
    except:
        process.kill()
        process.wait()
        raise
    retcode = process.poll()
    if check and retcode:
        raise subprocess.CalledProcessError(
            retcode, process.args, output=stdout, stderr=stderr)
    return retcode, stdout, stderr


def run_command(cmdargs):
    resp = _run(cmdargs)
    if len(resp.stderr.decode()) > 0:
        raise Exception("Error in run command %s cmd: %s" % (resp, cmdargs))
    return resp.stdout
