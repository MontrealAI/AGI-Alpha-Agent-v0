# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ctypes
import os
from typing import Any


def enforce() -> dict[str, Any]:
    library = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_rule_add_array.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_void_p,
    ]
    library.seccomp_rule_add_array.restype = ctypes.c_int
    library.seccomp_load.argtypes = [ctypes.c_void_p]
    library.seccomp_load.restype = ctypes.c_int
    library.seccomp_release.argtypes = [ctypes.c_void_p]

    class Compare(ctypes.Structure):
        _fields_ = [
            ("arg", ctypes.c_uint),
            ("op", ctypes.c_uint),
            ("mask", ctypes.c_uint64),
            ("value", ctypes.c_uint64),
        ]

    context = library.seccomp_init(0x7FFF0000)
    if not context:
        raise RuntimeError("read-only verifier filter unavailable")
    denied = [
        "creat",
        "openat2",
        "unlink",
        "unlinkat",
        "rename",
        "renameat",
        "renameat2",
        "mkdir",
        "mkdirat",
        "rmdir",
        "link",
        "linkat",
        "symlink",
        "symlinkat",
        "mknod",
        "mknodat",
        "chmod",
        "fchmod",
        "fchmodat",
        "fchmodat2",
        "chown",
        "fchown",
        "fchownat",
        "lchown",
        "truncate",
        "ftruncate",
        "setxattr",
        "lsetxattr",
        "fsetxattr",
        "removexattr",
        "lremovexattr",
        "fremovexattr",
        "utime",
        "utimes",
        "utimensat",
        "futimesat",
        "mount",
        "umount2",
        "pivot_root",
        "socket",
        "socketpair",
        "io_uring_setup",
        "execve",
        "execveat",
        "ptrace",
        "process_vm_writev",
    ]
    try:
        for name in denied:
            call = library.seccomp_syscall_resolve_name(name.encode())
            if call >= 0 and library.seccomp_rule_add_array(context, 0x0005000D, call, 0, None) != 0:
                raise RuntimeError("verifier mutation filter rule failed: " + name)
        for name, argument in [("open", 1), ("openat", 2)]:
            call = library.seccomp_syscall_resolve_name(name.encode())
            for bit in [os.O_WRONLY, os.O_RDWR, os.O_CREAT, os.O_TRUNC, os.O_APPEND]:
                compare = Compare(argument, 7, bit, bit)
                if library.seccomp_rule_add_array(context, 0x0005000D, call, 1, ctypes.byref(compare)) != 0:
                    raise RuntimeError("verifier write-open filter failed")
        if library.seccomp_load(context) != 0:
            raise RuntimeError("verifier kernel filter refused; no verification attestation")
    finally:
        library.seccomp_release(context)
    return {
        "mechanism": "additional kernel seccomp filter in verifier process",
        "file_write_open_and_mutation_denied": True,
        "new_sockets_and_exec_denied": True,
        "scope": "trusted deterministic verifier, no hostile arbitrary-native-code sandbox claim",
    }
