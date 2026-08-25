import os
import sys


def main() -> None:
    log = os.environ.get("SLM_TAMER_LOG", "/tmp/slm-tamer-core.log")
    pid = os.fork()
    if pid == 0:
        os.setsid()
        if os.fork() != 0:
            os._exit(0)
        fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
        os.dup2(fd, 1)
        os.dup2(fd, 2)
        devnull = os.open(os.devnull, os.O_RDONLY)
        os.dup2(devnull, 0)
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(here)
        os.execvp(sys.executable, [sys.executable, "-m", "slmtamer"] + sys.argv[1:])
    os.waitpid(pid, 0)


if __name__ == "__main__":
    main()
