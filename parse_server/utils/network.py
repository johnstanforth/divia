import socket
import fcntl
import struct
import array
import sys


def get_net_interfaces():
    """
    Adapted from original all_interfaces() code below, with the following changes:
    - returns 'interfaces' dict instead of 'ifaces' list
    - uses Python 3.x context manager for socket(), to auto-close afterward
    - uses /dev/zero to initialize array (not sure, might be up to 2x as fast?)
    - uses newer .tobytes() instead of deprecated .tostring()
    """
    struct_size = 40 if (sys.maxsize > 2 ** 32) else 32  # test for 64-bit
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        max_possible = 8  # initial value
        while True:
            _bytes = max_possible * struct_size
            names = array.array('B')
            with open('/dev/zero', 'rb') as zr0:
                names.fromfile(zr0, _bytes)
            outbytes = struct.unpack('iL', fcntl.ioctl(s.fileno(), 0x8912,  # SIOCGIFCONF
                                                       struct.pack('iL', _bytes, names.buffer_info()[0])))[0]
            if outbytes == _bytes:
                max_possible *= 2
            else:
                break

    name_str = names.tobytes()
    interfaces = {}
    for i in range(0, outbytes, struct_size):
        ifc_name = bytes.decode(name_str[i:i + 16]).split('\0', 1)[0]
        ifc_addr = socket.inet_ntoa(name_str[i + 20:i + 24])
        interfaces[ifc_name] = ifc_addr

    return interfaces


# Original version of get_network_interfaces() function, created by various developers at
# http://code.activestate.com/recipes/439093-get-names-of-all-up-network-interfaces-linux-only/?in=user-2551140
def all_interfaces():
    is_64bits = sys.maxsize > 2**32
    struct_size = 40 if is_64bits else 32
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    max_possible = 8 # initial value
    while True:
        _bytes = max_possible * struct_size
        names = array.array('B')
        for i in range(0, _bytes):
            names.append(0)
        outbytes = struct.unpack('iL', fcntl.ioctl(
            s.fileno(),
            0x8912,  # SIOCGIFCONF
            struct.pack('iL', _bytes, names.buffer_info()[0])
        ))[0]
        if outbytes == _bytes:
            max_possible *= 2
        else:
            break
    namestr = names.tostring()
    ifaces = []
    for i in range(0, outbytes, struct_size):
        iface_name = bytes.decode(namestr[i:i+16]).split('\0', 1)[0]
        iface_addr = socket.inet_ntoa(namestr[i+20:i+24])
        ifaces.append((iface_name, iface_addr))

    return ifaces
