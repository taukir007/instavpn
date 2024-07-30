import subprocess
import select
import logging

logger = logging.getLogger(__name__)

def call(popenargs,
         stdout_log_level=logging.DEBUG,
         stderr_log_level=logging.ERROR, **kwargs):
    child = subprocess.Popen(popenargs, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, **kwargs)

    log_level = {child.stdout: stdout_log_level,
                 child.stderr: stderr_log_level}

    def check_io():
        ready_to_read = select.select([child.stdout, child.stderr], [], [], 1.0)[0]
        for io in ready_to_read:
            line = io.readline()
            if line:
                logger.log(log_level[io], line.decode().rstrip())

    while child.poll() is None:
        check_io()

    check_io()  # Check again to catch any remaining output

    child.stdout.close()
    child.stderr.close()

    return child.wait()

# Example usage:
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    call(["echo", "Hello, world!"])
