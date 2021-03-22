import logging

from analysis_const import FILE_SYSCALLS, NETWORK_SYSCALLS, PROCESS_SYSCALLS, TIME_SYSCALLS, SIGNAL_SYSCALLS, IPC_SYSCALLS, KEY_MANAGEMENT_SYSCALLS
from util.enum_util import SyscallEnum


class StraceEntry(object):
    def __init__(self, pid, syscall_name, syscall_arguments, return_value,
                 was_unfinished=False, was_resumed=False, timestamp=None, elapsed_time=None):
        self.pid = pid
        self.syscall_name = syscall_name
        self.syscall_arguments = syscall_arguments
        self.return_value = return_value
        self.category = self._get_category()
        self.was_unfinished = was_unfinished
        self.was_resumed = was_resumed
        self.timestamp = timestamp
        self.elapsed_time = elapsed_time

    def _get_category(self):
        syscall_str = self.syscall_name.upper()
        if syscall_str in FILE_SYSCALLS:
            return SyscallEnum.file
        elif syscall_str in NETWORK_SYSCALLS:
            return SyscallEnum.network
        elif syscall_str in PROCESS_SYSCALLS:
            return SyscallEnum.process
        elif syscall_str in TIME_SYSCALLS:
            return SyscallEnum.time
        elif syscall_str in SIGNAL_SYSCALLS:
            return SyscallEnum.signal
        elif syscall_str in IPC_SYSCALLS:
            return SyscallEnum.ipc
        elif syscall_str in KEY_MANAGEMENT_SYSCALLS:
            return SyscallEnum.key_management
        else:
            return None

    def is_sensitive_operation(self):
        # TODO
        pass

    def is_privilege_operation(self):
        # TODO
        pass


class StraceDomain(object):
    # http://www.brendangregg.com/blog/2016-10-27/dtrace-for-linux-2016.html
    # getaddrinfo/gethostbyname
    pass

class StraceSocket(object):
    pass


class StraceFile(object):
    pass


class StraceOperation(object):
    # Sensitive operations, such as reading sensitive info, performing privileged operations.
    pass


class StraceProcess(object):
    # Creation and termination
    # "CLONE","FORK","VFORK","EXECVE","EXECVEAT","EXIT","EXIT_GROUP","WAIT4","WAITID",
    def __init__(self, pid, name):
        self.pid = pid
        self.name = name
        self.entries = []
        self.child_pids = []  # or parent id?
        self.sockets = {}
        self.files = {}
        self.operations = {}

    def add_entry(self, entry):
        self.entries.append(entry)
        if entry.syscall_name:
            pass

    def set_name(self, name):
        self.name = name

    def _add_socket(self):
        pass

    def _add_file(self):
        pass

    def _add_child_pid(self):
        pass


class StraceInputStream(object):
    def __init__(self, infile):
        """
        Initialize the strace input stream from file name
        """
        self.inf = open(infile, 'r')
        self.line_no = 0
        self.unfinished_syscalls = {}  # PID -> line

    def __iter__(self):
        return self

    def _parse_arguments(self, arguments_str, include_quotes=True, include_ellipsis=True):
        """
        Parse the given argument string and return an array of substrings
        """
        arguments = []
        current_arg = ""
        quote_type = None
        escaped = False
        expect_comma = False
        between_arguments = False
        nest_stack = []
        for ch in arguments_str:
            # characters between argumnets
            if between_arguments and ch in [' ', '\t']:
                continue
            else:
                between_arguments = False
            if expect_comma:
                assert quote_type is None
                if ch == '.':
                    if include_ellipsis:
                        current_arg += ch
                elif ch == ',':
                    expect_comma = False
                    between_arguments = True
                    arguments.append(current_arg)
                    current_arg = ""
                elif ch in [' ', '\t']:
                    continue
                else:
                    logging.error("'%s' found where comma expected; offending string: %s", ch, arguments_str)
                continue

            # arguments
            if escaped:
                current_arg += ch
                escaped = False
            elif ch == '\\':
                current_arg += ch
                escaped = True
            elif ch in ['"', '\'', '[', ']', '{', '}']:
                if quote_type in ['"', '\''] and ch != quote_type:
                    current_arg += ch
                elif ch == quote_type:
                    if include_quotes or len(nest_stack) > 0:
                        current_arg += ch
                    if len(nest_stack) > 1:
                        nest_stack.pop()
                        quote_type = nest_stack[-1]
                    else:
                        nest_stack.pop()
                        quote_type = None
                        if not current_arg == '[?]':
                            expect_comma = True
                elif ch in [']', '}']:
                    current_arg += ch
                else:
                    if include_quotes or len(nest_stack) > 0:
                        current_arg += ch
                    if ch == '[':
                        ch = ']'
                    if ch == '{':
                        ch = '}'
                    quote_type = ch
                    nest_stack.append(ch)
            elif ch == ',' and quote_type is None:
                arguments.append(current_arg)
                current_arg = ""
                between_arguments = True
            else:
                current_arg += ch

        if quote_type is not None:
            logging.error("Expected '%s' but found end of the string; offending string: %s",
                          quote_type, arguments_str)
        if len(current_arg) > 0:
            arguments.append(current_arg)
        return arguments

    def next(self):
        """
        Return the next complete entry. Raise StopIteration if done
        """
        line = self.inf.next()
        if line is None:
            raise StopIteration

        line = line.strip()
        self.line_no += 1
        pos_start = 0

        if line == "":
            if self.line_no == 1:
                raise Exception("The first line needs to be valid!")
            else:
                return self.next()
        if not line[0].isdigit():
            if self.line_no == 1:
                raise Exception("The first line needs to be valie!")

        # Get the PID
        pid = None
        timestamp = None
        was_unfinished = False
        was_resumed = False
        elapsed_time = None
        syscall_name = None
        arguments = None
        return_value = None

        # Signals

        # Exit/Kill

        # Unfinished and resumed syscalls

        # Extract basic information

        # Extract the return value

        # Extract the arguments

        # Finish
        return StraceEntry(pid=pid, syscall_name=syscall_name, syscall_arguments=arguments, return_value=return_value,
                           was_unfinished=was_unfinished, was_resumed=was_resumed)

    def close(self):
        """
        Close the input stream
        """
        self.inf.close()


class StraceParser(object):
    """
    Process strace logs generated by command:
    strace -fqv -s 1024 -o $trace_file $cmd
    """
    def __init__(self, infile):
        """
        Load the strace file contents from the given file.
        """
        self.infile = infile
        self.content = []
        self.processes = {}

        # TODO: Currently no timestamp is logged. Optionally add suport for timestamps.
        self.start_time = None
        self.last_timestamp = None
        self.finish_time = None
        self.elapsed_time = None

        # Process the file
        strace_stream = StraceInputStream(self.infile)
        for entry in strace_stream:
            if entry.pid not in self.processes.keys():
                self.processes.setdefault(entry.pid, StraceProcess(entry.pid, None))
            if self.processes[entry.pid].name is None:
                if entry.syscall_name == "execve" and len(entry.syscall_arguments) > 0:
                    self.processes[entry.pid].set_name(entry.syscall_arguments[0])
            self.content.append(entry)
            self.processes[entry.pid].add_entry(entry)

