# Лабораторная работа №1 - Docker

## Делаем ручками
Чтобы написать утилиту, я решил сначала проделать все шаги вручную. Вначале нужно было скачать rootfs Alpine, я скопировал и распаковал его в рабочей директории утилиты.
![](<1 initial.png>)


Теперь у меня есть minirootfs в директории `base_rootfs`, которую я буду использовать как lowerdir в overlayfs. Также я создал еще 3 директории для работы моего тестового контейнера `test`.
![alt text](<2 overlayfs.png>)


Следующим шагом я создал cgroup для своей утилиты, и для каждого контейнера создаётся дочерняя cgroup с ограничениями, которые задаются в `config.json`. Но пока я записал всё вручную.
![alt text](<3 cgroups-1.png>)
![alt text](<3 cgroups-2.png>)

Пришло время namespaces, они должны изолировать наш процесс, позволяя ему работать со своими PID, hostname и mount.
![alt text](<4 namespaces.png>)

Последний шаг - чрутизация. Корневой директорией процесса становится выбранная нами, и он не может выбраться за ей пределы. Также я делаю `mount --make-rprivate`, чтобы mount не выбрался в основную систему.
![alt text](<5 chroot.png>)
На этом этапе я получил готоый контейнер, который должна создавать утилита.

## Вот теперь скрипт

Файл утилиты [mycont](mycont.py) лежит в репозитории, в отчете я пройдусь по функциям и алгоритму работы. Он схож с тем, что я проделывал руками.

Функция run запускает команду cmd:
```py
def run(cmd):
    subprocess.run(cmd, shell=True, check=True)
```

Функция `prepare_dirs(cid)` создаёт директории под контейнер с ID `cid`
```py
def prepare_dirs(cid):
    root = os.path.join(BASE_PATH, cid)
    upper = os.path.join(root, "upper")
    work = os.path.join(root, "work")
    merged = os.path.join(root, "merged")

    os.makedirs(upper, exist_ok=True)
    os.makedirs(work, exist_ok=True)
    os.makedirs(merged, exist_ok=True)

    return root, upper, work, merged
```

Функция `mount_overlay` монтирует overlayfs
```py
def mount_overlay(lower, upper, work, merged):
    run(f"mount -t overlay overlay -o lowerdir={lower},upperdir={upper},workdir={work} {merged}")
```

Функция `setup_cgroup(cid, config)` создаёт cgroup и задаёт ограничения из `config.json`
```py
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
```

Функция `add_proc_to_cgroup(cg, pid)` добавляет процесс в cgroup
```py
def add_proc_to_cgroup(cg, pid):
    with open(f"{cg}/cgroup.procs", "w") as f:
        f.write(str(pid))
```

Функция `container_main` меняет hostname и делает чрутизацию
```py
def container_main(merged, hostname, args):
    subprocess.run(["hostname", hostname], check=True)

    os.chroot(merged)
    os.chdir("/")
    run("mount -t proc proc /proc")

    os.execvp(args[0], args)
```

Функция `run_container` создаёт контейнер и запускает команду в нем, а также дожидается её завершения и делает cleanup. Для удобства я также добавил cleanup после нажатия Ctrl+C.
```py
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
```

## Источники
Лекция продвинутого потока, презентация  
[Статья на Хабре: Как собрать Linux-контейнер с нуля и без Docker
](https://habr.com/ru/companies/flant/articles/880354/)  
[Статья на Хабре: cgroups и namespaces в Linux: как это работает?](https://habr.com/ru/companies/otus/articles/858780/)