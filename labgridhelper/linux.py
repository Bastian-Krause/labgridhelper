from labgrid.protocol import CommandProtocol

def get_systemd_status(command):
    assert isinstance(command, CommandProtocol), "command must be a CommandProtocol"
    # TODO: Use busctl --json if systemd>239
    array_notation = "a(ssssssouso)"
    out = command.run_check(
        "busctl call --no-pager org.freedesktop.systemd1 \
        /org/freedesktop/systemd1 org.freedesktop.systemd1.Manager ListUnits"
    )

    out = out[0]
    if array_notation not in out:
        raise ValueError("Systemd ListUnits output changed")
    out = out[len(array_notation):]
    array_length = int(out[:out.index('"')].strip(" "))
    out = out[out.index('"')+1:-1]
    out = out.split('\" \"')
    data = iter(out)
    services = {}
    for _ in range(array_length):
        name = next(data)
        services[name] = {}
        services[name]["description"] = next(data)
        services[name]["load"] = next(data)
        services[name]["active"] = next(data)
        services[name]["sub"] = next(data)
        services[name]["follow"] = next(data)
        path_and_id = next(data)
        pos = path_and_id.index('"')
        services[name]["path"] = path_and_id[:pos]
        services[name]["id"] = int(path_and_id[pos+1:-1].strip(" "))
        services[name]["type"] = path_and_id[path_and_id.rfind('"'):]
        services[name]["objpath"] = next(data)

    return services

def get_commands(command, directories=None):
    """Returns the commands of a running linux system
    Args:
        command (CommandProtocol): An instance of a Driver implementing the CommandProtocol
        directories (list): An optional list of directories to include
    Returns:
        list: list of commands available under linux
    """
    assert isinstance(command, CommandProtocol), "command must be a CommandProtocol"
    out = command.run_check("ls /usr/bin")
    out.extend(command.run_check("ls /usr/sbin"))
    if directories:
        assert isinstance(directories, list), "directories must be a list"
        for directory in directories:
            out.extend(command.run_check("ls {}".format(directory)))
    commands = []
    for line in out:
        for cmd in line.split(" "):
            if cmd:
                commands.append(cmd)

    return commands

def get_systemd_service_active(command, service):
    """Returns True if service is active, False in all other cases
    Args:
        command (CommandProtocol): An instance of a Driver implementing the CommandProtocol
        service (str): name of the service
    Returns:
        bool: True if service is active, False otherwise
    """
    assert isinstance(command, CommandProtocol), "command must be a CommandProtocol"
    _, _, exitcode = command.run(
        "systemctl --quiet is-active {}".format(service)
    )
    return exitcode == 0

def get_interface_ip(command, interface="eth0"):
    import re
    """Returns the global valid IPv4 address of the supplied interface
    Args:
        command (CommandProtocol): An instance of a Driver implementing the CommandProtocol
        interface (string): name of the interface
    Returns:
        str: IPv4 address of the interface, None otherwise
    """
    try:
        ip_string = command.run_check("ip -o -4 addr show")
    except ExecutionError:
        self.logger.debug('No ip address found')
        return None

    regex = re.compile(
        r"""\d+:       # Match the leading number
        \s+(?P<if>\w+) # Match whitespace and interfacename
        \s+inet\s+(?P<ip>[\d.]+) # Match IP Adress
        /(?P<prefix>\d+) # Match prefix
        .*global # Match global scope, not host scope""", re.X
    )
    result = {}

    for line in ip_string:
        match = regex.match(line)
        if match:
            match = match.groupdict()
            result[match['if']] = match['ip']
    if result:
        return result[interface]

    return None

def get_hostname(command):
    """Returns the hostname
    Args:
        command (CommandProtocol): An instance of a Driver implementing the CommandProtocol
    Returns:
        str: hostname of the target, None otherwise
    """
    try:
        hostname_string = command.run_check("hostname")
    except ExecutionError:
        return None
    return hostname_string[0]
