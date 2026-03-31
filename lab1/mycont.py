import os
import sys
import json
import shutil
import signal
import subprocess

SCRIPT_NAME = "mycont"
BASE_PATH = f"/var/lib/{SCRIPT_NAME}"
BASE_ROOTFS = f"{BASE_PATH}/base_rootfs"
CGROUP_BASE = "/sys/fs/cgroup"


def run(cmd):
    subprocess.run(cmd, shell=True, check=True)


def load_config(config_path):
    with open(os.path.join(config_path, "config.json")) as f:
        return json.load(f)


def prepare_dirs(cid):
    root = os.path.join(BASE_PATH, cid)
    upper = os.path.join(root, "upper")
    work = os.path.join(root, "work")
    merged = os.path.join(root, "merged")

    os.makedirs(upper, exist_ok=True)
    os.makedirs(work, exist_ok=True)
    os.makedirs(merged, exist_ok=True)

    return root, upper, work, merged


def mount_overlay(lower, upper, work, merged):
    run(f"mount -t overlay overlay -o lowerdir={lower},upperdir={upper},workdir={work} {merged}")


def setup_cgroup(cid, config):
    cg = os.path.join("/sys/fs/cgroup", f"{SCRIPT_NAME}-{cid}")
    os.makedirs(cg, exist_ok=True)

    resources = config.get("linux", {}).get("resources", {})

    mem = resources.get("memory", {})
    if "limit" in mem:
        with open(f"{cg}/memory.max", "w") as f:
            f.write(str(mem["limit"]))
    else:
        with open(f"{cg}/memory.max", "w") as f:
            f.write("max")

    cpu = resources.get("cpu", {})
    if "quota" in cpu and "period" in cpu:
        with open(f"{cg}/cpu.max", "w") as f:
            f.write(f"{cpu['quota']} {cpu['period']}")
    else:
        with open(f"{cg}/cpu.max", "w") as f:
            f.write("max 100000")

    return cg


def add_proc_to_cgroup(cg, pid):
    with open(f"{cg}/cgroup.procs", "w") as f:
        f.write(str(pid))


def cleanup(root, cg):
    try:
        run(f"umount -l {root}/merged/proc")
    except:
        pass

    try:
        run(f"umount -l {root}/merged")
    except:
        pass

    try:
        shutil.rmtree(root)
    except:
        pass

    try:
        os.rmdir(cg)
    except:
        pass


def container_main(merged, hostname, args):
    subprocess.run(["hostname", hostname], check=True)

    os.chroot(merged)
    os.chdir("/")
    run("mount -t proc proc /proc")

    os.execvp(args[0], args)


def run_container(bundle, cid, cmd_args):
    config = load_config(bundle)
    hostname = config.get("hostname", "container")

    root, upper, work, merged = prepare_dirs(cid)
    mount_overlay(BASE_ROOTFS, upper, work, merged)
    cg = setup_cgroup(cid, config)

    cmd = " ".join(cmd_args)

    container_cmd = f"""
    mount --make-rprivate / &&
    hostname {hostname} &&
    cd {merged} &&
    mount -t proc proc proc &&
    exec chroot . {cmd}
    """

    signal.signal(signal.SIGINT, lambda s,f: cleanup(root, cg) or sys.exit(1))
    signal.signal(signal.SIGTERM, lambda s,f: cleanup(root, cg) or sys.exit(1))

    pid = os.fork()

    if pid == 0:
        os.execvp("unshare", [
            "unshare",
            "--fork",
            "--pid",
            "--mount",
            "--uts",
            "--ipc",
            "--mount-proc",
            "bash",
            "-c",
            container_cmd
        ])
    else:
        add_proc_to_cgroup(cg, pid)
        os.waitpid(pid, 0)
        cleanup(root, cg)


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 mycont.py <config dir> <id> <command...>")
        sys.exit(1)

    _, config_dir, cid, *cmd_args = sys.argv
    run_container(config_dir, cid, cmd_args)


if __name__ == "__main__":
    main()